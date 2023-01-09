#include <stdio.h>
#include <stdlib.h>
#include <avr/pgmspace.h>
#include <avr/interrupt.h>
#include <stdio.h>
#include <string.h>
#include <util\delay.h>

#include "shell.h"
#include "FreeRTOS.h"
#include "FreeRTOS_CLI.h"
#include "semphr.h"
#include "task.h"
#include "queue.h"
#include "uart.h"

static SemaphoreHandle_t xTxMutex = NULL;
#define cmdMAX_MUTEX_WAIT		pdMS_TO_TICKS( 300 )

#if ( configAPPLICATION_ALLOCATED_HEAP == 1 )

/* The application writer has already defined the array used for the RTOS
* heap - probably so it can be placed in a special segment or address. */
uint8_t __attribute__((section (".myBufSection"))) ucHeap[ configTOTAL_HEAP_SIZE ];

#endif

QueueHandle_t __attribute__((section (".myBufSection"))) FreeRTOS_ShellRecvQueue;
static uint8_t __attribute__((section (".myBufSection"))) inputBuffer[FREERTOS_SHELL_INPUT_BUFFER_LENGTH];
static uint8_t __attribute__((section (".myBufSection"))) *inputBuffer_ptr;
static uint8_t __attribute__((section (".myBufSection"))) outputBuffer[FREERTOS_CLI_OUTPUT_MAX_BUFFER_SIZE];

int USART1_putc(char data, FILE *stream)
{
	uart1_putc(data);	
	return data;
}

int USART1_getc(FILE *stream)
{
	return uart1_getc();
}

static FILE usart_stdout = FDEV_SETUP_STREAM(USART1_putc, NULL, _FDEV_SETUP_WRITE);
static FILE usart_stdin = FDEV_SETUP_STREAM(NULL, USART1_getc, _FDEV_SETUP_READ);
static FILE usart_stdio = FDEV_SETUP_STREAM(USART1_putc, USART1_getc, _FDEV_SETUP_RW);

void uartInit(void)
{		
	#define UART_BAUD_RATE 9600
	uart_init(UART_BAUD_SELECT(UART_BAUD_RATE, F_CPU));
	
	stdout = (FILE *)&usart_stdout;
	stdin = (FILE *)&usart_stdin;
	stderr = (FILE *)&usart_stdio;
	sei();	
}

void FreeRTOS_ShellOutput(const uint8_t* buffer, int length) 
{	
	for(int i = 0; i < length; i++)
	{
		uart1_putc((unsigned char)buffer[i]);				
	}
}

void vOutputString( const uint8_t* const pcMessage, int length )
{
	if( xSemaphoreTake( xTxMutex, cmdMAX_MUTEX_WAIT ) == pdPASS )
	{
		FreeRTOS_ShellOutput(pcMessage, length);
		xSemaphoreGive( xTxMutex );
	}
}

const char __attribute__((section (".myBufSection"))) *welcome = "Hello world! Waiting for input ...\r\n";

#define FREERTOS_SHELL_START_LOGO \
"___________                    _____________________________    _________         \r\n"\
"\\_   _____/______   ____   ____\\______   \\__    ___/\\_____  \\  /   _____/    \r\n"\
" |    __) \\_  __ \\_/ __ \\_/ __ \\|       _/ |    |    /   |   \\ \\_____  \\   \r\n"\
" |     \\   |  | \\/\\  ___/\\  ___/|    |   \\ |    |   /    |    \\/        \\  \r\n"\
" \\___  /   |__|    \\___  >\\___  >____|_  / |____|   \\_______  /_______  /     \r\n"\
"     \\/                \\/     \\/       \\/                   \\/        \\/    \r\n"\
"           _________.__           .__  .__                 \r\n"\
"          /   _____/|  |__   ____ |  | |  |                \r\n"\
"  ______  \\_____  \\ |  |  \\_/ __ \\|  | |  |            \r\n"\
" /_____/  /        \\|   Y  \\  ___/|  |_|  |__            \r\n"\
"         /_______  /|___|  /\\___  >____/____/             \r\n"\
"                 \\/      \\/     \\/                      \r\n"\
"\r\n"
#define FREERTOS_SHELL_USER_INFO "[root@FreeRTOS]# "

const char *pcParameter;
char ip[16]={0};
char subnet[16]={0};

static BaseType_t prvSetNetworkConfigCommand( char *pcWriteBuffer, size_t xWriteBufferLen, const char *pcCommandString )
{
	BaseType_t xParameterStringLength, xReturn;

	/* Remove compile time warnings about unused parameters, and check the
	write buffer is not NULL.  NOTE - for simplicity, this example assumes the
	write buffer length is adequate, so does not check for buffer overflows. */
	( void ) pcCommandString;
	( void ) xWriteBufferLen;
	configASSERT( pcWriteBuffer );

    pcParameter = FreeRTOS_CLIGetParameter(pcCommandString, 1, &xParameterStringLength);
    strncat(ip, pcParameter, xParameterStringLength);    

    pcParameter = FreeRTOS_CLIGetParameter(pcCommandString, 2, &xParameterStringLength);
    strncat(subnet, pcParameter, xParameterStringLength);    
    
    sprintf(pcWriteBuffer,"Network Setting Done\r\n"); 
    
    xReturn = pdFALSE;
    return xReturn;
}

