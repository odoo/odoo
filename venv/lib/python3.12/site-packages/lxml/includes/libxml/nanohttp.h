/*
 * Summary: minimal HTTP implementation
 * Description: minimal HTTP implementation allowing to fetch resources
 *              like external subset.
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */

#ifndef __NANO_HTTP_H__
#define __NANO_HTTP_H__

#include <libxml/xmlversion.h>

#ifdef LIBXML_HTTP_ENABLED

#ifdef __cplusplus
extern "C" {
#endif
XMLPUBFUN void
	xmlNanoHTTPInit		(void);
XMLPUBFUN void
	xmlNanoHTTPCleanup	(void);
XMLPUBFUN void
	xmlNanoHTTPScanProxy	(const char *URL);
XMLPUBFUN int
	xmlNanoHTTPFetch	(const char *URL,
				 const char *filename,
				 char **contentType);
XMLPUBFUN void *
	xmlNanoHTTPMethod	(const char *URL,
				 const char *method,
				 const char *input,
				 char **contentType,
				 const char *headers,
				 int   ilen);
XMLPUBFUN void *
	xmlNanoHTTPMethodRedir	(const char *URL,
				 const char *method,
				 const char *input,
				 char **contentType,
				 char **redir,
				 const char *headers,
				 int   ilen);
XMLPUBFUN void *
	xmlNanoHTTPOpen		(const char *URL,
				 char **contentType);
XMLPUBFUN void *
	xmlNanoHTTPOpenRedir	(const char *URL,
				 char **contentType,
				 char **redir);
XMLPUBFUN int
	xmlNanoHTTPReturnCode	(void *ctx);
XMLPUBFUN const char *
	xmlNanoHTTPAuthHeader	(void *ctx);
XMLPUBFUN const char *
	xmlNanoHTTPRedir	(void *ctx);
XMLPUBFUN int
	xmlNanoHTTPContentLength( void * ctx );
XMLPUBFUN const char *
	xmlNanoHTTPEncoding	(void *ctx);
XMLPUBFUN const char *
	xmlNanoHTTPMimeType	(void *ctx);
XMLPUBFUN int
	xmlNanoHTTPRead		(void *ctx,
				 void *dest,
				 int len);
#ifdef LIBXML_OUTPUT_ENABLED
XMLPUBFUN int
	xmlNanoHTTPSave		(void *ctxt,
				 const char *filename);
#endif /* LIBXML_OUTPUT_ENABLED */
XMLPUBFUN void
	xmlNanoHTTPClose	(void *ctx);
#ifdef __cplusplus
}
#endif

#endif /* LIBXML_HTTP_ENABLED */
#endif /* __NANO_HTTP_H__ */
