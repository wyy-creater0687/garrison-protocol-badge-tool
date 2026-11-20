"""main —— 主循环的结构级重建（非原码）。

说明：这个文件是**结构级**重建，不是逐条翻译。依据是对 测试1.0.exe 里
garrison_farm.main（原第 1744 行，8436 字节字节码）的反汇编：分支结构、
判定用的界面关键字、日志字符串都取自反汇编原文；函数内部的细节被抽象成
有名字的辅助函数（detect_screen / do_prep 等），方便阅读。

逐条翻译的版本见同目录 prep_phase.py。
"""

import argparse
import ctypes
import os
import sys
import time
import traceback

GARRISON = ('极速模拟', '卫戍', 'STRONGHOLD', '同盟模拟', '个人模拟', '确认准备',
            '资金将在', '选择策略', '确认本局信息', '确定自选编队', '返回主页',
            '模拟完成', '模拟中断', 'COUNTDOWN', '断线重连', '放弃模拟')

LEAVE_TIMEOUT = 180      # 秒：这么久看不到卫戍协议界面就认为退出了
STALL_TIMEOUT = 600      # 秒：局内这么久没有进展就判定卡死
MAX_ERRORS = 10          # 连续异常次数上限


def parse_args(argv):
    ap = argparse.ArgumentParser(description='卫戍协议 · 极速模拟 自动刷策略角标')
    ap.add_argument('--runs', type=int, default=200, help='目标通关局数')
    ap.add_argument('--attempts', type=int, default=0, help='总局数上限（成功失败都算），0=不限')
    ap.add_argument('--maa', default='', help='MAA 目录（默认自动查找）')
    ap.add_argument('--adb', default='', help='覆盖 MAA 配置中的 adb 路径')
    ap.add_argument('--address', default='', help='覆盖 MAA 配置中的连接地址')
    ap.add_argument('--check', action='store_true', help='只检查 MAA/设备/OCR 是否正常，然后退出')
    ap.add_argument('--yes', action='store_true', help='启动时不再弹确认框')
    ap.add_argument('--no-maa', action='store_true', help='不依赖 MAA，直接使用本机 adb')
    ap.add_argument('--show-doc', default='', help='显示 bat 里 :: 开头的说明文字')
    ap.add_argument('--profile', default='full', choices=('full', 'low'),
                    help='full=标准（要自选编队），low=低配（只用预设）')
    ap.add_argument('--target', type=int, default=6, help='3=金色角标，6=彩色角标')
    ap.add_argument('--menu', action='store_true', help='显示模式选择菜单')
    ap.add_argument('--no-maafw', action='store_true', help='不使用 MaaFramework')
    ap.add_argument('--device', default='emulator', choices=('emulator', 'pc'))
    ap.add_argument('--pc-screencap', default='', help='PC 端截图方式')
    ap.add_argument('--pc-mouse', default='', help='PC 端鼠标方式')
    return ap.parse_args(argv)


