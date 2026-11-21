"""보드 사진과 ZIF 사진에 칩 종류별 점퍼 번호를 표시 (zif-wiring.html 탭용).

사용 (ROMReader 저장소 루트에서):
    python HART/tools/make_wiring_photos.py HART

입력: photo/20261121_222148.jpg (결합 보드 앞면), photo/20261121_113651.jpg (베이스 뒷면),
      photo/20261121_222138.jpg (브레드보드 위 ZIF + 2764)
출력: HART/wiring_photo_2764.jpg, wiring_photo_82S129.jpg, wiring_photo_82S123.jpg

같은 번호 배지끼리 점퍼 한 가닥으로 잇습니다. 헤더 핀 위치는 README 2.1절 방향(사진 판독)으로,
ZIF 다리 위치는 사진에서 칩 1번(브레드보드 1번 줄)과 14번(14번 줄)을 재서 정했습니다.
"""
import os, sys
from PIL import Image, ImageOps, ImageDraw, ImageFont

OUTDIR = sys.argv[1]
BOARD = "photo/20261121_222148.jpg"
ZIFP = "photo/20261121_222138.jpg"

F, FB = "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"
def font(sz, bold=True):
    return ImageFont.truetype(FB if bold else F, sz)
BLK, WHITE = (0, 0, 0), (255, 255, 255)
COL = {"a": (40, 120, 220), "c": (200, 120, 10), "d": (20, 150, 100), "p": (220, 40, 40), "g": (110, 110, 105)}

W = {
    "2764": (14, [
        ("J117", 1, 10, "A0", "a"), ("J117", 2, 9, "A1", "a"), ("J117", 3, 8, "A2", "a"), ("J117", 4, 7, "A3", "a"),
        ("J117", 5, 6, "A4", "a"), ("J117", 6, 5, "A5", "a"), ("J117", 7, 4, "A6", "a"), ("J117", 8, 3, "A7", "a"),
        ("J117", 9, 1, "VPP", "p"),
        ("J121", 1, 37, "A8", "a"), ("J121", 2, 36, "A9", "a"), ("J121", 3, 33, "A10", "a"), ("J121", 4, 35, "A11", "a"),
        ("J121", 5, 2, "A12", "a"), ("J121", 6, 32, "/CE", "c"), ("J121", 7, 34, "/OE", "c"), ("J121", 9, 40, "VCC", "p"),
        ("J121", 10, 14, "GND", "g"),
        ("J104", 1, 11, "O0", "d"), ("J104", 2, 12, "O1", "d"), ("J104", 3, 13, "O2", "d"), ("J104", 4, 27, "O3", "d"),
        ("J104", 5, 28, "O4", "d"), ("J104", 6, 29, "O5", "d"), ("J104", 7, 30, "O6", "d"), ("J104", 8, 31, "O7", "d"),
        ("J104", 9, 39, "/PGM", "p")]),
    "82S129": (8, [
        ("J117", 1, 5, "A0", "a"), ("J117", 2, 6, "A1", "a"), ("J117", 3, 7, "A2", "a"), ("J117", 4, 4, "A3", "a"),
        ("J117", 5, 3, "A4", "a"), ("J117", 6, 2, "A5", "a"), ("J117", 7, 1, "A6", "a"), ("J117", 8, 39, "A7", "a"),
        ("J117", 9, 40, "VCC", "p"), ("J117", 10, 8, "GND", "g"),
        ("J121", 6, 37, "/CE1", "c"), ("J121", 10, 38, "/CE2", "g"),
        ("J104", 1, 36, "O1", "d"), ("J104", 2, 35, "O2", "d"), ("J104", 3, 34, "O3", "d"), ("J104", 4, 33, "O4", "d")]),
    "82S123": (8, [
        ("J117", 1, 34, "A0", "a"), ("J117", 2, 35, "A1", "a"), ("J117", 3, 36, "A2", "a"), ("J117", 4, 37, "A3", "a"),
        ("J117", 5, 38, "A4", "a"), ("J117", 9, 40, "VCC", "p"), ("J117", 10, 8, "GND", "g"),
        ("J121", 6, 39, "/CE", "c"),
        ("J104", 1, 1, "O1", "d"), ("J104", 2, 2, "O2", "d"), ("J104", 3, 3, "O3", "d"), ("J104", 4, 4, "O4", "d"),
        ("J104", 5, 5, "O5", "d"), ("J104", 6, 6, "O6", "d"), ("J104", 7, 7, "O7", "d"), ("J104", 8, 33, "O8", "d")]),
}
PORT = {"J117": "PB", "J121": "PC", "J104": "PF"}

# 보드 사진(원본 픽셀)의 헤더 핀 좌표. 사진 판독값
def grid(origin, pts):
    ox, oy = origin
    return {k: (ox + x, oy + y) for k, (x, y) in pts.items()}
