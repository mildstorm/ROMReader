# ATmega128 FreeRTOS firmware. Requires avr-gcc on PATH.
#
# BOARD=stacked (default): base + CPU. 7-segment and PG0/PG1 LEDs, internal heap.
# BOARD=cpu: AM-128RAM only. External SRAM heap, no 7-segment and no LED.
BOARD ?= stacked
ifeq ($(filter stacked cpu,$(BOARD)),)
$(error BOARD must be stacked or cpu)
endif

TARGET := FreeRTOS
MCU := atmega128
F_CPU := 16000000
BUILD := build/$(BOARD)

CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size

SRC := \
	event_groups.c \
	lib/delay.c \
	lib/FreeRTOS_CLI.c \
	lib/shell.c \
	lib/uart.c \
	list.c \
	main.c \
	portable/GCC/ATMega323/port.c \
	portable/MemMang/heap_1.c \
	queue.c \
	stream_buffer.c \
	tasks.c \
	timers.c

OBJ := $(addprefix $(BUILD)/,$(SRC:.c=.o))

CFLAGS := -mmcu=$(MCU) -DF_CPU=$(F_CPU)UL -DDEBUG -DUSART1_ENABLED \
	-Iinclude -Iportable/GCC/ATMega323 -I. \
	-O1 -g2 -Wall -std=gnu99 \
	-funsigned-char -funsigned-bitfields \
	-ffunction-sections -fdata-sections -fpack-struct -fshort-enums \
	-mrelax

ifeq ($(BOARD),cpu)
CFLAGS += -DBOARD_CPU_ONLY
endif

# stacked keeps the linker's data region inside the internal 4 KB, so the
# hardware stack stays at 0x10FF. cpu extends that region across the external
# window so .noinit can sit there, and pins the stack back to internal SRAM.
DATA_REGION_LENGTH := 0x1000
ifeq ($(BOARD),cpu)
DATA_REGION_LENGTH := 0x7F00
endif

LDFLAGS := -mmcu=$(MCU) -mrelax -Wl,--gc-sections \
	-Wl,-Map,$(BUILD)/$(TARGET).map \
	-Wl,-u,vfprintf \
	-Wl,--start-group -Wl,-lm -Wl,-lprintf_flt -Wl,-lscanf_flt -Wl,--end-group \
	-Wl,--defsym=__DATA_REGION_LENGTH__=$(DATA_REGION_LENGTH)

# FreeRTOS heap is .noinit at external 0x1100-0x7FFF (0x800000 + CPU address).
ifeq ($(BOARD),cpu)
LDFLAGS += -Wl,--section-start,.noinit=0x801100 -Wl,--defsym=__stack=0x10FF
endif

.PHONY: all clean

all: $(BUILD)/$(TARGET).hex

$(BUILD)/$(TARGET).elf: $(OBJ)
	$(CC) -o $@ $(OBJ) $(LDFLAGS)
	$(SIZE) $@

$(BUILD)/$(TARGET).hex: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O ihex -R .eeprom -R .fuse -R .lock -R .signature -R .user_signatures $< $@

$(BUILD)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf build
