"""U45, U46 (2764) 핀 번호를 HART 앞면·뒷면 기준 사진에 표시.

사용 (HART 저장소 루트에서):
    python <ROMReader>/HART/tools/annotate_u45_u46_pins.py <출력.jpg>

- 앞면 기준 사진 202813, 뒷면 기준 사진 203240 (HART photos/overview).
- 노치: 확대 사진 212346에서 두 칩 모두 앞면 기준 아래쪽 끝 → 1번 핀 오른쪽 아래.
  오른쪽 줄 아래→위 1–14, 왼쪽 줄 위→아래 15–28.
- 뒷면 좌표는 data/front_back_registration.json 의 front_to_back 다항식으로 옮김.
"""
import json, sys
from PIL import Image, ImageOps, ImageDraw, ImageFont

OUT = sys.argv[1]
FRONT = "photos/overview/front/202813_front-flat_layout-ref.jpg"
BACK = "photos/overview/back/203240_back-flat_registration-ref.jpg"
REG = json.load(open("data/front_back_registration.json", encoding="utf-8"))

F, FB = "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"
def font(sz, bold=True):
    return ImageFont.truetype(FB if bold else F, sz)
BLK, WHITE, RED, BLUE, YEL, GRAY = (0, 0, 0), (255, 255, 255), (220, 20, 20), (0, 90, 220), (255, 215, 0), (120, 120, 120)

# 2764 핀 이름
NAMES = ["VPP", "A12", "A7", "A6", "A5", "A4", "A3", "A2", "A1", "A0", "O0", "O1", "O2", "GND",
         "O3", "O4", "O5", "O6", "O7", "/CE", "A10", "/OE", "A11", "A9", "A8", "NC", "/PGM", "VCC"]

# 앞면 기준 사진(원본 픽셀)에서 소켓 다리 줄 위치. 판독값 (crop 원점 835,1765 + crop 좌표)
OX, OY = 835, 1765
CHIPS = {  # ref: (왼쪽 줄 x, 오른쪽 줄 x)
    "U45 C/D8": (OX + 46, OX + 250),
    "U46 EF5": (OX + 300, OX + 506),
}
Y_TOP, Y_BOT = OY + 95, OY + 555          # 맨 위, 맨 아래 다리 중심
PITCH = (Y_BOT - Y_TOP) / 13


def front_pins(xl, xr):
    """앞면: 오른쪽 줄 아래→위 1–14, 왼쪽 줄 위→아래 15–28."""
    p = {}
    for i in range(14):
        p[i + 1] = (xr, Y_BOT - i * PITCH)
        p[15 + i] = (xl, Y_TOP + i * PITCH)
    return p


def poly(coef, x, y):
    x, y = x / 1000, y / 1000
    t = [1, x, y, x * x, x * y, y * y, x ** 3, x * x * y, x * y * y, y ** 3]
    return (sum(c[0] * v for c, v in zip(coef, t)), sum(c[1] * v for c, v in zip(coef, t)))


def panel(img, pts_by_chip, box, scale, title, sub):
    x0, y0, x1, y1 = box
    im = img.crop(box).resize((int((x1 - x0) * scale), int((y1 - y0) * scale)), Image.LANCZOS)
    cv = Image.new("RGB", (im.width + 40, im.height + 120), WHITE)
    cv.paste(im, (20, 100))
    d = ImageDraw.Draw(cv)
    d.text((20, 10), title, font=font(26), fill=BLK)
    d.text((20, 52), sub, font=font(17, False), fill=BLK)
    M = lambda p: (20 + (p[0] - x0) * scale, 100 + (p[1] - y0) * scale)
    for name, pins in pts_by_chip.items():
        cxs = [M(p)[0] for p in pins.values()]
        top = min(M(p)[1] for p in pins.values())
        tb = d.textbbox(((min(cxs) + max(cxs)) / 2, top - 34), name, font=font(18), anchor="mm")
        d.rectangle((tb[0] - 6, tb[1] - 4, tb[2] + 6, tb[3] + 4), fill=RED)
        d.text(((min(cxs) + max(cxs)) / 2, top - 34), name, font=font(18), fill=WHITE, anchor="mm")
        for n, p in pins.items():
            c = M(p)
            key = n in (1, 14, 15, 28)
            r = 13 if key else 10
            fill = YEL if n == 1 else WHITE
            d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=fill, outline=RED if key else BLUE, width=3)
            d.text(c, str(n), font=font(13 if n < 10 else 11), fill=BLK, anchor="mm")
    return cv


