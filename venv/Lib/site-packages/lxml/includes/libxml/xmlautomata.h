/*
 * Summary: API to build regexp automata
 * Description: the API to build regexp automata
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */

#ifndef __XML_AUTOMATA_H__
#define __XML_AUTOMATA_H__

#include <libxml/xmlversion.h>

#ifdef LIBXML_REGEXP_ENABLED
#ifdef LIBXML_AUTOMATA_ENABLED

#include <libxml/xmlstring.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * xmlAutomataPtr:
 *
 * A libxml automata description, It can be compiled into a regexp
 */
typedef struct _xmlAutomata xmlAutomata;
typedef xmlAutomata *xmlAutomataPtr;

/**
 * xmlAutomataStatePtr:
 *
 * A state int the automata description,
 */
typedef struct _xmlAutomataState xmlAutomataState;
typedef xmlAutomataState *xmlAutomataStatePtr;

/*
 * Building API
 */
XMLPUBFUN xmlAutomataPtr
		    xmlNewAutomata		(void);
XMLPUBFUN void
		    xmlFreeAutomata		(xmlAutomataPtr am);

XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataGetInitState	(xmlAutomataPtr am);
XMLPUBFUN int
		    xmlAutomataSetFinalState	(xmlAutomataPtr am,
						 xmlAutomataStatePtr state);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewState		(xmlAutomataPtr am);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewTransition	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 void *data);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewTransition2	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 const xmlChar *token2,
						 void *data);
XMLPUBFUN xmlAutomataStatePtr
                    xmlAutomataNewNegTrans	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 const xmlChar *token2,
						 void *data);

XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewCountTrans	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 int min,
						 int max,
						 void *data);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewCountTrans2	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 const xmlChar *token2,
						 int min,
						 int max,
						 void *data);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewOnceTrans	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 int min,
						 int max,
						 void *data);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewOnceTrans2	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 const xmlChar *token,
						 const xmlChar *token2,
						 int min,
						 int max,
						 void *data);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewAllTrans	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 int lax);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewEpsilon	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewCountedTrans	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 int counter);
XMLPUBFUN xmlAutomataStatePtr
		    xmlAutomataNewCounterTrans	(xmlAutomataPtr am,
						 xmlAutomataStatePtr from,
						 xmlAutomataStatePtr to,
						 int counter);
XMLPUBFUN int
		    xmlAutomataNewCounter	(xmlAutomataPtr am,
						 int min,
						 int max);

XMLPUBFUN struct _xmlRegexp *
		    xmlAutomataCompile		(xmlAutomataPtr am);
XMLPUBFUN int
		    xmlAutomataIsDeterminist	(xmlAutomataPtr am);

#ifdef __cplusplus
}
#endif

#endif /* LIBXML_AUTOMATA_ENABLED */
#endif /* LIBXML_REGEXP_ENABLED */

#endif /* __XML_AUTOMATA_H__ */
