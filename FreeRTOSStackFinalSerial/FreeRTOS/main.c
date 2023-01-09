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

#define GET_XRAM(addr) (*(volatile unsigned char *)(addr))
#define SET_XRAM(addr, data) ((*(volatile unsigned char *)(addr)) = data)

void XMEM_init(void) __attribute__ ((naked)) __attribute__ ((section(".init1")));

void XMEM_init(void) 
{
	// External memory interface enable
	MCUCR |= (1<<SRE);
	XMCRA = 0;
	//PC7..PC5 released pins
	XMCRB |= (1<<XMM1)|(1<<XMM0);
}

#define LED_TASK_PRIORITY (tskIDLE_PRIORITY + 5)
#define SHELL_TASK_PRIORITY (tskIDLE_PRIORITY + 4)

void taskLED(void *pvParameters)
{	
	// https://mansfield-devine.com/speculatrix/2017/04/avr-basics-reading-and-writing-gpio-pins/
    DDRE |= (1 << DDE6);   
	DDRE |= (1 << DDE7);   
    while(1) 
	{
		{
			//char message[20] = {0, };
			//sprintf(message, "toggling %s", "led");
			//printf("%s\n\r", message);
		}
		
		PORTE ^= (1 << PE6); // Toggle bit
		vTaskDelay(250);
		PORTE ^= (1 << PE7); // Toggle bit		
	    vTaskDelay(250);
    }
}

void deviceInit(void)
{
	uartInit();	
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

    vTaskStartScheduler();	
    
    while (1) { }
    return 0;
}
