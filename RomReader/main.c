/*
 * ATmega128 ROM reader (bare metal, no RTOS).
 *
 * Board: AB-M128Pro-A base + AM-128RAM CPU module, 16 MHz.
 * Reads 2764 EPROM (8K x 8), 82S129/82S126 PROM (256 x 4), 82S123 PROM (32 x 8).
 * Read only: no pin is ever driven above VCC, no program pulse exists.
 * The chip type is fixed at build time (see "chip" below); one ZIF socket is
 * rewired per chip type as README section 2 shows.
 *
 * Pins (base board 10-pin headers, pin 9 = VCC, pin 10 = GND):
 *   J117 PORTB  PB0-PB7  -> A0-A7      (output)
 *   J121 PORTC  PC0-PC4  -> A8-A12     (output)
 *               PC5      -> /CE        (output, idle High)
 *               PC6      -> /OE        (output, idle High)
 *               PC7      -> not wired. Kept High = module SRAM /CS off.
 *   J104 PORTF  PF0-PF7  <- D0-D7      (input, internal pull-up)
 *   PORTA       driven Low so the 7-segment stays dark.
 *   PG0 LED     on while a command runs, PG1 LED on after a read error.
 *
 * Serial: USART1 (UART1 header, FT232 TTL), 38400 8N1.
 */
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <util/delay.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#define BAUD        38400UL
#define UBRR_VALUE  ((F_CPU / (16UL * BAUD)) - 1)   /* 25 at 16 MHz, 0.2 % error */

#define CE_BIT      PC5
#define OE_BIT      PC6
#define SRAM_CS_BIT PC7
#define ADDR_HI_MASK 0x1F                          /* PC0-PC4 */

#define READS_PER_ADDR 3

/*
 * ---------- chip, fixed at build time ----------
 * One firmware per chip type: `make CHIP=2764`, `make CHIP=82S129`,
 * `make CHIP=82S123`. Flash the one that matches the ZIF wiring.
 */

typedef struct {
    const char *name;   /* in flash */
    uint16_t size;      /* bytes */
    uint8_t mask;       /* valid data bits */
} chip_t;

/*
 * ZIF pin of every wired MCU line, for the `wires` check (README section 2).
 * line 0-12 = A0-A12 (PB0-PB7, PC0-PC4), LINE_CE = /CE (PC5), LINE_OE = /OE
 * (PC6). data_zif[n] = ZIF pin of data bit n (PFn).
 */
#define LINE_CE 13
#define LINE_OE 14

typedef struct {
    uint8_t line;
    uint8_t zif;
} wire_t;

#if defined(CHIP_2764)
static const char chip_name[] PROGMEM = "2764";
static const chip_t chip = { chip_name, 8192, 0xFF };
static const wire_t addr_wires[] PROGMEM = {
    {0, 10}, {1, 9}, {2, 8}, {3, 7}, {4, 6}, {5, 5}, {6, 4}, {7, 3},
    {8, 37}, {9, 36}, {10, 33}, {11, 35}, {12, 2}, {LINE_CE, 32}, {LINE_OE, 34},
};
static const uint8_t data_zif[] PROGMEM = { 11, 12, 13, 27, 28, 29, 30, 31 };
#elif defined(CHIP_82S129)
static const char chip_name[] PROGMEM = "82S129";
static const chip_t chip = { chip_name, 256, 0x0F };
/* Not in order on the chip: A0-A2 are pins 5-7, A3-A6 pins 4-1, A7 pin 15. */
static const wire_t addr_wires[] PROGMEM = {
    {0, 5}, {1, 6}, {2, 7}, {3, 4}, {4, 3}, {5, 2}, {6, 1}, {7, 39}, {LINE_CE, 37},
};
static const uint8_t data_zif[] PROGMEM = { 36, 35, 34, 33 };
#elif defined(CHIP_82S123)
static const char chip_name[] PROGMEM = "82S123";
static const chip_t chip = { chip_name, 32, 0xFF };
static const wire_t addr_wires[] PROGMEM = {
    {0, 34}, {1, 35}, {2, 36}, {3, 37}, {4, 38}, {LINE_CE, 39},
};
static const uint8_t data_zif[] PROGMEM = { 1, 2, 3, 4, 5, 6, 7, 33 };
#else
#error "build with CHIP=2764, CHIP=82S129 or CHIP=82S123"
#endif