def choose_interactively(args):
    """--menu / 未指定 --device 时的交互式选择（原程序用 input() 实现）。"""
    if not args.menu and args.device:
        return args

    print('请选择设备（输入数字后按回车）：')
    print('  1. 安卓模拟器（MuMu 等，通过 adb）')
    print('  2. 官服鹰角 PC 端（需要管理员权限，运行时会移动鼠标）')
    dev = input('请输入 1 或 2：').strip() or '1'
    args.device = 'pc' if dev == '2' else 'emulator'
    if args.device == 'pc':
        print('请选择 PC 端鼠标方式（直接回车 = 使用 MAA 的配置）：')
        print('  1. AnchoredTouch      全后台操作，可能会闪')
        print('  2. PostMsg-WindowPos  后台操作，截图用 PrintWindow')
        print('  3. PostMsg-CursorPos  半后台，会移动一点鼠标')
        m = input('请输入 1~3（直接回车）：').strip()
        args.pc_mouse = {'1': 'AnchoredTouch',
                         '2': 'PostMessageWithWindowPos',
                         '3': 'PostMessageWithCursorPos'}.get(m, '')

    print('请选择运行模式（输入数字后按回车）：')
    print('  1. 标准模式 · 刷金色角标（每个策略通关 3 次）   需要配置自选编队')
    print('  2. 标准模式 · 刷彩色角标（每个策略通关 6 次）   需要配置自选编队')
    print('  3. 低配模式 · 刷金色角标（每个策略通关 3 次）   不需要自选编队')
    print('  4. 低配模式 · 刷彩色角标（每个策略通关 6 次）   不需要自选编队')
    mode = input('请输入 1~4：').strip() or '2'
    args.profile = 'low' if mode in ('3', '4') else 'full'
    args.target = 3 if mode in ('1', '3') else 6

    if not args.yes:
        msg = '\n'.join([
            '运行模式：%s · %s' % ('低配模式' if args.profile == 'low' else '标准模式',
                                   '彩色角标（通关 %d 次）' % args.target),
            '',
            '建议在「选配助战」里为自己没有的干员借用助战（最多 30 名），胜率更高。',
            '请确认游戏「自选编队」中已配置推荐干员。',
            '本程序会优先购买：塔露拉、维什戴尔、斩业星熊、予愿安洁莉娜、新约能天使…',
            '点击「确定」开始运行。',
        ])
        if not confirm_box('GarrisonFarm 使用前提醒', msg):
            raise SystemExit('用户取消运行')
    return args


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])

    # 显示 bat 里的说明（--show-doc 指向 bat 自己）
    if args.show_doc:
        show_doc_from_bat(args.show_doc)

    if is_admin() is False and args.device == 'pc':
        relaunch_as_admin()          # PC 端需要管理员权限，原程序会自我提权

    args = choose_interactively(args)

    # ---- 连接：MaaFramework → 退回 MAA 配置的 adb → 退回本机 adb ----
    setup(args.device)                              # 内部会设置 adb / MAA / PCWin
    if not args.no_maafw:
        maafw_init()
    ok, why = ocr_selftest()                        # 打印「OCR 正常（x.xs）」
    if not ok:
        print('OCR 初始化失败:', why)
        return 1
    if args.check:
        print('检查完成，未发现问题。')
        return 0

    load_layout()                                   # tiles.json
    print_mode_banner(args.profile, args.target)    # 「当前模式：…欢迎语」

    board = Board()
    done = load_done()
    results = []
    last_seen = time.time()
    last_progress = time.time()

    for run_t0 in range(10 ** 9):
        if args.attempts and len(results) >= args.attempts:
            break
        if len(results) >= args.runs:
            break

        try:
            img = shot()

            # ---- 1. 不在卫戍协议界面 → 提示并退出 ----
            if not any(k in find(img) for k in GARRISON):
                if args.check:
                    continue
                print('【提示】当前不是卫戍协议的极速模拟界面，程序已停止。')
                print('请先在游戏中进入「卫戍协议」主界面…')
                break

            # ---- 2. 界面导航 ----
            if '同盟模拟' in find(img) and '个人模拟' not in find(img):
                tap(1726, 989, 1.0)                 # 切到「个人模拟」
                log('卫戍协议主界面在「联合模拟」页，切换到「个人模拟」')
                continue

            if '断线重连' in find(img):
                log('检测到未完成的对局，断线重连')
                tap(*RECONNECT, 3.0)
                last_progress = time.time()
                continue

            if '极速模拟' in find(img) and '开始模拟' not in find(img):
                tap(*SPEED_MODE, 2.0)               # 主界面 → 极速模拟
                continue

            if '请选择模拟难度' in find(img) or '开始模拟' in find(img):
                tap(*START_SIM, 2.5)                # 1/3 → 开始模拟
                continue

            if '确认准备' in find(img) or '资金将在' in find(img):
                tap(*CONFIRM_READY, 2.5)            # 2/3 → 准备就绪
                continue

            if '选择状态' in find(img):
                pick_strategy(done)                 # 2/3 选策略（逐格检查）
                continue

            if '确认本局信息' in find(img):
                tap(*CONFIRM_INFO, 2.0)
                continue

            if '选择策略' in find(img):
                pick_strategy(done)
                continue

            if '确定自选编队' in find(img):
                if args.profile == 'full':
                    pick_squad()                    # 3/3 选自选编队 4 人
                tap(*READY, 2.0)
                continue

            # ---- 3. 局内：每回合准备 ----
            if '休整期' in find(img) or '回合' in find(img) or '准备就绪' in find(img):
                try:
                    prep_phase(board, img)
                except Exception:
                    log('休整期处理出错（已记录，继续运行）:', traceback.format_exc())
                    if errors_too_many():
                        print('出错次数过多，停止运行。')
                        break
                last_progress = time.time()
                continue

            # ---- 4. 结算 ----
            if '模拟完成' in find(img) or '模拟中断' in find(img):
                msg = find(img)
                win = '模拟完成' in msg and '模拟中断' not in msg
                current = board.current_strategy or '未识别'
                results.append((current, win))
                if win:
                    done[current] = done.get(current, 0) + 1
                    save_done(done)
                log('本局%s，策略 %s，用时 %ds，已通关 %d/%d，已打 %d 局'
                    % ('通关' if win else '失败', current, int(time.time() - run_t0),
                       sum(done.values()), args.runs, len(results)))
                tap(*BACK_HOME, 3.0)                # 返回主页，进入下一局
                board = Board()
                continue

            # ---- 5. 超时保护 ----
            if time.time() - last_progress > STALL_TIMEOUT:
                print('%d 分钟没有进展，判定为卡死，停止运行。' % (STALL_TIMEOUT // 60))
                break
            last_seen = time.time_since_marker(img, last_seen)
            if time.time() - last_seen > LEAVE_TIMEOUT:
                print('%d 秒检测不到卫戍协议界面，立即停止。' % LEAVE_TIMEOUT)
                break

            handle_popups()                         # 关掉「点击任意/继续/确认」这类弹窗

        except KeyboardInterrupt:
            print('已手动停止')
            break
        except Exception:
            log('运行时出错:', traceback.format_exc())
            if errors_too_many():
                print('出错次数过多，停止运行。')
                break

    print('结束。本次结果:', results)
    print('已获得角标的策略:', sorted(k for k, v in done.items() if v >= args.target))
    return 0


# ---- 说明 ----
# 上面出现的界面关键字、日志文案都取自反汇编里的字符串常量；
# 坐标常量（SPEED_MODE / START_SIM / READY …）对应模块级元组：
#   (1785, 768, 1850, 816) 等，具体值见 README 的常量表。
# 原程序在每一轮里还会处理：停在选择朝向界面时自动补设朝向、
# 「仍在休整期，重新点击准备就绪」、「点击取消」等分支，这里省略了细节。
