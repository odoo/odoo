/*
 * Summary: Old SAX version 1 handler, deprecated
 * Description: DEPRECATED set of SAX version 1 interfaces used to
 *              build the DOM tree.
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */


#ifndef __XML_SAX_H__
#define __XML_SAX_H__

#include <stdio.h>
#include <stdlib.h>
#include <libxml/xmlversion.h>
#include <libxml/parser.h>

#ifdef LIBXML_LEGACY_ENABLED

#ifdef __cplusplus
extern "C" {
#endif
XML_DEPRECATED
XMLPUBFUN const xmlChar * XMLCALL
		getPublicId			(void *ctx);
XML_DEPRECATED
XMLPUBFUN const xmlChar * XMLCALL
		getSystemId			(void *ctx);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		setDocumentLocator		(void *ctx,
						 xmlSAXLocatorPtr loc);

XML_DEPRECATED
XMLPUBFUN int XMLCALL
		getLineNumber			(void *ctx);
XML_DEPRECATED
XMLPUBFUN int XMLCALL
		getColumnNumber			(void *ctx);

XML_DEPRECATED
XMLPUBFUN int XMLCALL
		isStandalone			(void *ctx);
XML_DEPRECATED
XMLPUBFUN int XMLCALL
		hasInternalSubset		(void *ctx);
XML_DEPRECATED
XMLPUBFUN int XMLCALL
		hasExternalSubset		(void *ctx);

XML_DEPRECATED
XMLPUBFUN void XMLCALL
		internalSubset			(void *ctx,
						 const xmlChar *name,
						 const xmlChar *ExternalID,
						 const xmlChar *SystemID);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		externalSubset			(void *ctx,
						 const xmlChar *name,
						 const xmlChar *ExternalID,
						 const xmlChar *SystemID);
XML_DEPRECATED
XMLPUBFUN xmlEntityPtr XMLCALL
		getEntity			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN xmlEntityPtr XMLCALL
		getParameterEntity		(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN xmlParserInputPtr XMLCALL
		resolveEntity			(void *ctx,
						 const xmlChar *publicId,
						 const xmlChar *systemId);

XML_DEPRECATED
XMLPUBFUN void XMLCALL
		entityDecl			(void *ctx,
						 const xmlChar *name,
						 int type,
						 const xmlChar *publicId,
						 const xmlChar *systemId,
						 xmlChar *content);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		attributeDecl			(void *ctx,
						 const xmlChar *elem,
						 const xmlChar *fullname,
						 int type,
						 int def,
						 const xmlChar *defaultValue,
						 xmlEnumerationPtr tree);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		elementDecl			(void *ctx,
						 const xmlChar *name,
						 int type,
						 xmlElementContentPtr content);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		notationDecl			(void *ctx,
						 const xmlChar *name,
						 const xmlChar *publicId,
						 const xmlChar *systemId);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		unparsedEntityDecl		(void *ctx,
						 const xmlChar *name,
						 const xmlChar *publicId,
						 const xmlChar *systemId,
						 const xmlChar *notationName);

XML_DEPRECATED
XMLPUBFUN void XMLCALL
		startDocument			(void *ctx);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		endDocument			(void *ctx);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		attribute			(void *ctx,
						 const xmlChar *fullname,
						 const xmlChar *value);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		startElement			(void *ctx,
						 const xmlChar *fullname,
						 const xmlChar **atts);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		endElement			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		reference			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		characters			(void *ctx,
						 const xmlChar *ch,
						 int len);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		ignorableWhitespace		(void *ctx,
						 const xmlChar *ch,
						 int len);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		processingInstruction		(void *ctx,
						 const xmlChar *target,
						 const xmlChar *data);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		globalNamespace			(void *ctx,
						 const xmlChar *href,
						 const xmlChar *prefix);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		setNamespace			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN xmlNsPtr XMLCALL
		getNamespace			(void *ctx);
XML_DEPRECATED
XMLPUBFUN int XMLCALL
		checkNamespace			(void *ctx,
						 xmlChar *nameSpace);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		namespaceDecl			(void *ctx,
						 const xmlChar *href,
						 const xmlChar *prefix);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		comment				(void *ctx,
						 const xmlChar *value);
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		cdataBlock			(void *ctx,
						 const xmlChar *value,
						 int len);

#ifdef LIBXML_SAX1_ENABLED
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		initxmlDefaultSAXHandler	(xmlSAXHandlerV1 *hdlr,
						 int warning);
#ifdef LIBXML_HTML_ENABLED
XML_DEPRECATED
XMLPUBFUN void XMLCALL
		inithtmlDefaultSAXHandler	(xmlSAXHandlerV1 *hdlr);
#endif
#endif /* LIBXML_SAX1_ENABLED */

#ifdef __cplusplus
}
#endif

#endif /* LIBXML_LEGACY_ENABLED */

#endif /* __XML_SAX_H__ */
