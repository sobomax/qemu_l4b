CC = cc
CFLAGS = -nostdlib
SRC = min.c
OUT = hello

.PHONY: all clean

# Declare the default target
all: $(OUT)

# Target to build the executable
$(OUT): $(SRC)
	$(CC) $(CFLAGS) -o $(OUT) $(SRC)

# Clean up generated files
clean:
	rm -f $(OUT)
