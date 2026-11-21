/*
 * ATmega128 ROM reader (bare metal, no RTOS).
 *
 * Board: AB-M128Pro-A base + AM-128RAM CPU module, 16 MHz.
 * Reads 2764 EPROM (8K x 8), 82S129/82S126 PROM (256 x 4), 82S123 PROM (32 x 8).
 * Read only: no pin is ever driven above VCC, no program pulse exists.
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

/* ---------- chip table ---------- */

typedef struct {
    const char *name;   /* in flash */
    uint16_t size;      /* bytes */
    uint8_t mask;       /* valid data bits */
} chip_t;

static const char n2764[] PROGMEM = "2764";
static const char n129[]  PROGMEM = "82S129";
static const char n123[]  PROGMEM = "82S123";

static const chip_t chips[] = {
    { n2764, 8192, 0xFF },
    { n129,   256, 0x0F },
    { n123,    32, 0xFF },
};
#define CHIP_COUNT (sizeof(chips) / sizeof(chips[0]))

static uint8_t chip_sel = 0;    /* 2764 */
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

/* Read READS_PER_ADDR times, return the first value; *stable = 0 on mismatch. */
static uint8_t read_byte(uint16_t a, uint8_t *stable)
{
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
    return &chips[chip_sel];
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
         "  type 2764|129|123   select chip (82S126 reads as 129)\r\n"
         "  info                show selected chip\r\n"
         "  dump                whole chip as Intel HEX\r\n"
         "  hex [addr] [len]    hex view (hex numbers)\r\n"
         "  peek <addr>         one address\r\n"
         "  check               chip present / outputs driven test\r\n"
         "  help\r\n");
}

static void cmd_type(const char *arg)
{
    if (!arg) {
        PUTS("ERR type needs 2764, 129 or 123\r\n");
        return;
    }
    if (strstr_P(arg, PSTR("2764")))
        chip_sel = 0;
    else if (strstr_P(arg, PSTR("129")) || strstr_P(arg, PSTR("126")))
        chip_sel = 1;
    else if (strstr_P(arg, PSTR("123")))
        chip_sel = 2;
    else {
        PUTS("ERR unknown type\r\n");
        return;
    }
    PUTS("OK ");
    print_chip();
    put_nl();
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

    chip_enable(1);
    for (uint16_t base = 0; base < c->size; base += 16) {
        uint8_t n = (c->size - base) < 16 ? (uint8_t)(c->size - base) : 16;
        uint8_t buf[16];
        uint8_t sum = n + (uint8_t)(base >> 8) + (uint8_t)base;

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

    chip_enable(1);
    for (uint16_t a = start; a < start + len; a += 16) {
        put_hex16(a);
        PUTS(": ");
        uint8_t row[16];
        uint8_t n = (start + len - a) < 16 ? (uint8_t)(start + len - a) : 16;
        for (uint8_t i = 0; i < n; i++) {
            uint8_t ok = 1;
            row[i] = read_byte(a + i, &ok) & c->mask;
            put_hex8(row[i]);
            uart_putc(ok ? ' ' : '?');
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

    PUTS("\r\nATmega128 ROM reader (read only)\r\n");
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
        else if (!strcmp_P(cmd, PSTR("type")))
            cmd_type(a1);
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
        else
            PUTS("ERR unknown command, type help\r\n");
        led_busy(0);
    }
}
