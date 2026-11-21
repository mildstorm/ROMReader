"""GODO / Malum 결선 페이지용 그림 (zif-wiring.html).

사용 (ROMReader 저장소 루트에서):
    python tools/make_clone_images.py

출력
- 24pin/wiring_photo_2732.jpg, 24pin/wiring_photo_2716.jpg
    24핀 칩(2732, 2716)을 2764 결선 그대로 ZIF 3번부터 꽂을 때의 사진 결선도.
    보드 앞면, 보드 뒷면, ZIF 사진에 같은 점퍼 번호를 붙이고, ZIF 40 ↔ 38
    브레드보드 점퍼를 표시합니다.
- GODO/rom_godo.jpg, Malum/rom_malum.jpg
    보드 사진 위에 덤프한 칩의 위치, 라벨, 1번 핀(노란 원)을 표시합니다.

헤더 핀 좌표와 ZIF 다리 좌표는 HART/tools/make_wiring_photos.py와 같은 사진 판독값입니다.
"""
import os
from PIL import Image, ImageOps, ImageDraw, ImageFont

F, FB = "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"
def font(sz, bold=True):
    return ImageFont.truetype(FB if bold else F, sz)
BLK, WHITE, YEL = (0, 0, 0), (255, 255, 255), (255, 215, 0)
COL = {"a": (40, 120, 220), "c": (200, 120, 10), "d": (20, 150, 100), "p": (220, 40, 40),
       "g": (110, 110, 105), "x": (170, 170, 165)}

# ---------------------------------------------------------------- 사진 결선도
# (헤더, 핀, ZIF, 신호, 색). 'x' = 점퍼는 꽂혀 있지만 24핀 칩 다리가 없는 자리.
def wires_24(pin21):
    return [
        ("J117", 1, 10, "A0", "a"), ("J117", 2, 9, "A1", "a"), ("J117", 3, 8, "A2", "a"), ("J117", 4, 7, "A3", "a"),
        ("J117", 5, 6, "A4", "a"), ("J117", 6, 5, "A5", "a"), ("J117", 7, 4, "A6", "a"), ("J117", 8, 3, "A7", "a"),
        ("J117", 9, 1, "칩 없음", "x"),
        ("J121", 1, 37, "A8", "a"), ("J121", 2, 36, "A9", "a"), ("J121", 3, 33, "A10", "a"), ("J121", 4, 35, pin21, "a"),
        ("J121", 5, 2, "칩 없음", "x"), ("J121", 6, 32, "/CE", "c"), ("J121", 7, 34, "/OE", "c"),
        ("J121", 9, 40, "5V→38", "p"), ("J121", 10, 14, "GND", "g"),
        ("J104", 1, 11, "O0", "d"), ("J104", 2, 12, "O1", "d"), ("J104", 3, 13, "O2", "d"), ("J104", 4, 27, "O3", "d"),
        ("J104", 5, 28, "O4", "d"), ("J104", 6, 29, "O5", "d"), ("J104", 7, 30, "O6", "d"), ("J104", 8, 31, "O7", "d"),
        ("J104", 9, 39, "칩 없음", "x")]
W24 = {"2732": wires_24("A11"), "2716": wires_24("VPP")}
PORT = {"J117": "PB", "J121": "PC", "J104": "PF"}
LAB = {"J117": "PORTB", "J121": "PORTC", "J104": "PORTF"}

def grid(origin, pts):
    ox, oy = origin
    return {k: (ox + x, oy + y) for k, (x, y) in pts.items()}
