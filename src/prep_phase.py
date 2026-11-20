"""prep_phase —— 「回合准备阶段」的行为重建（非原码）。

来源：对 测试1.0.exe 里 garrison_farm.prep_phase（原第 1604 行）的反汇编
逐条人工翻译。变量名、字符串、比较方向、循环次数都与反汇编一致；
少量注释是我的理解，遇到不确定的地方标了「推断」。

原函数签名：prep_phase(board, img)
  board —— 局内状态对象，用到这些字段：
      round_done   已完成的回合数
      prep_done    本回合准备是否已完成
      healers      场上医疗干员数量
      owned        已拥有干员计数字典 {名字: 个数}
      pending      是否有待上场的干员（买完还在备战席）
      last_ready   上次点「准备就绪」的时间戳
  img —— 当前截图（商店界面）
"""

import time

# 原程序的模块级常量（坐标元组 / 状态容器）
UPX = (1786, 686)            # 商店「升级」按钮
REFRESH = (1785, 768)        # 商店「刷新」按钮
READY = (1850, 816)          # 「准备就绪」按钮
GOLD_FAIL = [0]              # 连续读取资金失败次数


def prep_phase(board, img):
    """一个回合的准备阶段：升级商店、买干员、部署待上场、点准备就绪。"""

    # ---------- 0. 读商店状态 ----------
    gold, up_cost, maxed, rnd = read_shop(img)

    # 读不到回合号时：本次准备已做完就直接返回，否则按「已完成回合 + 1」推算
    if rnd is None:
        if board.prep_done:
            return None
        rnd = max(1, board.round_done + 1)

    # 这一回合已经准备过了（比如重复截图进来）
    if rnd == board.round_done:
        return None

    t0 = time.time()
    log('回合%d 资金%s 升级费用%s 满级%s' % (rnd, gold, up_cost, maxed))
    save(img, 'shop_r%d' % rnd)

    # ---------- 1. 第 1 回合：只买 2 个干员（最多 1 个医疗） ----------
    if board.round_done == 0 and rnd == 1:
        bought = 0
        for c in shop_cards(img):
            g = gold_now()
            if bought >= 2:
                break
            # 不是干员 / 没有价格 / 买不起 → 跳过
            if not (c['op'] and c['cost'] is not None and (g is None or c['cost'] <= g)):
                continue
            if is_healer(c['name']) and board.healers >= 1:
                log('跳过第二个医疗干员:', c['name'])
                continue
            if buy_and_deploy(board, c['i'], 5 if c['hi'] else 1, c['cost']):
                bought += 1
                board.healers += is_healer(c['name'])

    # ---------- 2. 升级商店（最多 4 次，钱够就升） ----------
    # 每次点完都用「资金/升级费用是否变化」确认真的升上去了，
    # 连续点两次是为了防止第一次点击被动画吃掉。
    if not maxed:
        for _ in range(4):
            img = shot()
            gold, up_cost, maxed, _ = read_shop(img)
            if maxed or gold is None or up_cost is None or gold < up_cost:
                break
            ux0 = UPX
            tap(UPX[0], UPX[1], 0.6)
            tap(UPX[0], UPX[1], 1.0)
            g2, c2, maxed, _ = read_shop(shot())
            ok = (
                maxed                                     # 直接满级了
                or UPX != ux0                             # 按钮位置变了（界面推进）
                or (gold is not None and g2 is not None and g2 != gold)   # 资金变了
                or (up_cost is not None and c2 is not None and c2 < up_cost)  # 升级费用降了
            )
            if not ok:
                break                                     # 点了没反应，别死循环
            log('商店升级，资金 %s -> %s，升级费用 %s -> %s'
                % (gold, g2, up_cost, '满级' if maxed else c2))

    # ---------- 3. 没满级：继续买（每买一个都重新截图确认钱和格子） ----------
    if not maxed:
        for c in shop_cards(shot()):
            im = shot()
            g = read_gold(im)
            sl = slots_left(im)
            if g == 0 or sl == 0:
                log('停止购买：' + ('资金为 0' if g == 0 else '部署位已满'))
                break
            if g is None:
                log('警告：资金读取失败，仍尝试购买（买不起时游戏会提示）')
            if not (c['op'] and c['cost'] is not None and (g is None or c['cost'] <= g)):
                continue
            if is_healer(c['name']) and board.healers >= 1:
                log('跳过第二个医疗干员:', c['name'])
                continue
            if buy_and_deploy(board, c['i'], 5 if c['hi'] else 1, c['cost']):
                board.healers += is_healer(c['name'])

    # ---------- 4. 商店满级后：刷新找 5/6 级干员 ----------
    if maxed:
        refreshes, same_count, last_sig = 0, 0, None
        for _ in range(40):                       # 最多折腾 40 轮
            img = shot()
            gold = read_gold(img)
            got = False
            allc = shop_cards(img)
            sig = shop_signature(allc)            # 商店 5 张卡的「指纹」

            # 连续两次刷新后商店没变化 → 资金不足或没点中，直接放弃
            if last_sig is not None:
                if sig == last_sig:
                    same_count += 1
                    if same_count >= 2:
                        save(img, 'refresh_no_effect')
                        log('停止刷新：连续刷新后商店没有变化（可能资金不足或刷新按钮没点到），截图已保存')
                        break
                else:
                    same_count = 0
            last_sig = sig

            if gold is None:
                GOLD_FAIL[0] += 1
                if GOLD_FAIL[0] > 3:
                    save(img, 'gold_unreadable')
                log('警告：资金数字读取失败，按「未知」处理（尝试购买和刷新，由游戏提示判断是否买得起）')
            gold_v = 99 if gold is None else gold

            # 免费卡（费用 0）与买得起的 5/6 级干员
            free = [c for c in allc if c['op'] and c['cost'] == 0]
            cards = [c for c in allc
                     if c['hi'] and c['op'] and c['cost'] is not None and c['cost'] <= gold_v]

            def owned(c):
                """是否已经拥有（名字互相包含即算同一人，处理「玛恩纳」/「玛恩纳·异格」这类）。"""
                return any(n and (n in c['name'] or c['name'] in n) for n in board.owned)

            # 优先级：权重表里有的 → 已拥有的 → 输出位 → 随便买
            prio = sorted([c for c in cards if prio_index(c['name']) is not None],
                          key=lambda c: prio_index(c['name']))

            if free:
                # 免费卡按「星级够高优先」排序，只拿第一张
                pick = sorted(free, key=lambda c: -rank(c['name'], 5 if c['hi'] else 1))[:1]
            else:
                pick = (prio
                        or [c for c in cards if owned(c)]
                        or [c for c in cards if c['dps']]
                        or (cards if gold is not None and gold >= 4 else []))

            failed = False
            for c in pick:
                tag = ('优先' if prio_index(c['name']) is not None
                       else ('输出' if c['dps'] else '非输出'))
                log('购买 V/VI:', c['name'], tag, '费用%d' % c['cost'])
                if buy_and_deploy(board, c['i'], 5 if c['hi'] else 1, c['cost']):
                    board.owned[c['name']] = board.owned.get(c['name'], 0) + 1
                    got = True
                else:
                    failed = True
                    break

            if failed:
                log('购买失败，结束本回合购买')
                break
            if got:
                last_sig = None          # 买到东西了，指纹重置，继续找下一张
                continue
            if gold is not None and gold < 4:
                log('停止刷新：资金 %s 不足 4（本回合刷新 %d 次）' % (gold, refreshes))
                break
            refreshes += 1
            hi_n = sum(1 for c in allc if c['hi'] and c['op'])
            log('刷新商店（第 %d 次）：资金 %s，当前 5/6 级干员 %d 张，可买 %d 张'
                % (refreshes, gold if gold is not None else '未知', hi_n, len(cards)))
            tap(REFRESH[0], REFRESH[1], 1.0)

    # ---------- 5. 收尾：部署待上场干员 → 点「准备就绪」 ----------
    if board.pending:
        deploy_bench(board)
        board.pending = False
    board.round_done = rnd
    board.prep_done = True
    time.sleep(1.5)
    tap(READY[0], READY[1], 1.5)
    board.last_ready = time.time()
    handle_popups()
    log('回合%d 准备耗时 %.0fs' % (rnd, time.time() - t0))


# 下面是原程序里本函数用到的外部函数/常量，按签名列出方便阅读：
#   read_shop(img)      -> (gold, up_cost, maxed, rnd)
#   read_gold(img)      -> 当前资金（读不到返回 None）
#   gold_now()          -> 重新截图读资金
#   shop_cards(img)     -> [{'i': 序号, 'name': 干员名, 'cost': 费用, 'op': 是否干员,
#                            'hi': 是否 5/6 级, 'dps': 是否输出}]
#   shop_signature(cards) -> 商店指纹（用于判断刷新有没有生效）
#   slots_left(img)     -> 剩余可部署格数
#   is_healer(name)     -> 是否医疗干员
#   prio_index(name)    -> 该干员在优先购买表里的名次（不在表里返回 None）
#   rank(name, tier)    -> 同星级内的强度排名
#   buy_and_deploy(board, i, tier, cost) -> 买下第 i 张卡并部署，成功返回 True
#   deploy_bench(board) -> 把备战席待上场的干员拖到场上
#   handle_popups()     -> 关掉可能弹出的提示框
