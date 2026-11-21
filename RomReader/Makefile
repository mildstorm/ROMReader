# ATmega128 ROM reader firmware (bare metal). Requires avr-gcc on PATH.
#
# One firmware per chip type; flash the one that matches the ZIF wiring.
#   make CHIP=2764      -> build/2764/RomReader_2764.hex
#   make CHIP=82S129    -> build/82S129/RomReader_82S129.hex  (also 82S126)
#   make CHIP=82S123    -> build/82S123/RomReader_82S123.hex
#   make all-chips      -> all three
CHIP ?= 2764
ifeq ($(filter 2764 82S129 82S123,$(CHIP)),)
$(error CHIP must be 2764, 82S129 or 82S123)
endif

TARGET := RomReader_$(CHIP)
MCU := atmega128
F_CPU := 16000000
BUILD := build/$(CHIP)

CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size

SRC := main.c
OBJ := $(addprefix $(BUILD)/,$(SRC:.c=.o))

CFLAGS := -mmcu=$(MCU) -DF_CPU=$(F_CPU)UL -DCHIP_$(CHIP) \
	-Os -g2 -Wall -Wextra -std=gnu99 \
	-funsigned-char -funsigned-bitfields \
	-ffunction-sections -fdata-sections -fshort-enums

LDFLAGS := -mmcu=$(MCU) -Wl,--gc-sections -Wl,-Map,$(BUILD)/$(TARGET).map

.PHONY: all all-chips clean

all: $(BUILD)/$(TARGET).hex

all-chips:
	$(MAKE) CHIP=2764
	$(MAKE) CHIP=82S129
	$(MAKE) CHIP=82S123

$(BUILD)/$(TARGET).elf: $(OBJ)
	$(CC) -o $@ $(OBJ) $(LDFLAGS)
	$(SIZE) $@

$(BUILD)/$(TARGET).hex: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O ihex -R .eeprom -R .fuse -R .lock -R .signature -R .user_signatures $< $@

$(BUILD)/%.o: %.c Makefile
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf build
