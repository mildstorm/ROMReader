"""칩 종류별 ROM 위치·1번 핀 그림 (zif-wiring.html 탭용).

사용 (HART 저장소 루트에서):
    python <ROMReader>/HART/tools/make_rom_type_images.py <출력 폴더>

출력: rom_2764.jpg, rom_82S129.jpg, rom_82S123.jpg
- 앞면 기준 사진 202813 위에 data/bom.csv 좌표(1000x1600 격자)로 칩을 표시.
- 세로 칩 1번 핀 = 오른쪽 아래(노치 아래) 보드 규칙. U45, U46은 확대 사진 212346에서 노치 확인.
  나머지는 규칙으로 추정한 것이라 뽑기 전에 노치를 확인.
- 아래에 뽑은 칩 핀 배치(노치 위)를 함께 그림.
"""
import csv, os, sys
from PIL import Image, ImageOps, ImageDraw, ImageFont

OUTDIR = sys.argv[1]
FRONT = "photos/overview/front/202813_front-flat_layout-ref.jpg"
rows = {r["ref"]: r for r in csv.DictReader(open("data/bom.csv", encoding="utf-8"))}

F, FB = "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"
def font(sz, bold=True):
    return ImageFont.truetype(FB if bold else F, sz)
BLK, WHITE, RED, BLUE, YEL, GRN = (0, 0, 0), (255, 255, 255), (220, 20, 20), (0, 90, 220), (255, 215, 0), (0, 140, 60)

PINS = {
    "2764": ["VPP", "A12", "A7", "A6", "A5", "A4", "A3", "A2", "A1", "A0", "O0", "O1", "O2", "GND",
             "O3", "O4", "O5", "O6", "O7", "/CE", "A10", "/OE", "A11", "A9", "A8", "NC", "/PGM", "VCC"],
    "82S129": ["A6", "A5", "A4", "A3", "A0", "A1", "A2", "GND", "O4", "O3", "O2", "O1", "/CE1", "/CE2", "A7", "VCC"],
    "82S123": ["O1", "O2", "O3", "O4", "O5", "O6", "O7", "GND", "O8", "A0", "A1", "A2", "A3", "A4", "/CE", "VCC"],
}
TYPES = {  # 종류: (클러스터 목록, 칩 라벨, 노치 확인된 칩)
    "2764": ([["U45", "U46"], ["U65"], ["U70"]],
             {"U45": "C/D8", "U46": "EF5", "U65": "VD5", "U70": "CHR P4"}, {"U45", "U46"}),
    "82S129": ([["U17", "U18"], ["U36", "U38", "U50", "U51"]],
               {"U17": "?", "U18": "M", "U36": "3", "U38": "", "U50": "1", "U51": "2"}, set()),
    "82S123": ([["U5"]], {"U5": ""}, set()),
}

front = ImageOps.exif_transpose(Image.open(FRONT)).convert("RGB")
SX, SY = front.width / 1000, front.height / 1600


def box(ref):
    r = rows[ref]
    return float(r["x0"]) * SX, float(r["y0"]) * SY, float(r["x1"]) * SX, float(r["y1"]) * SY


def cluster_panel(refs, labels, checked, n, scale):
    bs = [box(r) for r in refs]
    m = 70
    x0, y0 = min(b[0] for b in bs) - m, min(b[1] for b in bs) - m - 20
    x1, y1 = max(b[2] for b in bs) + m, max(b[3] for b in bs) + m
    im = front.crop((int(x0), int(y0), int(x1), int(y1)))
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    M = lambda x, y: ((x - x0) * scale, (y - y0) * scale)
    half = n // 2
    for ref, b in zip(refs, bs):
        a, c = M(b[0], b[1]), M(b[2], b[3])
        ok = ref in checked
        col = GRN if ok else RED
        d.rectangle((a[0], a[1], c[0], c[1]), outline=col, width=4)
        t = ref + (f" {labels[ref]}" if labels[ref] else "")
        tb = d.textbbox(((a[0] + c[0]) / 2, a[1] - 18), t, font=font(18), anchor="mm")
        d.rectangle((tb[0] - 5, tb[1] - 3, tb[2] + 5, tb[3] + 3), fill=col)
        d.text(((a[0] + c[0]) / 2, a[1] - 18), t, font=font(18), fill=WHITE, anchor="mm")
        h = c[1] - a[1]
        top, bot = a[1] + 0.06 * h, c[1] - 0.04 * h
        for num, (px, py) in {1: (c[0], bot), half: (c[0], top), half + 1: (a[0], top), n: (a[0], bot)}.items():
            r = 14
            d.ellipse((px - r, py - r, px + r, py + r), fill=YEL if num == 1 else WHITE, outline=col, width=3)
            d.text((px, py), str(num), font=font(13), fill=BLK, anchor="mm")
    return im


