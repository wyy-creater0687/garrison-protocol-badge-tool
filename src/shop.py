"""商店识别与买卡 —— 行为重建（非原码）。

来源：对 测试1.0.exe 里 garrison_farm.shop_cards（原 1117 行）、buy（1145 行）、
buy_and_deploy（1526 行）的反汇编人工翻译。坐标、阈值、字符串都取自反汇编；
个别语义（如 board.ops 的写入形式）标了「推断」。
"""

# 模块级常量（原程序里的坐标表，取自反汇编的常量池）
CARDS = (304, 550, 790, 1034, 1274, 1520)   # 商店卡位中心 x
CARD_Y = 900                                # 点卡片的 y
GOLD_BOX = (1785, 740, 1910, 800)           # 右上角资金数字的 OCR 框（推断）
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}
LAST_TIER = [5]                             # 上次购买的星级
LAST_TILE = ['rest0']                       # 上次放置的位置


def shop_cards(img):
    """识别商店 5~6 个卡位，返回每张卡的信息。

    返回: [{'i':卡位序号, 'x':中心x, 'empty':是否空位, 'cost':价格(可为None),
            'hi':是否 5/6 级, 'op':是否干员卡, 'name':名字, 'dps':是否输出}, ...]

    识别要点（与反汇编逐条对应）：
      · 价格：y==830 且离卡位中心 <=45px 的纯数字文字；否则用 numrec 再识别一次
        卡片下方 (x-22,780)-(x+22,822) 的区域；
      · 空位：该卡位内出现 'INFO' 字样；
      · 星级：y==840、x==卡位+50 的罗马数字；认不出就用卡片左上角的黄色占比
        （>0.1 判定为 5/6 级）；
      · 名字：y>=1000 且含中文/字母数字的文字，取最后一个；
      · 干员：y 在 930~1000 之间且含中文的文字。
    """
    items = ocr(img, (180, 770, 1700, 1060))
    out = []
    for i, x in enumerate(CARDS):
        # 归属到本卡位（横向 ±115px）
        mine = [(cx, cy, t) for (cx, cy, t) in items if abs(cx - x) <= 115]

        empty = any('INFO' in t() for (_cx, _cy, t) in mine)

        # ---- 价格 ----
        cost = None
        for cx, cy, t in mine:
            if cy == 830 and abs(cx - x) <= 45 and t() and all(ch in '0123456789' for ch in t()):
                cost = int(t())
        if cost is None and not empty:
            cost = numrec(img, (x - 22, 780, x + 22, 822))

        # ---- 是否干员卡 ----
        op = any(930 <= cy <= 1000 and any('一' <= ch <= '鿿' for ch in t())
                 for (cx, cy, t) in mine)

        # ---- 星级（罗马数字 → 黄框兜底） ----
        r = 0
        for cx, cy, t in mine:
            tt = t().upper().replace('1', 'I').replace('L', 'I')
            if cy == 840 and cx == x + 50 and tt in ROMAN:
                r = ROMAN[tt]
        if r:
            hi = r >= 5
        else:
            hi = yellow_ratio(img, (x - 104, 800, x + 78, 826)) > 0.1

        # ---- 名字 ----
        names = [t for (cx, cy, t) in mine
                 if cy >= 1000 and any('一' <= ch <= '鿿' or ch.isalnum() for ch in t)]
        name = names[-1]() if names else ''

        out.append(dict(i=i, x=x, empty=empty, cost=cost, hi=hi,
                        op=(op and not empty), name=name, dps=is_dps(name)))
    return out


def buy(i, cost):
    """买第 i 个卡位的卡：点卡 → 判断弹窗/是否干员 → 点「购买」→ 看资金有没有减少。

    返回 True 表示买到（或免费/资金未知时按买到处理）。
    """
    x = CARDS[i]
    g0 = numrec(shot(), GOLD_BOX)
    tap(x, CARD_Y, 0.8)

    img = shot()
    # 弹窗「无法购买」/ 右上「资金不足」→ 关掉弹窗，失败
    if find(ocr(img, (x - 120, 980, x + 120, 1060)), '无法购买') \
            or find(ocr(img, (1400, 120, 1920, 260)), '资金不足'):
        tap(960, 600, 0.4)
        return False

    # 左侧详情面板：有「特质/天赋/特性」才是干员卡
    left = ocr(img, (0, 250, 700, 620))
    is_op = bool(find(left, '特质', '天赋', '特性'))
    if not is_op:
        tap(x, CARD_Y, 0.4)      # 取消选中
        tap(960, 600, 0.4)
        return False

    tap(x, CARD_Y - 106, 1.2)    # 「购买」按钮在卡片上方
    g1 = numrec(shot(), GOLD_BOX)

    # 资金没变 → 没买成功；免费卡或资金读不到时按成功处理
    if cost > 0 and g0 is not None and g1 is not None and not (g1 < g0):
        tap(960, 600, 0.4)
        return False
    return True


def buy_and_deploy(board, i, tier, cost):
    """买一张卡并尽量立刻部署：买 → 找新干员在备战席的格子 → 拖到场上。"""
    before = shot()
    if not buy(i, cost):
        return False
    after = shot()

    slot = new_bench_slot(before, after)     # 对比买前买后，找出新出现的备战席格子
    if not slot:
        log('没找到新买的干员（可能合成晋升了）')
        handle_popups()
        board.pending = True                 # 记下来，回合结束前再统一部署
        return True

    pos = deploy_from_bench(slot, board, hi=(tier >= 5))
    if pos:
        # 推断：把「摆到哪了 + 星级」记进场上表，供后续替换/卖出判断
        board.ops[(pos[0], pos[1])] = (pos[0], pos[1],
                                       max(tier, LAST_TIER[0]), LAST_TILE[0])
    else:
        board.pending = True                 # 没找到合适位置，等回合结束再摆

    return True


# 依赖的辅助函数（原程序实现，见 tools/list_functions.py 的函数表）：
#   ocr(img, box) -> [(cx, cy, text), ...]   text 是可直接调用取字符串的 OCR 条目
#   find(items, *keywords) -> bool           在 OCR 结果里找关键字
#   numrec(img, box)                         只认数字的 OCR（读资金/费用）
#   yellow_ratio(img, box)                   框内黄色像素占比（判金色/高级卡）
#   new_bench_slot(before, after)            买前买后对比，找新干员所在的备战席格子
#   deploy_from_bench(slot, board, hi=bool)  把备战席格子拖到场上，返回落点或 None
