"""has_color_badge()：上下多试几个偏移，避免格子中心差几十像素就认不出彩标。"""

SRC = r'''
def has_color_badge(img, gx, gy):
    """格子右上角的彩色（镀层）角标：青蓝色系、不是金色。
    网格行位置会有几十像素的偏差，所以上下多扫几个偏移取最大值。"""
    best = 0.0
    for dy in (0, -25, -50):
        x1 = gx + 40
        y1 = max(0, gy - 110 + dy)
        x2 = gx + 95
        y2 = gy - 45 + dy
        if y2 <= y1 + 4 or x2 <= x1:
            continue
        hsv = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
        cyan = cv2.inRange(hsv, (70, 40, 150), (140, 255, 255)).mean() / 255.0
        if cyan > best:
            best = cyan
    return best > 0.12
'''
