/*
 * Summary: interface for the memory allocator
 * Description: provides interfaces for the memory allocator,
 *              including debugging capabilities.
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */


#ifndef __DEBUG_MEMORY_ALLOC__
#define __DEBUG_MEMORY_ALLOC__

#include <stdio.h>
#include <libxml/xmlversion.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * The XML memory wrapper support 4 basic overloadable functions.
 */
/**
 * xmlFreeFunc:
 * @mem: an already allocated block of memory
 *
 * Signature for a free() implementation.
 */
typedef void (*xmlFreeFunc)(void *mem);
/**
 * xmlMallocFunc:
 * @size:  the size requested in bytes
 *
 * Signature for a malloc() implementation.
 *
 * Returns a pointer to the newly allocated block or NULL in case of error.
 */
typedef void *(LIBXML_ATTR_ALLOC_SIZE(1) *xmlMallocFunc)(size_t size);

/**
 * xmlReallocFunc:
 * @mem: an already allocated block of memory
 * @size:  the new size requested in bytes
 *
 * Signature for a realloc() implementation.
 *
 * Returns a pointer to the newly reallocated block or NULL in case of error.
 */
typedef void *(*xmlReallocFunc)(void *mem, size_t size);

/**
 * xmlStrdupFunc:
 * @str: a zero terminated string
 *
 * Signature for an strdup() implementation.
 *
 * Returns the copy of the string or NULL in case of error.
 */
typedef char *(*xmlStrdupFunc)(const char *str);

/*
 * In general the memory allocation entry points are not kept
 * thread specific but this can be overridden by LIBXML_THREAD_ALLOC_ENABLED
 *    - xmlMalloc
 *    - xmlMallocAtomic
 *    - xmlRealloc
 *    - xmlMemStrdup
 *    - xmlFree
 */
/** DOC_DISABLE */
#ifdef LIBXML_THREAD_ALLOC_ENABLED
  #define XML_GLOBALS_ALLOC \
    XML_OP(xmlMalloc, xmlMallocFunc, XML_NO_ATTR) \
    XML_OP(xmlMallocAtomic, xmlMallocFunc, XML_NO_ATTR) \
    XML_OP(xmlRealloc, xmlReallocFunc, XML_NO_ATTR) \
    XML_OP(xmlFree, xmlFreeFunc, XML_NO_ATTR) \
    XML_OP(xmlMemStrdup, xmlStrdupFunc, XML_NO_ATTR)
  #define XML_OP XML_DECLARE_GLOBAL
    XML_GLOBALS_ALLOC
  #undef XML_OP
  #if defined(LIBXML_THREAD_ENABLED) && !defined(XML_GLOBALS_NO_REDEFINITION)
    #define xmlMalloc XML_GLOBAL_MACRO(xmlMalloc)
    #define xmlMallocAtomic XML_GLOBAL_MACRO(xmlMallocAtomic)
    #define xmlRealloc XML_GLOBAL_MACRO(xmlRealloc)
    #define xmlFree XML_GLOBAL_MACRO(xmlFree)
    #define xmlMemStrdup XML_GLOBAL_MACRO(xmlMemStrdup)
  #endif
#else
  #define XML_GLOBALS_ALLOC
/** DOC_ENABLE */
  XMLPUBVAR xmlMallocFunc xmlMalloc;
  XMLPUBVAR xmlMallocFunc xmlMallocAtomic;
  XMLPUBVAR xmlReallocFunc xmlRealloc;
  XMLPUBVAR xmlFreeFunc xmlFree;
  XMLPUBVAR xmlStrdupFunc xmlMemStrdup;
#endif

/*
 * The way to overload the existing functions.
 * The xmlGc function have an extra entry for atomic block
 * allocations useful for garbage collected memory allocators
 */
XMLPUBFUN int
	xmlMemSetup	(xmlFreeFunc freeFunc,
			 xmlMallocFunc mallocFunc,
			 xmlReallocFunc reallocFunc,
			 xmlStrdupFunc strdupFunc);
XMLPUBFUN int
	xmlMemGet	(xmlFreeFunc *freeFunc,
			 xmlMallocFunc *mallocFunc,
			 xmlReallocFunc *reallocFunc,
			 xmlStrdupFunc *strdupFunc);