HDR = {
    "J117": grid((1330, 1480), {1: (372, 108), 3: (318, 108), 5: (264, 108), 7: (208, 108), 9: (153, 108),
                                2: (369, 160), 4: (315, 160), 6: (260, 160), 8: (205, 160), 10: (150, 160)}),
    "J121": grid((560, 2100), {1: (165, 382), 3: (170, 325), 5: (176, 270), 7: (182, 215), 9: (190, 158),
                               2: (110, 382), 4: (115, 325), 6: (120, 268), 8: (128, 213), 10: (135, 157)}),
    "J104": grid((1250, 2840), {1: (388, 207), 3: (328, 207), 5: (268, 207), 7: (210, 207), 9: (152, 207),
                                2: (385, 267), 4: (323, 267), 6: (263, 267), 8: (205, 267), 10: (148, 267)}),
}
BHDR = {
    "J117": {1: (1657, 2885), 3: (1570, 2885), 5: (1488, 2885), 7: (1405, 2885), 9: (1322, 2885),
             2: (1657, 2805), 4: (1573, 2805), 6: (1490, 2805), 8: (1407, 2805), 10: (1325, 2805)},
    "J121": {1: (235, 1425), 3: (235, 1515), 5: (235, 1600), 7: (235, 1688), 9: (235, 1772),
             2: (140, 1425), 4: (140, 1515), 6: (140, 1600), 8: (140, 1688), 10: (140, 1772)},
    "J104": {1: (1677, 648), 3: (1587, 648), 5: (1500, 648), 7: (1413, 648), 9: (1325, 648),
             2: (1680, 555), 4: (1590, 555), 6: (1502, 555), 8: (1415, 555), 10: (1325, 555)},
}
ZX_L, ZX_R, ZY1, ZP = 965, 1415, 1940, (2835 - 1940) / 13
def zif_xy(z):
    row = z if z <= 20 else 41 - z
    return (ZX_L if z <= 20 else ZX_R), ZY1 + (row - 1) * ZP


def badge(d, c, num, col, r=26, sz=24):
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=col, outline=WHITE, width=4)
    d.text(c, str(num), font=font(sz), fill=WHITE, anchor="mm")


def mark_headers(img, hdr, wires, pad, r, sz, lab_below=()):
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