HDR = {
    # J117: 위 줄(보드 가장자리 쪽) 오른쪽→왼쪽 1,3,5,7,9 / 아래 줄 2,4,6,8,10
    "J117": grid((1330, 1480), {1: (372, 108), 3: (318, 108), 5: (264, 108), 7: (208, 108), 9: (153, 108),
                                2: (369, 160), 4: (315, 160), 6: (260, 160), 8: (205, 160), 10: (150, 160)}),
    # J121: 오른쪽 열(모듈 쪽) 아래→위 1,3,5,7,9 / 왼쪽 열 2,4,6,8,10
    "J121": grid((560, 2100), {1: (165, 382), 3: (170, 325), 5: (176, 270), 7: (182, 215), 9: (190, 158),
                               2: (110, 382), 4: (115, 325), 6: (120, 268), 8: (128, 213), 10: (135, 157)}),
    # J104: 위 줄(모듈 쪽) 오른쪽→왼쪽 1,3,5,7,9 / 아래 줄 2,4,6,8,10
    "J104": grid((1250, 2840), {1: (388, 207), 3: (328, 207), 5: (268, 207), 7: (210, 207), 9: (152, 207),
                                2: (385, 267), 4: (323, 267), 6: (263, 267), 8: (205, 267), 10: (148, 267)}),
}

# 뒷면 사진(photo/20261121_113651.jpg, 보드를 위아래로 뒤집어 7805가 아래) 헤더 핀 좌표.
# 실크 번호와 사각 패드(1번)에서 직접 읽음. 앞면과 위아래만 바뀌고 좌우는 같음.
BHDR = {
    # PORTB: 아래 줄 오른쪽→왼쪽 1,3,5,7,9 / 위 줄 2,4,6,8,10
    "J117": {1: (1657, 2885), 3: (1570, 2885), 5: (1488, 2885), 7: (1405, 2885), 9: (1322, 2885),
             2: (1657, 2805), 4: (1573, 2805), 6: (1490, 2805), 8: (1407, 2805), 10: (1325, 2805)},
    # PORTC: 오른쪽 열 위→아래 1,3,5,7,9 / 왼쪽 열 2,4,6,8,10
    "J121": {1: (235, 1425), 3: (235, 1515), 5: (235, 1600), 7: (235, 1688), 9: (235, 1772),
             2: (140, 1425), 4: (140, 1515), 6: (140, 1600), 8: (140, 1688), 10: (140, 1772)},
    # PORTF: 아래 줄 오른쪽→왼쪽 1,3,5,7,9 / 위 줄 2,4,6,8,10
    "J104": {1: (1677, 648), 3: (1587, 648), 5: (1500, 648), 7: (1413, 648), 9: (1325, 648),
             2: (1680, 555), 4: (1590, 555), 6: (1502, 555), 8: (1415, 555), 10: (1325, 555)},
}
BACK = "photo/20261121_113651.jpg"

# ZIF 사진(원본 픽셀): 칩 1번 = (965, 1940), 14번 = (965, 2835). 오른쪽 줄 x = 1415.
ZX_L, ZX_R, ZY1, ZP = 965, 1415, 1940, (2835 - 1940) / 13
def zif_xy(z):
    row = z if z <= 20 else 41 - z
    return (ZX_L if z <= 20 else ZX_R), ZY1 + (row - 1) * ZP


def badge(d, c, num, col, r=26, sz=24):
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=col, outline=WHITE, width=4)
    d.text(c, str(num), font=font(sz), fill=WHITE, anchor="mm")


board = ImageOps.exif_transpose(Image.open(BOARD)).convert("RGB")
backp = ImageOps.exif_transpose(Image.open(BACK)).convert("RGB")
zifp = ImageOps.exif_transpose(Image.open(ZIFP)).convert("RGB")
LAB = {"J117": "PORTB", "J121": "PORTC", "J104": "PORTF"}


def mark_headers(img, hdr, wires, pad, r, sz, lab_below=()):
    """헤더 테두리와 이름, 점퍼 번호 배지를 그린 사본을 돌려줌."""
    b = img.copy()
    d = ImageDraw.Draw(b)
    for name, pts in hdr.items():
        xs = [p[0] for p in pts.values()]; ys = [p[1] for p in pts.values()]
        d.rectangle((min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad), outline=(255, 230, 0), width=6)
        lab = f"{name} {LAB[name]}"
        ly = max(ys) + pad + 12 if name in lab_below else min(ys) - pad - 65
        tb = d.textbbox((min(xs) - pad, ly), lab, font=font(44))
        d.rectangle((tb[0] - 8, tb[1] - 6, tb[2] + 8, tb[3] + 6), fill=(255, 230, 0))
        d.text((min(xs) - pad, ly), lab, font=font(44), fill=BLK)
    for i, (h, p, z, sig, k) in enumerate(wires, 1):
        badge(d, hdr[h][p], i, COL[k], r=r, sz=sz)
    return b