static uint8_t error_led = 0;

/* ---------- UART1 ---------- */

static void uart_init(void)
{
    UBRR1H = (uint8_t)(UBRR_VALUE >> 8);
    UBRR1L = (uint8_t)UBRR_VALUE;
    UCSR1A = 0;
    UCSR1B = (1 << RXEN1) | (1 << TXEN1);
    UCSR1C = (1 << UCSZ11) | (1 << UCSZ10);         /* 8N1 */
}

static void uart_putc(char c)
{
    while (!(UCSR1A & (1 << UDRE1)))
        ;
    UDR1 = (uint8_t)c;
}

static char uart_getc(void)
{
    while (!(UCSR1A & (1 << RXC1)))
        ;
    return (char)UDR1;
}

static void puts_P_(const char *s)
{
    char c;
    while ((c = (char)pgm_read_byte(s++)) != 0)
        uart_putc(c);
}
#define PUTS(s) puts_P_(PSTR(s))

static void put_nl(void)
{
    uart_putc('\r');
    uart_putc('\n');
}

static void put_hex4(uint8_t v)
{
    v &= 0x0F;
    uart_putc((char)(v < 10 ? '0' + v : 'A' + v - 10));
}

static void put_hex8(uint8_t v)
{
    put_hex4(v >> 4);
    put_hex4(v);
}

static void put_hex16(uint16_t v)
{
    put_hex8((uint8_t)(v >> 8));
    put_hex8((uint8_t)v);
}

static void put_dec(uint16_t v)
{
    char buf[6];
    uint8_t i = 0;
    do {
        buf[i++] = (char)('0' + v % 10);
        v /= 10;
    } while (v);
    while (i)
        uart_putc(buf[--i]);
}

/* ---------- ROM bus ---------- */

static void bus_init(void)
{
    /* 7-segment segments (PORTA) Low: no LED current whatever PORTC does. */
    PORTA = 0x00;
    DDRA = 0xFF;

    PORTB = 0x00;                                   /* A0-A7 */
    DDRB = 0xFF;

    /* A8-A12 Low, /CE /OE High, SRAM /CS High. */
    PORTC = (1 << CE_BIT) | (1 << OE_BIT) | (1 << SRAM_CS_BIT);
    DDRC = 0xFF;

    /* PF4-PF7 are JTAG pins while JTAGEN is programmed: JTD needs two writes
     * within four cycles. */
    uint8_t m = MCUCSR | (1 << JTD);
    MCUCSR = m;
    MCUCSR = m;

    DDRF = 0x00;
    PORTF = 0xFF;                                   /* pull-ups on D0-D7 */

    /* PG0 busy LED, PG1 error LED (base board, High = on). */
    PORTG &= (uint8_t)~((1 << PG0) | (1 << PG1));
    DDRG |= (1 << PG0) | (1 << PG1);
}

static void led_busy(uint8_t on)
{
    if (on)
        PORTG |= (1 << PG0);
    else
        PORTG &= (uint8_t)~(1 << PG0);
}

static void led_error(uint8_t on)
{
    error_led = on;
    if (on)
        PORTG |= (1 << PG1);
    else
        PORTG &= (uint8_t)~(1 << PG1);
}

static void set_addr(uint16_t a)
{
    PORTB = (uint8_t)a;
    PORTC = (uint8_t)((PORTC & (uint8_t)~ADDR_HI_MASK) | ((a >> 8) & ADDR_HI_MASK));
}

static void chip_enable(uint8_t on)
{
    if (on)
        PORTC &= (uint8_t)~((1 << CE_BIT) | (1 << OE_BIT));
    else
        PORTC |= (1 << CE_BIT) | (1 << OE_BIT);
}

/* One raw sample. 2 us covers a 450 ns NMOS EPROM with margin. */
static uint8_t sample(uint16_t a)
{
    set_addr(a);
    _delay_us(2);
    return PINF;
}

/*
 * Read READS_PER_ADDR times, return the first value; *stable = 0 on mismatch.
 * One settling sample is thrown away first: over long jumpers a bipolar
 * PROM output (82S129) was still moving on the first 2 us sample after an
 * address change.
 */
