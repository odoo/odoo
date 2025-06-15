/*
 * Summary: API to handle XML Pointers
 * Description: API to handle XML Pointers
 * Base implementation was made accordingly to
 * W3C Candidate Recommendation 7 June 2000
 * http://www.w3.org/TR/2000/CR-xptr-20000607
 *
 * Added support for the element() scheme described in:
 * W3C Proposed Recommendation 13 November 2002
 * http://www.w3.org/TR/2002/PR-xptr-element-20021113/
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */

#ifndef __XML_XPTR_H__
#define __XML_XPTR_H__

#include <libxml/xmlversion.h>

#ifdef LIBXML_XPTR_ENABLED

#include <libxml/tree.h>
#include <libxml/xpath.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(LIBXML_XPTR_LOCS_ENABLED)
/*
 * A Location Set
 */
typedef struct _xmlLocationSet xmlLocationSet;
typedef xmlLocationSet *xmlLocationSetPtr;
struct _xmlLocationSet {
    int locNr;		      /* number of locations in the set */
    int locMax;		      /* size of the array as allocated */
    xmlXPathObjectPtr *locTab;/* array of locations */
};

/*
 * Handling of location sets.
 */

XML_DEPRECATED
XMLPUBFUN xmlLocationSetPtr
		    xmlXPtrLocationSetCreate	(xmlXPathObjectPtr val);
XML_DEPRECATED
XMLPUBFUN void
		    xmlXPtrFreeLocationSet	(xmlLocationSetPtr obj);
XML_DEPRECATED
XMLPUBFUN xmlLocationSetPtr
		    xmlXPtrLocationSetMerge	(xmlLocationSetPtr val1,
						 xmlLocationSetPtr val2);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewRange		(xmlNodePtr start,
						 int startindex,
						 xmlNodePtr end,
						 int endindex);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewRangePoints	(xmlXPathObjectPtr start,
						 xmlXPathObjectPtr end);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewRangeNodePoint	(xmlNodePtr start,
						 xmlXPathObjectPtr end);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewRangePointNode	(xmlXPathObjectPtr start,
						 xmlNodePtr end);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewRangeNodes	(xmlNodePtr start,
						 xmlNodePtr end);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewLocationSetNodes	(xmlNodePtr start,
						 xmlNodePtr end);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewLocationSetNodeSet(xmlNodeSetPtr set);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewRangeNodeObject	(xmlNodePtr start,
						 xmlXPathObjectPtr end);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrNewCollapsedRange	(xmlNodePtr start);
XML_DEPRECATED
XMLPUBFUN void
		    xmlXPtrLocationSetAdd	(xmlLocationSetPtr cur,
						 xmlXPathObjectPtr val);
XML_DEPRECATED
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrWrapLocationSet	(xmlLocationSetPtr val);
XML_DEPRECATED
XMLPUBFUN void
		    xmlXPtrLocationSetDel	(xmlLocationSetPtr cur,
						 xmlXPathObjectPtr val);
XML_DEPRECATED
XMLPUBFUN void
		    xmlXPtrLocationSetRemove	(xmlLocationSetPtr cur,
						 int val);
#endif /* defined(LIBXML_XPTR_LOCS_ENABLED) */

/*
 * Functions.
 */
XMLPUBFUN xmlXPathContextPtr
		    xmlXPtrNewContext		(xmlDocPtr doc,
						 xmlNodePtr here,
						 xmlNodePtr origin);
XMLPUBFUN xmlXPathObjectPtr
		    xmlXPtrEval			(const xmlChar *str,
						 xmlXPathContextPtr ctx);

#if defined(LIBXML_XPTR_LOCS_ENABLED)
XML_DEPRECATED
XMLPUBFUN void
		    xmlXPtrRangeToFunction	(xmlXPathParserContextPtr ctxt,
						 int nargs);
XML_DEPRECATED
XMLPUBFUN xmlNodePtr
		    xmlXPtrBuildNodeList	(xmlXPathObjectPtr obj);
XML_DEPRECATED
XMLPUBFUN void
		    xmlXPtrEvalRangePredicate	(xmlXPathParserContextPtr ctxt);
#endif /* defined(LIBXML_XPTR_LOCS_ENABLED) */
#ifdef __cplusplus
}
#endif

#endif /* LIBXML_XPTR_ENABLED */
#endif /* __XML_XPTR_H__ */