static BaseType_t prvGetNetworkConfigCommand( char *pcWriteBuffer, size_t xWriteBufferLen, const char *pcCommandString )
{
BaseType_t xReturn;
static int paramCount = 0;

    /* Remove compile time warnings about unused parameters, and check the
	write buffer is not NULL.  NOTE - for simplicity, this example assumes the
	write buffer length is adequate, so does not check for buffer overflows. */
	( void ) pcCommandString;
	( void ) xWriteBufferLen;
	configASSERT( pcWriteBuffer );

    switch(paramCount)
    {
        case 0:            
            sprintf(pcWriteBuffer,"MAC ADDRESS : %.2X:%.2X:%.2X:%.2X:%.2X:%.2X\r\n",10,113,110,94,420,30); 
            xReturn = pdPASS;
            paramCount++;
            break;
        case 1:            
            sprintf(pcWriteBuffer,"IP ADDRESS  : %d.%d.%d.%d\r\n",8,8,8,8); 
            xReturn = pdPASS;
            paramCount++;
            break;
        default:
            paramCount=0;
            xReturn = pdFALSE;
            break;
    }
    
    return xReturn;
}

static const CLI_Command_Definition_t xSetNetConfig =
{
	"set-net",
	"set-net <ip-addr> <subnet> <gateway>:\r\n",
	prvSetNetworkConfigCommand, /* The function to run. */
	3 /* Three parameters are expected, which can take any value. */
};

static const CLI_Command_Definition_t xGetNetConfig =
{
	"get-net",
	"get-net\r\n",
	prvGetNetworkConfigCommand, /* The function to run. */
	0
};

void vRegisterCLICommands(void)
{
	/* Register all the command line commands defined immediately above. */
	FreeRTOS_CLIRegisterCommand(&xSetNetConfig);
	FreeRTOS_CLIRegisterCommand(&xGetNetConfig);	
}

void taskFreeRTOSShell(void *pvParameters)
{
	uint8_t recvChar = 0;		
	uint16_t checkChar = 0;		
	int pass = 0;
	
	/* Create the semaphore used to access the UART Tx. */
	xTxMutex = xSemaphoreCreateMutex();
	configASSERT( xTxMutex );
		
	FreeRTOS_ShellRecvQueue = xQueueCreate(FREERTOS_SHELL_RECV_QUEUE_LENGTH, sizeof(uint16_t));
	uart_puts_P(FREERTOS_SHELL_START_LOGO);
	uart_puts_P(FREERTOS_SHELL_USER_INFO);
	
	vRegisterCLICommands();
	
	while(1) 
	{
		/* always wait a queue */		 
		checkChar = uart1_getc();
		recvChar = checkChar & 0xff;
		pass = 0;

		if (checkChar & UART_NO_DATA)
		{			
		}
		else
		{
			if (checkChar & UART_FRAME_ERROR)
			{				
			}
			else if (checkChar & UART_OVERRUN_ERROR)
			{	
			}
			else if (checkChar & UART_BUFFER_OVERFLOW)
			{			
			}
			else
			{		
				pass = 1;		
			}
		}		
		
		if (pass)
		{
			if( xSemaphoreTake( xTxMutex, cmdMAX_MUTEX_WAIT ) == pdPASS )
			{				
				int lineOver = 0;
				int isInputBufferEmpty = (inputBuffer_ptr == inputBuffer);				
		
				if(recvChar == 13)
				{
					lineOver = 1;
				}
				
				if(lineOver) 
				{
					BaseType_t ret = pdTRUE;
					//FreeRTOS_ShellOutput((const uint8_t *)"\r", 1);					
			
					if(!isInputBufferEmpty) 
					{
						while (ret == pdTRUE) 
						{
							ret = FreeRTOS_CLIProcessCommand((const char*)inputBuffer, (char*)outputBuffer, FREERTOS_CLI_OUTPUT_MAX_BUFFER_SIZE);
							FreeRTOS_ShellOutput((const uint8_t *)outputBuffer, strlen((const char*)outputBuffer));							
						}
						memset(outputBuffer,0,FREERTOS_CLI_OUTPUT_MAX_BUFFER_SIZE);
						memset(inputBuffer,0,FREERTOS_SHELL_INPUT_BUFFER_LENGTH);
						inputBuffer_ptr = inputBuffer;
					}
					FreeRTOS_ShellOutput((const uint8_t *)FREERTOS_SHELL_USER_INFO, strlen(FREERTOS_SHELL_USER_INFO));					
				}
				else if (!lineOver) 
				{
					/* backspace */
					if(recvChar == 0x7f && isInputBufferEmpty) 
					{						
					}
					/* backspace*/
					else if(recvChar == 0x7f && !isInputBufferEmpty) 
					{
						*--inputBuffer_ptr = 0;
						FreeRTOS_ShellOutput(&recvChar, 1);
					}
					/* tab */
					/* TODO: when double click tab, trigger auto complete */
					else if(recvChar == 0x08) 
					{						
					}
					else 
					{
						*inputBuffer_ptr++ = recvChar;
						FreeRTOS_ShellOutput(&recvChar, 1);
					}
				}	
				
				xSemaphoreGive( xTxMutex );
			}
		}
	}
}