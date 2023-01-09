#ifndef SHELL_H
#define SHELL_H

/* FreeRTOS-Shell macro */
#define FREERTOS_SHELL_RECV_QUEUE_LENGTH 32
//#define FREERTOS_SHELL_INPUT_BUFFER_LENGTH 20
#define FREERTOS_SHELL_INPUT_BUFFER_LENGTH 64
#define FREERTOS_SHELL_USER_INFO "[root@FreeRTOS]# "

/* FreeRTOS-CLI macro */
#define FREERTOS_CLI_OUTPUT_MAX_BUFFER_SIZE 128

void uartInit(void);
void taskFreeRTOSShell(void *pvParameters);
void FreeRTOS_ShellOutput(const uint8_t* buffer, int length);
void vOutputString( const uint8_t* const pcMessage, int length );

#endif // SHELL_H

