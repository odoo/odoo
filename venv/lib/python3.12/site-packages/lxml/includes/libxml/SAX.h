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

#include <libxml/xmlversion.h>
#include <libxml/parser.h>

#ifdef LIBXML_LEGACY_ENABLED

#ifdef __cplusplus
extern "C" {
#endif
XML_DEPRECATED
XMLPUBFUN const xmlChar *
		getPublicId			(void *ctx);
XML_DEPRECATED
XMLPUBFUN const xmlChar *
		getSystemId			(void *ctx);
XML_DEPRECATED
XMLPUBFUN void
		setDocumentLocator		(void *ctx,
						 xmlSAXLocatorPtr loc);

XML_DEPRECATED
XMLPUBFUN int
		getLineNumber			(void *ctx);
XML_DEPRECATED
XMLPUBFUN int
		getColumnNumber			(void *ctx);

XML_DEPRECATED
XMLPUBFUN int
		isStandalone			(void *ctx);
XML_DEPRECATED
XMLPUBFUN int
		hasInternalSubset		(void *ctx);
XML_DEPRECATED
XMLPUBFUN int
		hasExternalSubset		(void *ctx);

XML_DEPRECATED
XMLPUBFUN void
		internalSubset			(void *ctx,
						 const xmlChar *name,
						 const xmlChar *ExternalID,
						 const xmlChar *SystemID);
XML_DEPRECATED
XMLPUBFUN void
		externalSubset			(void *ctx,
						 const xmlChar *name,
						 const xmlChar *ExternalID,
						 const xmlChar *SystemID);
XML_DEPRECATED
XMLPUBFUN xmlEntityPtr
		getEntity			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN xmlEntityPtr
		getParameterEntity		(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN xmlParserInputPtr
		resolveEntity			(void *ctx,
						 const xmlChar *publicId,
						 const xmlChar *systemId);

XML_DEPRECATED
XMLPUBFUN void
		entityDecl			(void *ctx,
						 const xmlChar *name,
						 int type,
						 const xmlChar *publicId,
						 const xmlChar *systemId,
						 xmlChar *content);
XML_DEPRECATED
XMLPUBFUN void
		attributeDecl			(void *ctx,
						 const xmlChar *elem,
						 const xmlChar *fullname,
						 int type,
						 int def,
						 const xmlChar *defaultValue,
						 xmlEnumerationPtr tree);
XML_DEPRECATED
XMLPUBFUN void
		elementDecl			(void *ctx,
						 const xmlChar *name,
						 int type,
						 xmlElementContentPtr content);
XML_DEPRECATED
XMLPUBFUN void
		notationDecl			(void *ctx,
						 const xmlChar *name,
						 const xmlChar *publicId,
						 const xmlChar *systemId);
XML_DEPRECATED
XMLPUBFUN void
		unparsedEntityDecl		(void *ctx,
						 const xmlChar *name,
						 const xmlChar *publicId,
						 const xmlChar *systemId,
						 const xmlChar *notationName);

XML_DEPRECATED
XMLPUBFUN void
		startDocument			(void *ctx);
XML_DEPRECATED
XMLPUBFUN void
		endDocument			(void *ctx);
XML_DEPRECATED
XMLPUBFUN void
		attribute			(void *ctx,
						 const xmlChar *fullname,
						 const xmlChar *value);
XML_DEPRECATED
XMLPUBFUN void
		startElement			(void *ctx,
						 const xmlChar *fullname,
						 const xmlChar **atts);
XML_DEPRECATED
XMLPUBFUN void
		endElement			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN void
		reference			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN void
		characters			(void *ctx,
						 const xmlChar *ch,
						 int len);
XML_DEPRECATED
XMLPUBFUN void
		ignorableWhitespace		(void *ctx,
						 const xmlChar *ch,
						 int len);
XML_DEPRECATED
XMLPUBFUN void
		processingInstruction		(void *ctx,
						 const xmlChar *target,
						 const xmlChar *data);
XML_DEPRECATED
XMLPUBFUN void
		globalNamespace			(void *ctx,
						 const xmlChar *href,
						 const xmlChar *prefix);
XML_DEPRECATED
XMLPUBFUN void
		setNamespace			(void *ctx,
						 const xmlChar *name);
XML_DEPRECATED
XMLPUBFUN xmlNsPtr
		getNamespace			(void *ctx);
XML_DEPRECATED
XMLPUBFUN int
		checkNamespace			(void *ctx,
						 xmlChar *nameSpace);
XML_DEPRECATED
XMLPUBFUN void
		namespaceDecl			(void *ctx,
						 const xmlChar *href,
						 const xmlChar *prefix);
XML_DEPRECATED
XMLPUBFUN void
		comment				(void *ctx,
						 const xmlChar *value);
XML_DEPRECATED
XMLPUBFUN void
		cdataBlock			(void *ctx,
						 const xmlChar *value,
						 int len);

#ifdef LIBXML_SAX1_ENABLED
XML_DEPRECATED
XMLPUBFUN void
		initxmlDefaultSAXHandler	(xmlSAXHandlerV1 *hdlr,
						 int warning);
#ifdef LIBXML_HTML_ENABLED
XML_DEPRECATED
XMLPUBFUN void
		inithtmlDefaultSAXHandler	(xmlSAXHandlerV1 *hdlr);
#endif
#endif /* LIBXML_SAX1_ENABLED */

#ifdef __cplusplus
}
#endif

#endif /* LIBXML_LEGACY_ENABLED */

#endif /* __XML_SAX_H__ */
