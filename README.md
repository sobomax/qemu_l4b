## About

This is some test code and tooling to help developing [Userland BSD on Linux](https://github.com/sobomax/qemu-bsd-user-l4b/) project. 

## Content

 * `min.c`: minimal x86-64 "Hello-world" program for both Linux and FreeBSD written in C intrinsics.
 * `mid.c`: equivalent in pure C.
 * `Makefile`: BSD make makefile to build `min`, `mid` (`mid.c` statically linked) and `max` (`mid.c` linked dinamically) and run `sym_extract.py` to generate `target_os_defs.h`.
 * `sym_extract.py`: tool used to extract only relevant defines and structs from the FreeBSD kernel sources.
 * `*.econf`: extraction rules 
