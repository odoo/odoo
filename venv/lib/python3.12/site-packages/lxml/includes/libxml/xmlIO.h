/*
 * Summary: interface for the I/O interfaces used by the parser
 * Description: interface for the I/O interfaces used by the parser
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */

#ifndef __XML_IO_H__
#define __XML_IO_H__

#include <stdio.h>
#include <libxml/xmlversion.h>
#include <libxml/encoding.h>
#define XML_TREE_INTERNALS
#include <libxml/tree.h>
#undef XML_TREE_INTERNALS

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Those are the functions and datatypes for the parser input
 * I/O structures.
 */

/**
 * xmlInputMatchCallback:
 * @filename: the filename or URI
 *
 * Callback used in the I/O Input API to detect if the current handler
 * can provide input functionality for this resource.
 *
 * Returns 1 if yes and 0 if another Input module should be used
 */
typedef int (*xmlInputMatchCallback) (char const *filename);
/**
 * xmlInputOpenCallback:
 * @filename: the filename or URI
 *
 * Callback used in the I/O Input API to open the resource
 *
 * Returns an Input context or NULL in case or error
 */
typedef void * (*xmlInputOpenCallback) (char const *filename);
/**
 * xmlInputReadCallback:
 * @context:  an Input context
 * @buffer:  the buffer to store data read
 * @len:  the length of the buffer in bytes
 *
 * Callback used in the I/O Input API to read the resource
 *
 * Returns the number of bytes read or -1 in case of error
 */
typedef int (*xmlInputReadCallback) (void * context, char * buffer, int len);
/**
 * xmlInputCloseCallback:
 * @context:  an Input context
 *
 * Callback used in the I/O Input API to close the resource
 *
 * Returns 0 or -1 in case of error
 */
typedef int (*xmlInputCloseCallback) (void * context);

#ifdef LIBXML_OUTPUT_ENABLED
/*
 * Those are the functions and datatypes for the library output
 * I/O structures.
 */

/**
 * xmlOutputMatchCallback:
 * @filename: the filename or URI
 *
 * Callback used in the I/O Output API to detect if the current handler
 * can provide output functionality for this resource.
 *
 * Returns 1 if yes and 0 if another Output module should be used
 */
typedef int (*xmlOutputMatchCallback) (char const *filename);
/**
 * xmlOutputOpenCallback:
 * @filename: the filename or URI
 *
 * Callback used in the I/O Output API to open the resource
 *
 * Returns an Output context or NULL in case or error
 */
typedef void * (*xmlOutputOpenCallback) (char const *filename);
/**
 * xmlOutputWriteCallback:
 * @context:  an Output context
 * @buffer:  the buffer of data to write
 * @len:  the length of the buffer in bytes
 *
 * Callback used in the I/O Output API to write to the resource
 *
 * Returns the number of bytes written or -1 in case of error
 */
typedef int (*xmlOutputWriteCallback) (void * context, const char * buffer,
                                       int len);
/**
 * xmlOutputCloseCallback:
 * @context:  an Output context
 *
 * Callback used in the I/O Output API to close the resource
 *
 * Returns 0 or -1 in case of error
 */
typedef int (*xmlOutputCloseCallback) (void * context);
#endif /* LIBXML_OUTPUT_ENABLED */

/**
 * xmlParserInputBufferCreateFilenameFunc:
 * @URI: the URI to read from
 * @enc: the requested source encoding
 *
 * Signature for the function doing the lookup for a suitable input method
 * corresponding to an URI.
 *
 * Returns the new xmlParserInputBufferPtr in case of success or NULL if no
 *         method was found.
 */
typedef xmlParserInputBufferPtr
(*xmlParserInputBufferCreateFilenameFunc)(const char *URI, xmlCharEncoding enc);

/**
 * xmlOutputBufferCreateFilenameFunc:
 * @URI: the URI to write to
 * @enc: the requested target encoding
 *
 * Signature for the function doing the lookup for a suitable output method
 * corresponding to an URI.
 *
 * Returns the new xmlOutputBufferPtr in case of success or NULL if no
 *         method was found.
 */
typedef xmlOutputBufferPtr
(*xmlOutputBufferCreateFilenameFunc)(const char *URI,
        xmlCharEncodingHandlerPtr encoder, int compression);

struct _xmlParserInputBuffer {
    void*                  context;
    xmlInputReadCallback   readcallback;
    xmlInputCloseCallback  closecallback;

    xmlCharEncodingHandlerPtr encoder; /* I18N conversions to UTF-8 */

    xmlBufPtr buffer;    /* Local buffer encoded in UTF-8 */
    xmlBufPtr raw;       /* if encoder != NULL buffer for raw input */
    int	compressed;	    /* -1=unknown, 0=not compressed, 1=compressed */
    int error;
    unsigned long rawconsumed;/* amount consumed from raw */
};


#ifdef LIBXML_OUTPUT_ENABLED
struct _xmlOutputBuffer {
    void*                   context;
    xmlOutputWriteCallback  writecallback;
    xmlOutputCloseCallback  closecallback;

    xmlCharEncodingHandlerPtr encoder; /* I18N conversions to UTF-8 */

