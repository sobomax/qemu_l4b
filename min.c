#include <unistd.h>

const char msg[] = "Hello, World!\n";

void _start() {
#if defined __linux__
    asm volatile (
        "mov $1, %%rax\n"             // syscall: write
        "mov $1, %%rdi\n"             // file descriptor: stdout (1)
        "mov %0, %%rsi\n"             // pointer to message
        "mov $14, %%rdx\n"            // message length (13 bytes+\n)
        "syscall\n"
        :
        : "r"(msg)
        : "rax", "rdi", "rsi", "rdx"
    );
#else
    asm volatile (
        "mov $4, %%rax\n"             // syscall: write (FreeBSD uses 4)
        "mov $1, %%rdi\n"             // file descriptor: stdout (1)
        "mov %0, %%rsi\n"             // pointer to message
        "mov $14, %%rdx\n"            // message length (13 bytes+\n)
        "syscall\n"
        :
        : "r"(msg)
        : "rax", "rdi", "rsi", "rdx"
    );
#endif

    // Exit syscall
#if defined __linux__
    asm volatile (
        "mov $60, %%rax\n"            // syscall: exit
        "xor %%rdi, %%rdi\n"          // exit code 0
        "syscall\n"
        :
        :
        : "rax", "rdi"
    );
#else
    asm volatile (
        "mov $1, %%rax\n"             // syscall: exit (FreeBSD uses 1)
        "xor %%rdi, %%rdi\n"          // exit code 0
        "syscall\n"
        :
        :
        : "rax", "rdi"
    );
#endif
}