for chip, (rows, wires) in W.items():
    # 보드 앞면
    bc = mark_headers(board, HDR, wires, 45, 26, 24).crop((450, 1050, 2250, 3700))
    bc = bc.resize((int(bc.width * 0.36), int(bc.height * 0.36)), Image.LANCZOS)
    # 보드 뒷면 (헤더 핀이 납땜된 쪽, 실크 번호 확인용)
    kc = mark_headers(backp, BHDR, wires, 60, 34, 30, lab_below=("J121",)).crop((20, 380, 1900, 3080))
    kc = kc.resize((int(kc.width * 0.36), int(kc.height * 0.36)), Image.LANCZOS)

    # ZIF
    zc = zifp.copy()
    d = ImageDraw.Draw(zc)
    if rows != 14:
        y0 = ZY1 - ZP * 0.6; y1 = ZY1 + (rows - 1) * ZP + ZP * 0.6
        for x in range(int(ZX_L - 60), int(ZX_R + 60), 40):
            d.line((x, y0, x + 20, y0), fill=(255, 230, 0), width=6); d.line((x, y1, x + 20, y1), fill=(255, 230, 0), width=6)
        d.text(((ZX_L + ZX_R) / 2, y1 + 50), f"{chip} 자리 (1–{rows}줄)", font=font(48), fill=(255, 230, 0), anchor="mm",
               stroke_width=4, stroke_fill=BLK)
    for i, (h, p, z, sig, k) in enumerate(wires, 1):
        x, y = zif_xy(z)
        badge(d, (x, y), i, COL[k], r=30, sz=28)
        tx = x - 50 if z <= 20 else x + 50
        d.text((tx, y), f"{sig}", font=font(34), fill=WHITE, anchor="rm" if z <= 20 else "lm",
               stroke_width=5, stroke_fill=BLK)
    x1, y1 = zif_xy(1)
    d.text((x1 - 60, y1 - 70), "ZIF 1번 (레버 쪽)", font=font(40), fill=(255, 230, 0), anchor="rm", stroke_width=4, stroke_fill=BLK)
    zcc = zc.crop((300, 1450, 2100, 3500))
    zcc = zcc.resize((int(zcc.width * 0.46), int(zcc.height * 0.46)), Image.LANCZOS)

    # 표
    lines = [(i, h, p, z, sig, k) for i, (h, p, z, sig, k) in enumerate(wires, 1)]
    col_h = 30
    tbl_h = 70 + col_h * ((len(lines) + 1) // 2) + 20
    panels = [(bc, "① 보드 앞면 (점퍼 꽂는 쪽)", "7805 왼쪽 위, 7세그먼트 아래"),
              (kc, "② 보드 뒷면 (같은 헤더, 실크 번호 확인)", "위아래로 뒤집은 모습: 7805가 아래. 사각 패드 = 1번"),
              (zcc, "③ 브레드보드 위 ZIF", "레버 위, 칩 노치를 레버 쪽으로")]
    Wd = sum(p[0].width for p in panels) + 20 * (len(panels) + 1)
    ph = max(p[0].height for p in panels)
    Ht = 160 + ph + tbl_h
    cv = Image.new("RGB", (Wd, Ht), WHITE)
    d = ImageDraw.Draw(cv)
    d.text((20, 12), f"{chip}: 같은 번호끼리 점퍼 한 가닥 ({len(wires)}가닥)", font=font(28), fill=BLK)
    d.text((20, 58), "앞면·뒷면은 같은 헤더를 양쪽에서 본 것 (뒷면은 핀 번호 확인용). "
           "색: 파랑 주소, 주황 /CE·/OE, 초록 데이터, 빨강 5 V, 회색 GND",
           font=font(16, False), fill=BLK)
    x = 20
    for im, t1, t2 in panels:
        d.text((x, 95), t1, font=font(19), fill=BLK)
        d.text((x, 124), t2, font=font(14, False), fill=(80, 80, 80))
        cv.paste(im, (x, 150))
        x += im.width + 20
    ty = 160 + ph
    d.text((20, ty), "번호  보드 헤더 핀  →  ZIF 다리 (브레드보드 줄)  신호", font=font(17), fill=BLK)
    half = (len(lines) + 1) // 2
    for j, (i, h, p, z, sig, k) in enumerate(lines):
        cx = 20 + (j // half) * (Wd // 2)
        cy = ty + 36 + (j % half) * col_h
        port = "5V" if p == 9 else "GND" if p == 10 else f"{PORT[h]}{p-1}"
        row = f"{z}줄 왼쪽" if z <= 20 else f"{41 - z}줄 오른쪽"
        badge(d, (cx + 14, cy + 11), i, COL[k], r=13, sz=13)
        d.text((cx + 36, cy), f"{h}-{p} ({port})  →  ZIF {z} ({row})  {sig}", font=font(16, False), fill=BLK)
    out = os.path.join(OUTDIR, f"wiring_photo_{chip}.jpg")
    cv.save(out, quality=88)
    print(out, cv.size)
