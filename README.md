# ATmega128 FreeRTOS

NewTC **AB-M128Pro-A** 베이스보드 위에 **AM-128RAM** CPU 모듈을 꽂은 구성에서 동작하는 FreeRTOS 펌웨어입니다. MCU는 ATmega128, 클럭은 모듈 크리스탈 **16 MHz**입니다.

펌웨어 소스는 `FreeRTOSStackFinalSerial/FreeRTOS`에 있습니다.

## 1. 보드 결합

두 보드를 헤더로 포개어 사용합니다.

| 보드 | 역할 |
| --- | --- |
| AB-M128Pro-A | 베이스. 12 V 어댑터, 7805(5 V), 4자리 7세그먼트, LED(PG0/PG1), UART1 핀헤더, ISP |
| AM-128RAM | CPU 모듈. ATmega128-16AU, 16 MHz 크리스탈, 32 KB SRAM(IS62C256-70) |

모듈을 베이스 소켓에 끝까지 꽂습니다. 모듈 헤더의 XTAL 핀(23, 24)은 오픈이라 베이스의 7.3728 MHz 발진은 쓰지 않고, MCU는 모듈의 16 MHz로 동작합니다. 전원은 베이스의 12 V 어댑터입니다.

외부 SRAM 배선은 다음과 같습니다. 현재 펌웨어는 7세그먼트와 핀이 겹치므로 XMEM을 켜지 않고, PC7(/CS)을 High로 잡아 SRAM을 버스에서 떼어 둡니다.

| SRAM | MCU |
| --- | --- |
| A0–A7 | PA, ALE(PG2)로 74LVC573에 래치 |
| A8–A14 | PC0–PC6 |
| /CS | PC7 (Low일 때 선택, 0x0000–0x7FFF) |
| /WE | PG0 |
| /OE | PG1 |

회로와 매뉴얼은 `doc/AB-M128Pro-A`, `doc/AM-128RAM`에 있습니다. 결합 사진은 `doc/AB-M128Pro-A_AM-128RAM.jpg`입니다.

## 2. 케이블 결선

USB 허브의 포트 스위치는 해당 동글의 USB 전원만 켜고 끕니다. 보드 전원은 12 V 어댑터입니다. 플래시할 때는 STK500 포트를 켜고, CLI를 볼 때는 FT232 포트를 켭니다. 둘 다 켜 두어도 됩니다. STK500이 프로그래밍 모드를 빠져나오면 리셋은 풀립니다.

### ISP (플래시)

USB STK500을 보드 ISP 커넥터에 연결합니다. 이 PC에서는 **COM10**으로 잡힙니다.

### CLI 시리얼 (FT232 TTL)

베이스보드 UART1 헤더를 사용합니다. 모듈의 3핀 RS-232 커넥터(MAX232, ±12 V)에는 연결하지 않습니다.

UART1 실크 핀:

| 핀 | 신호 |
| --- | --- |
| 1 | VCC |
| 2 | TX1 (MCU PD3) |
| 3 | RX1 (MCU PD2) |
| 4 | GND |

FT232는 TTL, 점퍼 **5 V**. 보드가 12 V 어댑터로 전원을 받으므로 FT232 VCC는 연결하지 않습니다. DTR, CTS도 연결하지 않습니다.

| FT232 | 보드 UART1 |
| --- | --- |
| GND | 4 GND |
| RX | 2 TX1 |
| TX | 3 RX1 |
| VCC | 연결 안 함 |

이 PC에서 FT232는 **COM11**입니다. 터미널은 **9600 8N1**, 흐름 제어 없음입니다.

## 3. 플래싱 (avrdude)

avrdude 8.3 소스는 `avrdude/`에 있고, Windows 빌드 결과는 다음 경로입니다.

- `avrdude/build-ucrt64/src/avrdude.exe`
- `avrdude/build-ucrt64/src/avrdude.conf`

실행 시 `D:\msys64\ucrt64\bin`이 PATH에 있어야 합니다. libusb, hidapi, libftdi, readline이 여기 있습니다. STK500은 v2, **115200 8N1**, 대상은 `m128`입니다.