static uint8_t read_byte(uint16_t a, uint8_t *stable)
{
    (void)sample(a);
    _delay_us(20);
    uint8_t v = sample(a);
    for (uint8_t i = 1; i < READS_PER_ADDR; i++) {
        if (sample(a) != v)
            *stable = 0;
    }
    return v;
}

/* ---------- commands ---------- */

static const chip_t *cur(void)
{
    return &chip;
}

static void print_chip(void)
{
    puts_P_(cur()->name);
    PUTS(" size=");
    put_dec(cur()->size);
    PUTS(" mask=0x");
    put_hex8(cur()->mask);
}

static void cmd_help(void)
{
    PUTS("Commands:\r\n"
         "  info                chip this firmware was built for\r\n"
         "  dump                whole chip as Intel HEX\r\n"
         "  hex [addr] [len]    hex view (hex numbers)\r\n"
         "  peek <addr>         one address\r\n"
         "  check               chip present / outputs driven test\r\n"
         "  wires               jumper check, chip OUT: one line at a time\r\n"
         "  help\r\n");
}

/*
 * Intel HEX, 16 bytes per record. Lines that do not start with ':' are
 * status lines starting with '#'; the PC script ignores everything else.
 */
static void cmd_dump(void)
{
    const chip_t *c = cur();
    uint16_t unstable = 0;
    uint16_t first_bad = 0xFFFF;
    uint8_t and_all = 0xFF, or_all = 0x00;

    PUTS("# BEGIN ");
    print_chip();
    put_nl();

    for (uint16_t base = 0; base < c->size; base += 16) {
        uint8_t n = (c->size - base) < 16 ? (uint8_t)(c->size - base) : 16;
        uint8_t buf[16];
        uint8_t sum = n + (uint8_t)(base >> 8) + (uint8_t)base;

        /* Enable the chip only while sampling, not while the UART sends:
         * bipolar PROMs (82S129/82S123) draw heavy current with the outputs
         * on, and that disturbed the serial output over long jumpers. */
        chip_enable(1);
        for (uint8_t i = 0; i < n; i++) {
            uint8_t ok = 1;
            uint8_t v = read_byte(base + i, &ok) & c->mask;
            if (!ok) {
                unstable++;
                if (first_bad == 0xFFFF)
                    first_bad = base + i;
            }
            and_all &= v;
            or_all |= v;
            buf[i] = v;
            sum += v;
        }
        chip_enable(0);
        set_addr(0);

        uart_putc(':');
        put_hex8(n);
        put_hex16(base);
        put_hex8(0x00);
        for (uint8_t i = 0; i < n; i++)
            put_hex8(buf[i]);
        put_hex8((uint8_t)(0x100 - sum));
        put_nl();
    }
    chip_enable(0);
    set_addr(0);

    PUTS(":00000001FF\r\n");
    PUTS("# UNSTABLE ");
    put_dec(unstable);
    if (unstable) {
        PUTS(" first=0x");
        put_hex16(first_bad);
    }
    put_nl();
    if (and_all == or_all) {
        PUTS("# WARN every byte is 0x");
        put_hex8(and_all);
        PUTS(" (no chip, no power, or blank)\r\n");
    }
    led_error(unstable != 0);
    PUTS("# END\r\n");
}

static void cmd_hex(uint16_t start, uint16_t len)
{
    const chip_t *c = cur();
    if (start >= c->size) {
        PUTS("ERR address out of range\r\n");
        return;
    }
    if (len == 0 || (uint32_t)start + len > c->size)
        len = c->size - start;

    for (uint16_t a = start; a < start + len; a += 16) {
        uint8_t row[16], okr[16];
        uint8_t n = (start + len - a) < 16 ? (uint8_t)(start + len - a) : 16;
        /* Sample the whole row with the chip on, then print with it off
         * (same reason as in cmd_dump). */
        chip_enable(1);
        for (uint8_t i = 0; i < n; i++) {
            okr[i] = 1;
            row[i] = read_byte(a + i, &okr[i]) & c->mask;
        }
        chip_enable(0);
        set_addr(0);
        put_hex16(a);
        PUTS(": ");
        for (uint8_t i = 0; i < n; i++) {
            put_hex8(row[i]);
            uart_putc(okr[i] ? ' ' : '?');
        }
        PUTS(" |");
        for (uint8_t i = 0; i < n; i++)
            uart_putc((row[i] >= 0x20 && row[i] < 0x7F) ? (char)row[i] : '.');
        PUTS("|\r\n");
    }
    chip_enable(0);
    set_addr(0);
}