XMLPUBFUN int
	xmlGcMemSetup	(xmlFreeFunc freeFunc,
			 xmlMallocFunc mallocFunc,
			 xmlMallocFunc mallocAtomicFunc,
			 xmlReallocFunc reallocFunc,
			 xmlStrdupFunc strdupFunc);
XMLPUBFUN int
	xmlGcMemGet	(xmlFreeFunc *freeFunc,
			 xmlMallocFunc *mallocFunc,
			 xmlMallocFunc *mallocAtomicFunc,
			 xmlReallocFunc *reallocFunc,
			 xmlStrdupFunc *strdupFunc);

/*
 * Initialization of the memory layer.
 */
XML_DEPRECATED
XMLPUBFUN int
	xmlInitMemory	(void);

/*
 * Cleanup of the memory layer.
 */
XML_DEPRECATED
XMLPUBFUN void
                xmlCleanupMemory        (void);
/*
 * These are specific to the XML debug memory wrapper.
 */
XMLPUBFUN size_t
	xmlMemSize	(void *ptr);
XMLPUBFUN int
	xmlMemUsed	(void);
XMLPUBFUN int
	xmlMemBlocks	(void);
XMLPUBFUN void
	xmlMemDisplay	(FILE *fp);
XMLPUBFUN void
	xmlMemDisplayLast(FILE *fp, long nbBytes);
XMLPUBFUN void
	xmlMemShow	(FILE *fp, int nr);
XMLPUBFUN void
	xmlMemoryDump	(void);
XMLPUBFUN void *
	xmlMemMalloc	(size_t size) LIBXML_ATTR_ALLOC_SIZE(1);
XMLPUBFUN void *
	xmlMemRealloc	(void *ptr,size_t size);
XMLPUBFUN void
	xmlMemFree	(void *ptr);
XMLPUBFUN char *
	xmlMemoryStrdup	(const char *str);
XMLPUBFUN void *
	xmlMallocLoc	(size_t size, const char *file, int line) LIBXML_ATTR_ALLOC_SIZE(1);
XMLPUBFUN void *
	xmlReallocLoc	(void *ptr, size_t size, const char *file, int line);
XMLPUBFUN void *
	xmlMallocAtomicLoc (size_t size, const char *file, int line) LIBXML_ATTR_ALLOC_SIZE(1);
XMLPUBFUN char *
	xmlMemStrdupLoc	(const char *str, const char *file, int line);


/** DOC_DISABLE */
#ifdef DEBUG_MEMORY_LOCATION
/**
 * xmlMalloc:
 * @size:  number of bytes to allocate
 *
 * Wrapper for the malloc() function used in the XML library.
 *
 * Returns the pointer to the allocated area or NULL in case of error.
 */
#define xmlMalloc(size) xmlMallocLoc((size), __FILE__, __LINE__)
/**
 * xmlMallocAtomic:
 * @size:  number of bytes to allocate
 *
 * Wrapper for the malloc() function used in the XML library for allocation
 * of block not containing pointers to other areas.
 *
 * Returns the pointer to the allocated area or NULL in case of error.
 */
#define xmlMallocAtomic(size) xmlMallocAtomicLoc((size), __FILE__, __LINE__)
/**
 * xmlRealloc:
 * @ptr:  pointer to the existing allocated area
 * @size:  number of bytes to allocate
 *
 * Wrapper for the realloc() function used in the XML library.
 *
 * Returns the pointer to the allocated area or NULL in case of error.
 */
#define xmlRealloc(ptr, size) xmlReallocLoc((ptr), (size), __FILE__, __LINE__)
/**
 * xmlMemStrdup:
 * @str:  pointer to the existing string
 *
 * Wrapper for the strdup() function, xmlStrdup() is usually preferred.
 *
 * Returns the pointer to the allocated area or NULL in case of error.
 */
#define xmlMemStrdup(str) xmlMemStrdupLoc((str), __FILE__, __LINE__)

#endif /* DEBUG_MEMORY_LOCATION */
/** DOC_ENABLE */

#ifdef __cplusplus
}
#endif /* __cplusplus */

#endif  /* __DEBUG_MEMORY_ALLOC__ */