펌웨어 빌드 (MSYS2, avr-gcc):

```bash
export PATH=/ucrt64/bin:$PATH
cd FreeRTOSStackFinalSerial/FreeRTOS
make
```

산출물: `FreeRTOSStackFinalSerial/FreeRTOS/build/FreeRTOS.hex`

플래시 (PowerShell, COM 번호는 장치 관리자 기준):

```powershell
$env:PATH = "D:\msys64\ucrt64\bin;" + $env:PATH
& .\avrdude\build-ucrt64\src\avrdude.exe `
  -C .\avrdude\build-ucrt64\src\avrdude.conf `
  -c stk500v2 -P COM10 -b 115200 -p m128 `
  -U flash:w:FreeRTOSStackFinalSerial\FreeRTOS\build\FreeRTOS.hex:i
```

쓰기가 끝나면 avrdude가 플래시를 다시 읽어 검증합니다. CLI 세션(COM11)은 그대로 두고, 플래시 후 보드를 리셋하면 부팅 로고와 프롬프트가 나옵니다.

## 4. STK500 드라이버

STK500 USB-시리얼(Prolific) 드라이버는 `driver/STK500-COM-Driver.zip`에 있습니다. 장치 관리자에 STK500이 없거나 노란 느낌표가 있으면 이 압축을 풀어 설치합니다. 설치 후 포트 번호(이 PC는 COM10)를 확인하고 위 avrdude 명령의 `-P`에 맞춥니다.

FT232는 별도입니다. FTDI 드라이버가 잡히면 "USB Serial Port"로 보이며, 이 PC에서는 COM11입니다.

## 5. FreeRTOS 구현

클럭 16 MHz, 틱 1 ms (`configTICK_RATE_HZ` 1000). 힙은 내부 SRAM **2048바이트**만 사용합니다. 링커 데이터 영역도 내부 4 KB(`__DATA_REGION_LENGTH__=0x1000`)로 제한합니다. PORTA와 PC0–PC3이 7세그먼트이므로 외부 버스(XMEM)는 꺼 둔 상태입니다. 외부 SRAM과 7세그먼트는 동시에 쓸 수 없습니다.

태스크:

| 태스크 | 우선순위 | 동작 |
| --- | --- | --- |
| SEG | idle+6 | 4자리 7세그먼트. 1 ms마다 한 자리씩 다중화, 1초마다 0000–9999 증가(앞자리 0 표시). 왼쪽(PC0)이 천의 자리 |
| LED | idle+5 | PG0, PG1을 250 ms 간격으로 번갈아 토글. High가 켜짐 |
| SHELL | idle+4 | USART1 CLI |

7세그먼트는 공통 캐소드, 세그먼트 활성 High입니다. 폰트는 0=`0x3F` … 9=`0x67`. 자릿수 PC0–PC3은 활성 Low입니다. PC7은 High로 고정해 SRAM이 버스를 구동하지 않게 합니다. PG0/PG1은 SRAM /WE, /OE이기도 하지만 /CS가 High이면 GPIO로 토글해도 SRAM은 응답하지 않습니다.

### CLI

USART1, **9600 8N1**. 프롬프트는 `[root@FreeRTOS]#`입니다. 부팅 시 ASCII 고양이 로고를 출력한 뒤 프롬프트가 나옵니다. 9600 bps라 로고가 다 그려지기까지 몇 초 걸립니다. 터미널 폭은 80칸 이상을 권합니다.

Enter는 CR 또는 LF입니다. 입력은 에코되고, Backspace(0x08, 0x7F)를 처리합니다.

| 명령 | 설명 |
| --- | --- |
| `help` | 등록된 명령 목록 |
| `set-net <ip> <subnet> <gateway>` | 인자 3개가 필요합니다. IP와 서브넷만 저장하고 게이트웨이는 사용하지 않습니다 |
| `get-net` | 고정 MAC과 `8.8.8.8`을 출력합니다. `set-net`으로 저장한 값은 반영되지 않습니다 |

네트워크 명령은 실제 이더넷 설정이 아닙니다. 저장한 문자열을 보여주는 예제입니다.