/*
 * With the chip disabled the outputs float and the pull-ups read 1.
 * With it enabled, a data bit that is ever 0 is being driven by the chip.
 * Bits never seen 0 are either all-1 data or not connected.
 */
static void cmd_check(void)
{
    const chip_t *c = cur();
    uint8_t seen0 = 0, seen1 = 0, off_low = 0;

    chip_enable(0);
    for (uint16_t a = 0; a < c->size; a++) {
        off_low |= (uint8_t)~sample(a);
    }
    chip_enable(1);
    for (uint16_t a = 0; a < c->size; a++) {
        uint8_t v = sample(a);
        seen0 |= (uint8_t)~v;
        seen1 |= v;
    }
    chip_enable(0);
    set_addr(0);

    seen0 &= c->mask;
    seen1 &= c->mask;
    off_low &= c->mask;

    PUTS("# disabled: bits pulled low = 0x");
    put_hex8(off_low);
    if (off_low)
        PUTS("  (outputs not released or shorted)\r\n");
    else
        PUTS("  (ok, outputs float)\r\n");
    PUTS("# enabled : bits seen 0 = 0x");
    put_hex8(seen0);
    PUTS(", bits seen 1 = 0x");
    put_hex8(seen1);
    put_nl();
    if (seen0 == 0)
        PUTS("# WARN no bit ever driven low: no chip, no power, or /CE wiring\r\n");
    else if (seen0 != c->mask)
        PUTS("# NOTE some data bits never 0: check those data wires\r\n");
    else
        PUTS("# OK all data bits toggle\r\n");
}

/*
 * Jumper check with the chip OUT of the ZIF (no chip output can fight the
 * MCU). A swapped or shifted jumper gives a dump whose every read matches
 * but whose bytes sit at the wrong addresses (HART U36, doc/troubleshooting.md),
 * so repeat reads cannot catch it; this can.
 *
 * Address lines: one MCU line at a time is set to its active level and the
 * reader names the ZIF pin where the meter should see it. Enter = next.
 * Data lines: the user touches each data ZIF pin to GND with a jumper; the
 * pull-up input that goes Low is named with the ZIF pin it must be.
 */
static uint8_t uart_poll(char *ch)
{
    if (!(UCSR1A & (1 << RXC1)))
        return 0;
    *ch = (char)UDR1;
    return 1;
}

