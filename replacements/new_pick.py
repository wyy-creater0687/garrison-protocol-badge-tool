"""pick_strategy()：一格一格检查，查过的记下来，下次不用再点。

要点：
  · 每格都点开看右侧面板（左→右、上→下）；
  · 面板「已通过模拟 6 次」→ 记进 checked_full.json，下次同一位置直接跳过、不再点；
  · 面板里有「禁用 / 不可用」→ 跳过（红标那种本次不能打）；
  · 点下去面板消失 → 那是"当前选中"那张，重新点回来再判断；
  · 剩下的第一格 → 选中它，交给主流程点「确认选择」；
  · 一页都跳过了 → 往下滑一页（约 4 行）继续；滑到底 → 结束。
"""

SRC = r'''
def pick_strategy(done):
    """从左到右、从上到下一格一格点开检查；查过已满的记下来，下次不再点。"""
    mem = {}
    try:
        f = open('checked_full.json', 'r')
        mem = json.load(f)
        f.close()
    except Exception:
        mem = {}
    tap(1500, 580, 1.1)
    rows = detect_rows(shot())
    if not rows:
        rows = list(GRID_Y)
    changed = False
    for page in range(8):
        for gy in rows:
            if not (GRID_TOP + 40 <= gy <= GRID_BOTTOM + 40):
                continue
            base = int(rows[0] // 50) if rows else 0
            for gx in GRID_X:
                key = str(base) + '|' + str(gx) + '|' + str(int(gy // 50 * 50))
                if mem.get(key, 0) >= TARGET:
                    continue
                tap(gx, gy, 1.1)
                panel = ocr(shot(), (1440, 150, 1920, 800))
                if not panel:
                    tap(gx, gy, 1.1)
                    panel = ocr(shot(), (1440, 150, 1920, 800))
                if not panel:
                    log('读不到面板（跳过）: 格子 ' + str((gx, gy)))
                    continue
                text = ''
                for _it in panel:
                    text += _it[2]
                if ('禁用' in text) or ('不可用' in text):
                    log('跳过（本次禁用 / 红标）: 格子 ' + str((gx, gy)))
                    continue
                cnt = passed_count(panel)
                if cnt >= TARGET:
                    mem[key] = cnt
                    changed = True
                    log('跳过（已通过 ' + str(cnt) + ' 次，已记录）: 格子 ' + str((gx, gy)))
                    continue
                log('选择策略: 第 ' + str(page + 1) + ' 页 格子 ' + str((gx, gy)) + '（' + str(cnt) + '/' + str(TARGET) + '）')
                if changed:
                    try:
                        f = open('checked_full.json', 'w')
                        json.dump(mem, f)
                        f.close()
                    except Exception:
                        pass
                return '未识别'
        log('本页都打满了，向下翻页')
        before = shot()
        scroll_grid()
        after = shot()
        sh = grid_shift(before, after)
        if sh is not None and abs(sh) < 20:
            log('已经滑到底了，全部打满')
            break
        rows = detect_rows(after)
        if not rows:
            break
    if changed:
        try:
            f = open('checked_full.json', 'w')
            json.dump(mem, f)
            f.close()
        except Exception:
            pass
    return None
'''