    xmlBufPtr buffer;    /* Local buffer encoded in UTF-8 or ISOLatin */
    xmlBufPtr conv;      /* if encoder != NULL buffer for output */
    int written;            /* total number of byte written */
    int error;
};
#endif /* LIBXML_OUTPUT_ENABLED */

/** DOC_DISABLE */
#define XML_GLOBALS_IO \
  XML_OP(xmlParserInputBufferCreateFilenameValue, \
           xmlParserInputBufferCreateFilenameFunc, XML_DEPRECATED) \
  XML_OP(xmlOutputBufferCreateFilenameValue, \
           xmlOutputBufferCreateFilenameFunc, XML_DEPRECATED)

#define XML_OP XML_DECLARE_GLOBAL
XML_GLOBALS_IO
#undef XML_OP

#if defined(LIBXML_THREAD_ENABLED) && !defined(XML_GLOBALS_NO_REDEFINITION)
  #define xmlParserInputBufferCreateFilenameValue \
    XML_GLOBAL_MACRO(xmlParserInputBufferCreateFilenameValue)
  #define xmlOutputBufferCreateFilenameValue \
    XML_GLOBAL_MACRO(xmlOutputBufferCreateFilenameValue)
#endif
/** DOC_ENABLE */

/*
 * Interfaces for input
 */
XMLPUBFUN void
	xmlCleanupInputCallbacks		(void);

XMLPUBFUN int
	xmlPopInputCallbacks			(void);

XMLPUBFUN void
	xmlRegisterDefaultInputCallbacks	(void);
XMLPUBFUN xmlParserInputBufferPtr
	xmlAllocParserInputBuffer		(xmlCharEncoding enc);

XMLPUBFUN xmlParserInputBufferPtr
	xmlParserInputBufferCreateFilename	(const char *URI,
                                                 xmlCharEncoding enc);
XMLPUBFUN xmlParserInputBufferPtr
	xmlParserInputBufferCreateFile		(FILE *file,
                                                 xmlCharEncoding enc);
XMLPUBFUN xmlParserInputBufferPtr
	xmlParserInputBufferCreateFd		(int fd,
	                                         xmlCharEncoding enc);
XMLPUBFUN xmlParserInputBufferPtr
	xmlParserInputBufferCreateMem		(const char *mem, int size,
	                                         xmlCharEncoding enc);
XMLPUBFUN xmlParserInputBufferPtr
	xmlParserInputBufferCreateStatic	(const char *mem, int size,
	                                         xmlCharEncoding enc);
XMLPUBFUN xmlParserInputBufferPtr
	xmlParserInputBufferCreateIO		(xmlInputReadCallback   ioread,
						 xmlInputCloseCallback  ioclose,
						 void *ioctx,
	                                         xmlCharEncoding enc);
XMLPUBFUN int
	xmlParserInputBufferRead		(xmlParserInputBufferPtr in,
						 int len);
XMLPUBFUN int
	xmlParserInputBufferGrow		(xmlParserInputBufferPtr in,
						 int len);
XMLPUBFUN int
	xmlParserInputBufferPush		(xmlParserInputBufferPtr in,
						 int len,
						 const char *buf);
XMLPUBFUN void
	xmlFreeParserInputBuffer		(xmlParserInputBufferPtr in);
XMLPUBFUN char *
	xmlParserGetDirectory			(const char *filename);

XMLPUBFUN int
	xmlRegisterInputCallbacks		(xmlInputMatchCallback matchFunc,
						 xmlInputOpenCallback openFunc,
						 xmlInputReadCallback readFunc,
						 xmlInputCloseCallback closeFunc);

xmlParserInputBufferPtr
	__xmlParserInputBufferCreateFilename(const char *URI,
						xmlCharEncoding enc);

#ifdef LIBXML_OUTPUT_ENABLED
/*
 * Interfaces for output
 */
XMLPUBFUN void
	xmlCleanupOutputCallbacks		(void);
XMLPUBFUN int
	xmlPopOutputCallbacks			(void);
XMLPUBFUN void
	xmlRegisterDefaultOutputCallbacks(void);
XMLPUBFUN xmlOutputBufferPtr
	xmlAllocOutputBuffer		(xmlCharEncodingHandlerPtr encoder);

XMLPUBFUN xmlOutputBufferPtr
	xmlOutputBufferCreateFilename	(const char *URI,
					 xmlCharEncodingHandlerPtr encoder,
					 int compression);

XMLPUBFUN xmlOutputBufferPtr
	xmlOutputBufferCreateFile	(FILE *file,
					 xmlCharEncodingHandlerPtr encoder);

XMLPUBFUN xmlOutputBufferPtr
	xmlOutputBufferCreateBuffer	(xmlBufferPtr buffer,
					 xmlCharEncodingHandlerPtr encoder);

XMLPUBFUN xmlOutputBufferPtr
	xmlOutputBufferCreateFd		(int fd,
					 xmlCharEncodingHandlerPtr encoder);

XMLPUBFUN xmlOutputBufferPtr
	xmlOutputBufferCreateIO		(xmlOutputWriteCallback   iowrite,
					 xmlOutputCloseCallback  ioclose,
					 void *ioctx,
					 xmlCharEncodingHandlerPtr encoder);

