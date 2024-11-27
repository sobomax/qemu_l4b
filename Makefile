CC = cc
CFLAGS_hello_min = -nostdlib -static
CFLAGS_hello_mid = -static
CFLAGS_hello_max = -O0 -g3
SRC_hello_min = min.c
SRC_hello_mid = mid.c
SRC_hello_max = mid.c
OUT = hello_min hello_mid hello_max target_os_defs.h

SYM_DIRS = sys netinet netinet6

.for dir in ${SYM_DIRS}
SYM_SRCS += syms_${dir}.econf
.endfor

.PHONY: all clean

# Declare the default target
all: $(OUT)

hello_min: $(SRC_hello_min)
	$(CC) $(CFLAGS_hello_min) -o $@ $(SRC_$(@))

# Rule for hello_mid target
hello_mid: $(SRC_hello_mid)
	$(CC) $(CFLAGS_hello_mid) -o $@ $(SRC_$(@))

hello_max: $(SRC_hello_max)
	$(CC) $(CFLAGS_hello_max) -o $@ $(SRC_$(@))

target_os_defs.h: sym_extract.py ${SYM_SRCS}
	rm -f $@ $@.tmp
	python sym_extract.py ~/projects/freebsd13/sys/sys syms_sys.econf  >> $@.tmp
.for dir in ${SYM_DIRS:Nsys}
	python sym_extract.py --no-header ~/projects/freebsd13/sys/${dir} syms_${dir}.econf  >> $@.tmp
.endfor
	mv $@.tmp $@

# Clean up generated files
clean:
	rm -f $(OUT)
