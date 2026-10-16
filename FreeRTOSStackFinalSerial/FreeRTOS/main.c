#include <avr/io.h>
#include <avr/pgmspace.h>
#include <util/delay.h>
#include <string.h>
#include <stdio.h>

#include "FreeRTOS.h"
#include "task.h"
#include "lib/shell.h"
#include "portable.h"
#include "lib/gpio.h"
#include "lib/lcd.h"
#include "lib/uart.h"

/* AB-M128Pro-A 4-digit, common cathode. PORTA is the segment pattern
 * (bit0=a .. bit6=g). PC0-PC3 select digits 0-3, active low.
 * Those pins are also the external SRAM bus, so the bus stays off. */
static const uint8_t seg_font[10] = {
	0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x27, 0x7F, 0x67
};

static void seg_init(void)
{
	DDRA = 0xFF;
	PORTA = 0x00;
	/* PC7 is the SRAM /CS. Hold it high so the chip stays off the bus. */
	DDRC |= 0x8F;
	PORTC |= 0x8F;
}

static void seg_show(uint8_t pos, uint8_t pattern)
{
	PORTC |= 0x0F;
	PORTA = pattern;
	PORTC = (uint8_t)((PORTC | 0x8F) & ~(1u << pos));
}

#define LED_TASK_PRIORITY (tskIDLE_PRIORITY + 5)
#define SHELL_TASK_PRIORITY (tskIDLE_PRIORITY + 4)
#define SEG_TASK_PRIORITY (tskIDLE_PRIORITY + 6)

void taskLED(void *pvParameters)
{
	/* AB-M128Pro-A LEDs are PG0 and PG1, on when the pin is high.
	 * PC7 stays high, so the external SRAM stays disabled. */
	(void)pvParameters;
	DDRG |= (1 << DDG0) | (1 << DDG1);
	PORTG &= (uint8_t)~((1 << PG0) | (1 << PG1));
	while(1)
	{
		PORTG ^= (1 << PG0);
		vTaskDelay(250);
		PORTG ^= (1 << PG1);
		vTaskDelay(250);
	}
}

static void taskSeg(void *pvParameters)
{
	uint16_t value = 0;
	uint8_t digits[4] = { 0, 0, 0, 0 };
	uint8_t pos = 0;
	uint16_t ticks = 0;

	(void)pvParameters;
	for (;;) {
		seg_show(pos, seg_font[digits[pos]]);
		pos = (uint8_t)((pos + 1u) & 3u);
		if (++ticks >= 1000u) {
			uint16_t next = (uint16_t)(value + 1u);

			ticks = 0;
			if (next > 9999u)
				next = 0;
			value = next;
			digits[0] = (uint8_t)(value / 1000u);
			digits[1] = (uint8_t)((value / 100u) % 10u);
			digits[2] = (uint8_t)((value / 10u) % 10u);
			digits[3] = (uint8_t)(value % 10u);
		}
		vTaskDelay(1);
	}
}

void deviceInit(void)
{
	uartInit();
	seg_init();
}

// https://www.digikey.com/en/maker/projects/introduction-to-rtos-solution-to-part-7-freertos-semaphore-example/51aa8660524c4daba38cba7c2f5baba7
// https://github.com/andygock/avr-uart/blob/master/example.c
int main(void)
{
	deviceInit();
	
    xTaskCreate(taskLED,
		(const char *)"LED",
		configMINIMAL_STACK_SIZE,
		NULL,
		LED_TASK_PRIORITY,
		NULL);
   
    xTaskCreate(taskFreeRTOSShell,
		(const char *)"SHELL",
		configMINIMAL_STACK_SIZE,
		NULL,
		SHELL_TASK_PRIORITY,
		NULL);

    xTaskCreate(taskSeg,
		(const char *)"SEG",
		configMINIMAL_STACK_SIZE,
		NULL,
		SEG_TASK_PRIORITY,
		NULL);

    vTaskStartScheduler();	
    
    while (1) { }
    return 0;
}