static void cmd_wires(void)
{
    const uint8_t n_addr = sizeof(addr_wires) / sizeof(addr_wires[0]);
    const uint8_t n_data = sizeof(data_zif);
    char ch = 0;

    PUTS("# wiring check for ");
    puts_P_(cur()->name);
    PUTS(". Take the chip OUT of the ZIF first.\r\n"
         "# Meter: black on GND, red on the ZIF pin named. Enter = next, q = quit\r\n");

    for (uint8_t i = 0; i < n_addr; i++) {
        uint8_t line = pgm_read_byte(&addr_wires[i].line);
        uint8_t zif = pgm_read_byte(&addr_wires[i].zif);

        chip_enable(0);
        if (line < LINE_CE) {
            set_addr((uint16_t)1 << line);
            uart_putc('A');
            put_dec(line);
            PUTS(" -> ZIF ");
            put_dec(zif);
            PUTS(": 5 V there, 0 V on every other address ZIF pin");
        } else {
            set_addr(0);
            PORTC &= (uint8_t)~(1 << (line == LINE_CE ? CE_BIT : OE_BIT));
            if (line == LINE_CE)
                PUTS("/CE");
            else
                PUTS("/OE");
            PUTS(" -> ZIF ");
            put_dec(zif);
            PUTS(": 0 V there (5 V when idle)");
        }
        PUTS("  [Enter/q] ");
        ch = uart_getc();
        put_nl();
        if (ch == 'q' || ch == 'Q')
            break;
    }
    set_addr(0);
    chip_enable(0);
    if (ch == 'q' || ch == 'Q')
        return;

    PUTS("# Data lines: touch each data ZIF pin to GND with a jumper. q = quit\r\n#  expect");
    for (uint8_t b = 0; b < n_data; b++) {
        PUTS(" D");
        put_dec(b);
        PUTS("=ZIF ");
        put_dec(pgm_read_byte(&data_zif[b]));
    }
    put_nl();

    const uint8_t mask = cur()->mask;
    uint8_t last = 0;
    for (;;) {
        if (uart_poll(&ch) && (ch == 'q' || ch == 'Q'))
            break;
        uint8_t low = (uint8_t)~PINF & mask;
        if (low != last) {
            _delay_ms(20);                          /* let the jumper settle */
            low = (uint8_t)~PINF & mask;
        }
        if (low != last) {
            uint8_t count = 0;
            for (uint8_t b = 0; b < 8; b++) {
                if ((low >> b) & 1) {
                    count++;
                    if (!((last >> b) & 1)) {
                        PUTS("D");
                        put_dec(b);
                        PUTS(" low -> this must be ZIF ");
                        put_dec(pgm_read_byte(&data_zif[b]));
                        put_nl();
                    }
                }
            }
            if (count > 1)
                PUTS("# WARN several data bits low at once: shorted jumpers?\r\n");
            last = low;
        }
    }
    PUTS("# wiring check done\r\n");
}

/* ---------- line input ---------- */

static uint8_t read_line(char *buf, uint8_t max)
{
    uint8_t n = 0;
    for (;;) {
        char ch = uart_getc();
        if (ch == '\r' || ch == '\n') {
            if (n == 0)
                continue;
            put_nl();
            buf[n] = 0;
            return n;
        }
        if (ch == 0x08 || ch == 0x7F) {
            if (n) {
                n--;
                PUTS("\b \b");
            }
            continue;
        }
        if (ch >= 0x20 && n < max - 1) {
            buf[n++] = ch;
            uart_putc(ch);
        }
    }
}

static uint16_t parse_hex(const char *s)
{
    return s ? (uint16_t)strtoul(s, NULL, 16) : 0;
}

int main(void)
{
    char line[40];

    bus_init();
    uart_init();

    PUTS("\r\nATmega128 ROM reader (read only), built for ");
    print_chip();
    PUTS("\r\nWire the ZIF for this chip before inserting it.\r\n");
    cmd_help();

    for (;;) {
        PUTS("[");
        puts_P_(cur()->name);
        PUTS("]> ");
        read_line(line, sizeof(line));

        char *cmd = strtok(line, " \t");
        char *a1 = strtok(NULL, " \t");
        char *a2 = strtok(NULL, " \t");
        if (!cmd)
            continue;

        led_busy(1);
        if (!strcmp_P(cmd, PSTR("help")) || !strcmp_P(cmd, PSTR("?")))
            cmd_help();
        else if (!strcmp_P(cmd, PSTR("info"))) {
            print_chip();
            put_nl();
        } else if (!strcmp_P(cmd, PSTR("dump")))
            cmd_dump();
        else if (!strcmp_P(cmd, PSTR("hex")))
            cmd_hex(parse_hex(a1), a2 ? parse_hex(a2) : 0x100);
        else if (!strcmp_P(cmd, PSTR("peek"))) {
            uint16_t a = parse_hex(a1);
            if (a >= cur()->size) {
                PUTS("ERR address out of range\r\n");
            } else {
                uint8_t ok = 1;
                chip_enable(1);
                uint8_t v = read_byte(a, &ok) & cur()->mask;
                chip_enable(0);
                put_hex16(a);
                PUTS(" = ");
                put_hex8(v);
                if (ok)
                    put_nl();
                else
                    PUTS(" (unstable)\r\n");
            }
        } else if (!strcmp_P(cmd, PSTR("check")))
            cmd_check();
        else if (!strcmp_P(cmd, PSTR("wires")))
            cmd_wires();
        else
            PUTS("ERR unknown command, type help\r\n");
        led_busy(0);
    }
}
