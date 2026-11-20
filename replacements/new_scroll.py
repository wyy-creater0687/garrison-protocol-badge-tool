"""scroll_grid()：一次翻页拖动约 780px（比原来 560 多、比两段 1120 少）。"""

SRC = r'''
def scroll_grid():
    """慢速向上拖动策略列表约 4 行（780px），结束前停顿消除惯性"""
    x = 1000
    touch('DOWN', x, 1000)
    drag_path(x, 1000, x, 220, 16)
    time.sleep(0.45)
    touch('UP', x, 220)
    time.sleep(0.8)
'''
