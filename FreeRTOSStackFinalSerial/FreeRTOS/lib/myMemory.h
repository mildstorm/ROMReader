#ifndef __MY_MEMORY_H__
#define __MY_MEMORY_H__

typedef struct
{
	int is_available;
	int size;
} MCB, *MCB_P;

char *mem_start_p;
int max_mem;
int allocated_mem; /* this is the memory in use. */
int mcb_count;

char *heap_end;

enum {NEW_MCB = 0, NO_MCB, REUSE_MCB};
enum {FREE,IN_USE};
	
void InitMem(char *ptr, int size_in_bytes);
void * myalloc(int elem_size);
void myfree(void *p);

#endif