front = ImageOps.exif_transpose(Image.open(FRONT)).convert("RGB")
back = ImageOps.exif_transpose(Image.open(BACK)).convert("RGB")

fpins = {k: front_pins(*v) for k, v in CHIPS.items()}
bpins = {k: {n: poly(REG["front_to_back"], *p) for n, p in v.items()} for k, v in fpins.items()}

fb = (OX - 40, OY + 30, OX + 590, OY + 620)
pA = panel(front, fpins, fb, 1.0,
           "앞면 (부품면, 슬롯이 위) — 사진 202813",
           "노치 = 아래쪽 끝. 노란 원 = 1번 (오른쪽 아래)")

bx = [p[0] for v in bpins.values() for p in v.values()]
by = [p[1] for v in bpins.values() for p in v.values()]
bb = (int(min(bx)) - 80, int(min(by)) - 70, int(max(bx)) + 80, int(max(by)) + 40)
pB = panel(back, bpins, bb, 1.0,
           "뒷면 (납땜면) — 사진 203240",
           "좌우가 바뀜: 노란 원 = 1번 (왼쪽 아래)")

# 뽑은 칩 그림 (위에서 본 모습, 노치 위)
cw, chh = 560, 640
pC = Image.new("RGB", (cw, chh), WHITE)
d = ImageDraw.Draw(pC)
d.text((20, 10), "뽑은 칩 (글자 면을 위로, 노치를 위쪽으로)", font=font(22), fill=BLK)
d.text((20, 46), "1번 = 노치 왼쪽. 반시계 방향으로 번호 증가", font=font(16, False), fill=BLK)
bx0, by0, bw, bh = 200, 100, 160, 500
d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), 8, fill=(110, 95, 90), outline=BLK, width=2)
d.pieslice((bx0 + bw / 2 - 18, by0 - 18, bx0 + bw / 2 + 18, by0 + 18), 0, 180, fill=WHITE, outline=BLK)
d.text((bx0 + bw / 2, by0 + bh / 2), "2764", font=font(22), fill=WHITE, anchor="mm")
d.ellipse((bx0 + 14, by0 + 14, bx0 + 26, by0 + 26), fill=WHITE)
pp = (bh - 40) / 13
for i in range(14):
    y = by0 + 20 + i * pp
    l, r = i + 1, 28 - i
    d.rectangle((bx0 - 22, y - 6, bx0, y + 6), fill=(200, 200, 200), outline=BLK)
    d.rectangle((bx0 + bw, y - 6, bx0 + bw + 22, y + 6), fill=(200, 200, 200), outline=BLK)
    d.text((bx0 - 30, y), f"{NAMES[l-1]}  {l}", font=font(15), fill=RED if l == 1 else BLK, anchor="rm")
    d.text((bx0 + bw + 30, y), f"{r}  {NAMES[r-1]}", font=font(15), fill=BLK, anchor="lm")

# 합치기
W = pA.width + pB.width + 20
H = max(pA.height, pB.height) + pC.height + 120
cv = Image.new("RGB", (max(W, pC.width + 40), H), WHITE)
cv.paste(pA, (0, 0))
cv.paste(pB, (pA.width + 20, 0))
yC = max(pA.height, pB.height) + 10
cv.paste(pC, (20, yC))
d = ImageDraw.Draw(cv)
tx = pC.width + 60
lines = [
    ("ZIF에 꽂을 때", True),
    ("• 노치를 ZIF 레버 쪽으로, 칩 1번을 ZIF 1번(왼쪽 줄 맨 위)에", False),
    ("• 칩 1–14번 → ZIF 1–14번, 15–28번 → ZIF 27–40번", False),
    ("• ZIF 15–26번은 비움", False),
    ("", False),
    ("확인", True),
    ("• 노치: 확대 사진 212346에서 두 칩 모두 앞면 아래쪽 끝", False),
    ("• 보드 규칙(세로 칩 1번 = 오른쪽 아래)과 같음", False),
    ("• 뒷면 위치는 앞·뒤 정합(평균 오차 약 2 px)으로 옮긴 것", False),
    ("• 다리 위치는 사진 판독값이라 몇 px 어긋날 수 있음", False),
]
y = yC + 20
for t, b in lines:
    d.text((tx, y), t, font=font(18, b), fill=BLK)
    y += 32
cv.save(OUT, quality=90)
print(cv.size)