/* Couple of APIs to get the output without digging into the buffers */
XMLPUBFUN const xmlChar *
        xmlOutputBufferGetContent       (xmlOutputBufferPtr out);
XMLPUBFUN size_t
        xmlOutputBufferGetSize          (xmlOutputBufferPtr out);

XMLPUBFUN int
	xmlOutputBufferWrite		(xmlOutputBufferPtr out,
					 int len,
					 const char *buf);
XMLPUBFUN int
	xmlOutputBufferWriteString	(xmlOutputBufferPtr out,
					 const char *str);
XMLPUBFUN int
	xmlOutputBufferWriteEscape	(xmlOutputBufferPtr out,
					 const xmlChar *str,
					 xmlCharEncodingOutputFunc escaping);

XMLPUBFUN int
	xmlOutputBufferFlush		(xmlOutputBufferPtr out);
XMLPUBFUN int
	xmlOutputBufferClose		(xmlOutputBufferPtr out);

XMLPUBFUN int
	xmlRegisterOutputCallbacks	(xmlOutputMatchCallback matchFunc,
					 xmlOutputOpenCallback openFunc,
					 xmlOutputWriteCallback writeFunc,
					 xmlOutputCloseCallback closeFunc);

xmlOutputBufferPtr
	__xmlOutputBufferCreateFilename(const char *URI,
                              xmlCharEncodingHandlerPtr encoder,
                              int compression);

#ifdef LIBXML_HTTP_ENABLED
/*  This function only exists if HTTP support built into the library  */
XMLPUBFUN void
	xmlRegisterHTTPPostCallbacks	(void );
#endif /* LIBXML_HTTP_ENABLED */

#endif /* LIBXML_OUTPUT_ENABLED */

XMLPUBFUN xmlParserInputPtr
	xmlCheckHTTPInput		(xmlParserCtxtPtr ctxt,
					 xmlParserInputPtr ret);

/*
 * A predefined entity loader disabling network accesses
 */
XMLPUBFUN xmlParserInputPtr
	xmlNoNetExternalEntityLoader	(const char *URL,
					 const char *ID,
					 xmlParserCtxtPtr ctxt);

/*
 * xmlNormalizeWindowsPath is obsolete, don't use it.
 * Check xmlCanonicPath in uri.h for a better alternative.
 */
XMLPUBFUN xmlChar *
	xmlNormalizeWindowsPath		(const xmlChar *path);

XMLPUBFUN int
	xmlCheckFilename		(const char *path);
/**
 * Default 'file://' protocol callbacks
 */
XMLPUBFUN int
	xmlFileMatch			(const char *filename);
XMLPUBFUN void *
	xmlFileOpen			(const char *filename);
XMLPUBFUN int
	xmlFileRead			(void * context,
					 char * buffer,
					 int len);
XMLPUBFUN int
	xmlFileClose			(void * context);

/**
 * Default 'http://' protocol callbacks
 */
#ifdef LIBXML_HTTP_ENABLED
XMLPUBFUN int
	xmlIOHTTPMatch			(const char *filename);
XMLPUBFUN void *
	xmlIOHTTPOpen			(const char *filename);
#ifdef LIBXML_OUTPUT_ENABLED
XMLPUBFUN void *
	xmlIOHTTPOpenW			(const char * post_uri,
					 int   compression );
#endif /* LIBXML_OUTPUT_ENABLED */
XMLPUBFUN int
	xmlIOHTTPRead			(void * context,
					 char * buffer,
					 int len);
XMLPUBFUN int
	xmlIOHTTPClose			(void * context);
#endif /* LIBXML_HTTP_ENABLED */

/**
 * Default 'ftp://' protocol callbacks
 */
#if defined(LIBXML_FTP_ENABLED)
XMLPUBFUN int
	xmlIOFTPMatch			(const char *filename);
XMLPUBFUN void *
	xmlIOFTPOpen			(const char *filename);
XMLPUBFUN int
	xmlIOFTPRead			(void * context,
					 char * buffer,
					 int len);
XMLPUBFUN int
	xmlIOFTPClose			(void * context);
#endif /* defined(LIBXML_FTP_ENABLED) */

XMLPUBFUN xmlParserInputBufferCreateFilenameFunc
	xmlParserInputBufferCreateFilenameDefault(
		xmlParserInputBufferCreateFilenameFunc func);
XMLPUBFUN xmlOutputBufferCreateFilenameFunc
	xmlOutputBufferCreateFilenameDefault(
		xmlOutputBufferCreateFilenameFunc func);
XMLPUBFUN xmlOutputBufferCreateFilenameFunc
	xmlThrDefOutputBufferCreateFilenameDefault(
		xmlOutputBufferCreateFilenameFunc func);
XMLPUBFUN xmlParserInputBufferCreateFilenameFunc
	xmlThrDefParserInputBufferCreateFilenameDefault(
		xmlParserInputBufferCreateFilenameFunc func);

#ifdef __cplusplus
}
#endif

#endif /* __XML_IO_H__ */
