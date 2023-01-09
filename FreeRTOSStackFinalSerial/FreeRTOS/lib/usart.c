#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#define USART_BAUDRATE 9600
#define UBRR_VALUE (((F_CPU / (USART_BAUDRATE * 16UL))) - 1)
//define max buffer size
#define BUF_SIZE 20

//type definition of buffer structure
typedef struct{
	//Array of chars
	uint8_t buffer[BUF_SIZE];
	//array element index
	uint8_t index;
}u8buf;

u8buf buf;

void USART1Init(void)
{
	// Set baud rate
	UBRR1H = (uint8_t)(UBRR_VALUE>>8);
	UBRR1L = (uint8_t)UBRR_VALUE;
	// Set frame format to 8 data bits, no parity, 1 stop bit
	UCSR1C |= (1<<UCSZ11)|(1<<UCSZ10);
	//enable reception and RC complete interrupt
	UCSR1B |= (1<<RXEN1)|(1<<RXCIE1);
}

//RX Complete interrupt service routine
ISR(USART1_RX_vect)
{
	uint8_t u8temp;
	u8temp=UDR1;
	
	void FreeRTOS_ShellIRQHandle(uint8_t recvData);
	FreeRTOS_ShellIRQHandle(u8temp);
		
	//check if period char or end of buffer
    if (buf.index<BUF_SIZE)
    {
	    buf.buffer[buf.index] = u8temp;
	    //increment buffer index
	    buf.index++;
	}
	else
	{
        //disable reception and RX Complete interrupt
        UCSR0B &= ~((1<<RXEN0)|(1<<RXCIE0));
        //enable transmission and UDR0 empty interrupt
        UCSR0B |= (1<<TXEN0)|(1<<UDRIE0);			    
	}
}

//UDR0 Empty interrupt service routine
ISR(USART1_UDRE_vect)
{
	uint8_t u8data;
	
    if(buf.index>0)
    {
	    buf.index--;
	    u8data=buf.buffer[buf.index];	    
    }
    else
	{
        buf.index=0;
        //disable transmission and UDR0 empty interrupt
        UCSR0B &= ~((1<<TXEN0)|(1<<UDRIE0));
        //enable reception and RC complete interrupt
        UCSR0B |= (1<<RXEN0)|(1<<RXCIE0);				
	}
}

void uart1_putc(uint8_t data)
{
	buf.index
	UCSR1B |= _BV(UDRIE1);
}