def chip_drawing(kind):
    names = PINS[kind]
    n = len(names)
    half = n // 2
    pitch = 34
    bh = pitch * (half - 1) + 40
    W, H = 470, bh + 110
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    d.text((16, 8), f"뽑은 {kind} (글자 면 위, 노치 위)", font=font(19), fill=BLK)
    d.text((16, 38), "1번 = 노치 왼쪽, 반시계 방향", font=font(15, False), fill=BLK)
    bx, by, bw = 175, 80, 120
    d.rounded_rectangle((bx, by, bx + bw, by + bh), 8, fill=(110, 95, 90), outline=BLK, width=2)
    d.pieslice((bx + bw / 2 - 15, by - 15, bx + bw / 2 + 15, by + 15), 0, 180, fill=WHITE, outline=BLK)
    d.ellipse((bx + 12, by + 12, bx + 22, by + 22), fill=WHITE)
    d.text((bx + bw / 2, by + bh / 2), kind, font=font(18), fill=WHITE, anchor="mm")
    for i in range(half):
        y = by + 20 + i * pitch
        l, r = i + 1, n - i
        d.rectangle((bx - 18, y - 5, bx, y + 5), fill=(200, 200, 200), outline=BLK)
        d.rectangle((bx + bw, y - 5, bx + bw + 18, y + 5), fill=(200, 200, 200), outline=BLK)
        d.text((bx - 26, y), f"{names[l-1]}  {l}", font=font(15), fill=RED if l == 1 else BLK, anchor="rm")
        d.text((bx + bw + 26, y), f"{r}  {names[r-1]}", font=font(15), fill=BLK, anchor="lm")
    return im


for kind, (clusters, labels, checked) in TYPES.items():
    n = len(PINS[kind])
    scale = 0.9 if kind == "2764" else 1.3
    panels = [cluster_panel(c, labels, checked, n, scale) for c in clusters]
    chip = chip_drawing(kind)
    top_w = sum(p.width for p in panels) + 20 * (len(panels) - 1)
    top_h = max(p.height for p in panels)
    W = max(top_w, chip.width + 420) + 40
    H = 90 + top_h + 20 + chip.height + 20
    cv = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(cv)
    d.text((20, 10), f"{kind}: 보드 앞면 위치와 1번 핀 (슬롯이 위)", font=font(24), fill=BLK)
    note = ("초록 = 노치 확인됨, 빨강 = 보드 규칙(세로 칩 1번 = 오른쪽 아래)으로 추정 → 뽑기 전 노치 확인"
            if checked else "보드 규칙(세로 칩 1번 = 오른쪽 아래)으로 추정 → 뽑기 전 노치(반달 홈)가 아래쪽인지 확인")
    d.text((20, 50), note, font=font(15, False), fill=BLK)
    x = 20
    for p in panels:
        cv.paste(p, (x, 90))
        x += p.width + 20
    cv.paste(chip, (20, 90 + top_h + 20))
    tx, ty = chip.width + 50, 90 + top_h + 40
    zif = ("칩 1–14 → ZIF 1–14, 15–28 → ZIF 27–40" if n == 28 else "칩 1–8 → ZIF 1–8, 9–16 → ZIF 33–40")
    for t, b in [("ZIF에 꽂을 때", True), ("노치를 레버 쪽으로, 칩 1번 = ZIF 1번", False), (zif, False),
                 ("", False), ("보드 앞면에서", True), ("노치 = 칩 아래쪽 끝, 1번 = 오른쪽 아래", False),
                 ("오른쪽 줄 아래→위로 1번부터", False)]:
        d.text((tx, ty), t, font=font(17, b), fill=BLK)
        ty += 30
    out = os.path.join(OUTDIR, f"rom_{kind}.jpg")
    cv.save(out, quality=88)
    print(out, cv.size)