def wiring_photo(kind, out):
    wires = W24[kind]
    board = ImageOps.exif_transpose(Image.open("photo/20261121_222148.jpg")).convert("RGB")
    backp = ImageOps.exif_transpose(Image.open("photo/20261121_113651.jpg")).convert("RGB")
    zifp = ImageOps.exif_transpose(Image.open("photo/20261121_222138.jpg")).convert("RGB")

    bc = mark_headers(board, HDR, wires, 45, 26, 24).crop((450, 1050, 2250, 3700))
    bc = bc.resize((int(bc.width * 0.36), int(bc.height * 0.36)), Image.LANCZOS)
    kc = mark_headers(backp, BHDR, wires, 60, 34, 30, lab_below=("J121",)).crop((20, 380, 1900, 3080))
    kc = kc.resize((int(kc.width * 0.36), int(kc.height * 0.36)), Image.LANCZOS)

    zc = zifp.copy()
    d = ImageDraw.Draw(zc)
    # 24핀 칩 자리: ZIF 3–14 / 27–38 (브레드보드 3–14번 줄)
    y0 = ZY1 + 2 * ZP - ZP * 0.6; y1 = ZY1 + 13 * ZP + ZP * 0.6
    for x in range(int(ZX_L - 60), int(ZX_R + 60), 40):
        d.line((x, y0, x + 20, y0), fill=YEL, width=6); d.line((x, y1, x + 20, y1), fill=YEL, width=6)
    d.text(((ZX_L + ZX_R) / 2, y1 + 50), f"{kind} 자리 (3–14줄)", font=font(48), fill=YEL, anchor="mm",
           stroke_width=4, stroke_fill=BLK)
    # ZIF 40 ↔ 38 브레드보드 점퍼
    (xa, ya), (xb, yb) = zif_xy(40), zif_xy(38)
    jx = xa + 150
    d.line((xa + 30, ya, jx, ya, jx, yb, xb + 30, yb), fill=COL["p"], width=12, joint="curve")
    d.text((jx + 20, (ya + yb) / 2), "점퍼\n40↔38", font=font(34), fill=WHITE, anchor="lm",
           stroke_width=5, stroke_fill=BLK)
    for i, (h, p, z, sig, k) in enumerate(wires, 1):
        x, y = zif_xy(z)
        badge(d, (x, y), i, COL[k], r=30, sz=28)
        tx = x - 50 if z <= 20 else x + 50
        if z in (40, 38):
            continue
        d.text((tx, y), sig, font=font(34), fill=WHITE, anchor="rm" if z <= 20 else "lm",
               stroke_width=5, stroke_fill=BLK)
    d.text((zif_xy(38)[0] - 50, zif_xy(38)[1]), "VCC", font=font(34), fill=WHITE, anchor="rm",
           stroke_width=5, stroke_fill=BLK)
    x1, y1_ = zif_xy(1)
    d.text((x1 - 60, y1_ - 70), "ZIF 1번 (레버 쪽)", font=font(40), fill=YEL, anchor="rm", stroke_width=4, stroke_fill=BLK)
    zcc = zc.crop((300, 1450, 2100, 3500))
    zcc = zcc.resize((int(zcc.width * 0.46), int(zcc.height * 0.46)), Image.LANCZOS)

    lines = list(enumerate(wires, 1))
    col_h = 30
    extra = 2
    tbl_h = 70 + col_h * ((len(lines) + 1) // 2 + extra) + 20
    panels = [(bc, "① 보드 앞면 (점퍼 꽂는 쪽)", "7805 왼쪽 위, 7세그먼트 아래"),
              (kc, "② 보드 뒷면 (같은 헤더, 실크 번호 확인)", "위아래로 뒤집은 모습: 7805가 아래. 사각 패드 = 1번"),
              (zcc, "③ 브레드보드 위 ZIF", "칩 1번 = ZIF 3번 (두 칸 내림), 노치는 레버 쪽")]
    Wd = sum(p[0].width for p in panels) + 20 * (len(panels) + 1)
    ph = max(p[0].height for p in panels)
    Ht = 160 + ph + tbl_h
    cv = Image.new("RGB", (Wd, Ht), WHITE)
    d = ImageDraw.Draw(cv)
    pin21 = "A11" if kind == "2732" else "VPP (A11 선, A11 = High일 때 정상 읽기)"
    d.text((20, 12), f"{kind} (24핀): 2764 결선 그대로 + 브레드보드 점퍼 1가닥 (ZIF 40 ↔ 38)", font=font(28), fill=BLK)
    d.text((20, 58), "칩은 ZIF 3–14번 줄에 꽂고, 회색 번호(1, 2, 39번 자리)는 점퍼가 있어도 칩 다리가 없는 곳입니다. "
           "색: 파랑 주소, 주황 /CE·/OE, 초록 데이터, 빨강 5 V, 회색 GND",
           font=font(16, False), fill=BLK)
    x = 20
    for im, t1, t2 in panels:
        d.text((x, 95), t1, font=font(19), fill=BLK)
        d.text((x, 124), t2, font=font(14, False), fill=(80, 80, 80))
        cv.paste(im, (x, 150))
        x += im.width + 20
    ty = 160 + ph
    d.text((20, ty), "번호  보드 헤더 핀  →  ZIF 다리 (브레드보드 줄)  칩 신호", font=font(17), fill=BLK)
    half = (len(lines) + 1) // 2
    for j, (i, (h, p, z, sig, k)) in enumerate(lines):
        cx = 20 + (j // half) * (Wd // 2)
        cy = ty + 36 + (j % half) * col_h
        port = "5V" if p == 9 else "GND" if p == 10 else f"{PORT[h]}{p-1}"
        row = f"{z}줄 왼쪽" if z <= 20 else f"{41 - z}줄 오른쪽"
        badge(d, (cx + 14, cy + 11), i, COL[k], r=13, sz=13)
        s = sig if not (h == "J121" and p == 4) else pin21
        if z == 40:
            s = "칩 없음, ZIF 38로 5 V 공급(브레드보드 점퍼)"
        d.text((cx + 36, cy), f"{h}-{p} ({port})  →  ZIF {z} ({row})  {s}", font=font(16, False),
               fill=(150, 150, 150) if k == "x" else BLK)
    cy = ty + 36 + half * col_h + 8
    d.rectangle((20, cy - 4, 34, cy + 22), fill=COL["p"])
    d.text((44, cy), "브레드보드 점퍼: 오른쪽 1번 줄(ZIF 40, 5 V) ↔ 오른쪽 3번 줄(ZIF 38) → 칩 24번 VCC. "
           "2764를 꽂을 때는 ZIF 38이 NC라 그대로 둬도 됩니다.", font=font(16, False), fill=BLK)
    cv.save(out, quality=88)
    print(out, cv.size)


# ---------------------------------------------------------------- 보드 위치 그림
def pin1_corner(box, notch):
    """노치 방향으로 1번 핀 모서리. 노치 위 → 왼쪽 위, 왼쪽 → 왼쪽 아래, 오른쪽 → 오른쪽 위, 아래 → 오른쪽 아래."""
    x0, y0, x1, y1 = box
    m = 0.07
    dx, dy = (x1 - x0) * m, (y1 - y0) * m
    return {"up": (x0 + dx, y0 + dy), "left": (x0 + dx, y1 - dy),
            "right": (x1 - dx, y0 + dy), "down": (x1 - dx, y1 - dy)}[notch]


def notch_xy(box, notch):
    x0, y0, x1, y1 = box
    return {"up": ((x0 + x1) / 2, y0), "down": ((x0 + x1) / 2, y1),
            "left": (x0, (y0 + y1) / 2), "right": (x1, (y0 + y1) / 2)}[notch]


def annotate(src, chips, scale, title, note):
    """chips: (라벨, 종류·파일, 상자(원본 픽셀), 노치 방향)"""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for lab, sub, box, notch in chips:
        b = [v * scale for v in box]
        d.rectangle(b, outline=(255, 60, 60), width=6)
        nx, ny = notch_xy(b, notch)
        d.ellipse((nx - 14, ny - 14, nx + 14, ny + 14), outline=(0, 200, 255), width=5)
        px, py = pin1_corner(b, notch)
        d.ellipse((px - 18, py - 18, px + 18, py + 18), fill=YEL, outline=BLK, width=3)
        d.text((px, py), "1", font=font(20), fill=BLK, anchor="mm")
        t = f"{lab}  {sub}"
        tx, ty = b[0], b[1] - 12
        tb = d.textbbox((tx, ty), t, font=font(26), anchor="ld")
        d.rectangle((tb[0] - 6, tb[1] - 4, tb[2] + 6, tb[3] + 4), fill=(255, 60, 60))
        d.text((tx, ty), t, font=font(26), fill=WHITE, anchor="ld")
    head = 110
    cv = Image.new("RGB", (im.width, im.height + head), WHITE)
    cv.paste(im, (0, head))
    d = ImageDraw.Draw(cv)
    d.text((16, 10), title, font=font(28), fill=BLK)
    d.text((16, 56), note, font=font(17, False), fill=BLK)
    return cv


def side_by_side(parts, out):
    h = max(p.height for p in parts)
    parts = [p.resize((int(p.width * h / p.height), h), Image.LANCZOS) for p in parts]
    cv = Image.new("RGB", (sum(p.width for p in parts) + 20 * (len(parts) - 1), h), WHITE)
    x = 0
    for p in parts:
        cv.paste(p, (x, 0)); x += p.width + 20
    cv.save(out, quality=88)
    print(out, cv.size)


if __name__ == "__main__":
    wiring_photo("2732", "24pin/wiring_photo_2732.jpg")
    wiring_photo("2716", "24pin/wiring_photo_2716.jpg")

    note = "빨간 상자 = 덤프한 칩, 파란 원 = 노치, 노란 원 = 1번 핀. ZIF에는 노치를 레버 쪽으로 꽂습니다."
    g1 = annotate("GODO/20261122_031454.jpg", [
        ("F", "2732 → GODO/F.bin", (1200, 1260, 2060, 1660), "left"),
        ("E", "2764 → GODO/E.bin", (1210, 1870, 2080, 2250), "left"),
        ("D", "2764 → GODO/D.bin", (1210, 2480, 2080, 2900), "left"),
    ], 0.45, "GODO 메인 ROM (ROM-24)", note + " F는 24핀이라 28핀 소켓의 노치 쪽 두 칸이 비어 있습니다.")
    g2 = annotate("GODO/20261122_032917.jpg", [
        ("KEY 9135N", "MB8516 (2716) → GODO/KEY.bin", (590, 1110, 2840, 2410), "right"),
    ], 0.6, "GODO KEY 자리 (실크 KEY)", "내용은 문자 글꼴로 보입니다.")
    side_by_side([g1, g2], "GODO/rom_godo.jpg")

    m1 = annotate("Malum/20261122_035828.jpg", [
        ("D0", "2732 → Malum/D0.bin", (675, 100, 1890, 725), "right"),
        ("E0", "2732 → Malum/E0.bin", (710, 1600, 1890, 2200), "right"),
        ("F0", "2732 → Malum/F0.bin", (760, 3075, 1925, 3700), "right"),
    ], 0.45, "Malum 메인 ROM (ROM 1, 3, 5)", note + " ROM 2, 4, 6 소켓은 비어 있습니다.")
    m2 = annotate("Malum/20261122_035831.jpg", [
        ("Rom1", "D2716D (2716) → Malum/KEY.bin", (1075, 800, 1850, 2215), "down"),
    ], 0.45, "Malum KEY BOARD (ROM 7)", "내용은 문자 글꼴로 보입니다.")
    side_by_side([m1, m2], "Malum/rom_malum.jpg")
