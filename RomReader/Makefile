# ATmega128 ROM reader firmware (bare metal). Requires avr-gcc on PATH.
TARGET := RomReader
MCU := atmega128
F_CPU := 16000000
BUILD := build

CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size

SRC := main.c
OBJ := $(addprefix $(BUILD)/,$(SRC:.c=.o))

CFLAGS := -mmcu=$(MCU) -DF_CPU=$(F_CPU)UL \
	-Os -g2 -Wall -Wextra -std=gnu99 \
	-funsigned-char -funsigned-bitfields \
	-ffunction-sections -fdata-sections -fshort-enums

LDFLAGS := -mmcu=$(MCU) -Wl,--gc-sections -Wl,-Map,$(BUILD)/$(TARGET).map

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
