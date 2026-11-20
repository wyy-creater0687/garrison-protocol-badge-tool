"""截图与连接 —— 行为重建（非原码）。

来源：对 测试1.0.exe 里 garrison_farm 的 maafw_pc（原 662 行）、maafw_adb（687 行）、
adb（705 行）、shot（710 行）、save（818 行）的反汇编人工翻译。

要点：程序**不需要运行 MAA 客户端**。它自带 MaaFramework 的 Python 绑定
（_internal/maa），直接用 adb 连模拟器、用 maafw 自带的截图/触控实现工作；
MAA 的 config/gui.new.json 只用来读取 adb 路径和连接地址。
"""

import os
import time

import cv2
import numpy as np

LOG_DIR = 'farm_logs'          # 日志与调试截图目录
SHOT_RETRY = 60                # 截图重试次数（原版 5，2.5 秒就崩；这里 60 ≈ 30 秒）
SHOT_SLEEP = 0.5               # 每次失败等待


# ---------------------------------------------------------------- 连接：安卓
def maafw_adb(adb_path, address):
    """用 maafw 的 AdbController 连模拟器。

    截图固定用 RawWithGzip（adb 上跑 screencap 输出原始像素，gzip 传回，
    跳过 PNG 编解码），触控固定用 Maatouch（minitouch 协议）。

    原程序的逻辑：先按 RawWithGzip + Maatouch 建控制器并尝试连接；
    失败时退回到「该设备探测到的默认截图/输入方式」再试一次；
    还失败就抛 RuntimeError('maafw 连接模拟器失败')。
    """
    from maa.toolkit import Toolkit
    from maa.controller import AdbController
    from maa.define import MaaAdbScreencapMethodEnum as SC, MaaAdbInputMethodEnum as IM

    maafw_dll_dirs()                 # 把 _internal/maa 的 dll 目录加进搜索路径
    tk = maafw_init()

    sc, im, cfg = SC.Default, IM.Default, {}
    # 设备探测：拿到这台设备支持的截图/输入方式（字符串枚举值）
    for d in tk.find_adb_devices(specified_adb=adb_path):
        if d.address == address:
            sc, im, cfg = d.screencap_methods, d.input_methods, d.config
            break

    ctl = AdbController(adb_path, address, SC.RawWithGzip, IM.Maatouch, cfg)
    if not ctl.post_connection().wait().succeeded:
        ctl = AdbController(adb_path, address, sc, im, cfg)   # 退回默认方式
        if not ctl.post_connection().wait().succeeded:
            raise RuntimeError('maafw 连接模拟器失败')
    return MaaCtl(ctl)


# ---------------------------------------------------------------- 连接：PC
def maafw_pc(sc_name, mouse_name):
    """PC 端：按窗口标题找游戏窗口，用 maafw 的 Win32Controller 连上去。

    sc_name   —— 截图方式：PrintWindow / PostMessageWithWindowPos / ScreenDC …
    mouse_name —— 鼠标方式：AnchoredTouch / PostMessageWithCursorPos / SendMessage …
    """
    from maa.toolkit import Toolkit
    from maa.controller import Win32Controller
    from maa.define import MaaWin32ScreencapMethodEnum as SC, MaaWin32InputMethodEnum as IM

    maafw_dll_dirs()
    tk = maafw_init()

    hwnd = find_desktop_windows()        # 找「明日方舟 / 鹰角」窗口
    if hwnd is None:
        raise RuntimeError('没找到官服 PC 端的游戏窗口')
    ctl = Win32Controller(hwnd,
                          getattr(SC, sc_name or 'PrintWindow'),
                          getattr(IM, mouse_name or 'AnchoredTouch'))
    if not ctl.post_connection().wait().succeeded:
        raise RuntimeError('maafw 连接游戏窗口失败')
    return MaaCtl(ctl)


# ---------------------------------------------------------------- 截图
def shot():
    """截一张图：黑帧（mean<=1）自动丢弃重试，最多 60 次，约 30 秒。"""

    # ① MaaFramework（安卓模拟器/PC 都走这条）
    if MC:
        for _ in range(SHOT_RETRY):
            img = MC.screencap()                 # maafw 控制器截图（raw+gzip）
            if img is not None and img.mean() > 1:
                return img
            time.sleep(SHOT_SLEEP)
        raise RuntimeError('截图失败（maafw）')

    # ② PC 端专用路径
    if BACKEND == 'pc':
        for _ in range(SHOT_RETRY):
            img = PCW.screencap()                # PrintWindow / ScreenDC
            if img is not None and img.mean() > 1:
                return img
            time.sleep(SHOT_SLEEP)
        raise RuntimeError('PC 端截图失败（游戏窗口是否被最小化？）')

    # ③ 纯 adb，不依赖 maafw：exec-out screencap -p 拿 PNG 再解码
    for _ in range(SHOT_RETRY):
        raw = adb('exec-out', 'screencap', '-p', True)
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            return img
        time.sleep(SHOT_SLEEP)
    raise RuntimeError('截图失败')


def save(img, tag):
    """把截图存到 farm_logs\HHMMSS_tag.png，返回路径。"""
    p = os.path.join(LOG_DIR, '%s_%s.png' % (time.strftime('%H%M%S'), tag))
    cv2.imwrite(p, img)
    return p


# ---------------------------------------------------------------- 备注
# · MC      —— MaaCtl 实例（maafw 控制器），没有时是 None
# · PCW     —— PCWin 实例（PC 端窗口控制），只在 BACKEND == 'pc' 时存在
# · BACKEND —— 'pc' 或 'emulator'
# · 三种截图方式的分工（maafw 的 MaaAdbScreencapMethodEnum）：
#     RawWithGzip     adb 上 screencap 输出原始像素 + gzip，跳过 PNG 编解码，最快（实测 ~420ms）
#     Encode          adb exec-out screencap -p（PNG）
#     EncodeToFile    先存到设备再 adb pull
#     EmulatorExtras  调模拟器厂商接口（MuMu 的 external_renderer 等），需要额外插件，
#                     这版 maafw 没带，探测会直接报 "No available screencap method"
