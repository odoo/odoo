/*
 * Summary: the core parser module
 * Description: Interfaces, constants and types related to the XML parser
 *
 * Copy: See Copyright for the status of this software.
 *
 * Author: Daniel Veillard
 */

#ifndef __XML_PARSER_H__
#define __XML_PARSER_H__

#include <libxml/xmlversion.h>
#define XML_TREE_INTERNALS
#include <libxml/tree.h>
#undef XML_TREE_INTERNALS
#include <libxml/dict.h>
#include <libxml/hash.h>
#include <libxml/valid.h>
#include <libxml/entities.h>
#include <libxml/xmlerror.h>
#include <libxml/xmlstring.h>
#include <libxml/xmlmemory.h>
#include <libxml/encoding.h>
#include <libxml/xmlIO.h>
/* for compatibility */
#include <libxml/SAX2.h>
#include <libxml/threads.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * XML_DEFAULT_VERSION:
 *
 * The default version of XML used: 1.0
 */
#define XML_DEFAULT_VERSION	"1.0"

/**
 * xmlParserInput:
 *
 * An xmlParserInput is an input flow for the XML processor.
 * Each entity parsed is associated an xmlParserInput (except the
 * few predefined ones). This is the case both for internal entities
 * - in which case the flow is already completely in memory - or
 * external entities - in which case we use the buf structure for
 * progressive reading and I18N conversions to the internal UTF-8 format.
 */

/**
 * xmlParserInputDeallocate:
 * @str:  the string to deallocate
 *
 * Callback for freeing some parser input allocations.
 */
typedef void (* xmlParserInputDeallocate)(xmlChar *str);

struct _xmlParserInput {
    /* Input buffer */
    xmlParserInputBufferPtr buf;      /* UTF-8 encoded buffer */

    const char *filename;             /* The file analyzed, if any */
    const char *directory;            /* the directory/base of the file */
    const xmlChar *base;              /* Base of the array to parse */
    const xmlChar *cur;               /* Current char being parsed */
    const xmlChar *end;               /* end of the array to parse */
    int length;                       /* length if known */
    int line;                         /* Current line */
    int col;                          /* Current column */
    unsigned long consumed;           /* How many xmlChars already consumed */
    xmlParserInputDeallocate free;    /* function to deallocate the base */
    const xmlChar *encoding;          /* unused */
    const xmlChar *version;           /* the version string for entity */
    int flags;                        /* Flags */
    int id;                           /* an unique identifier for the entity */
    unsigned long parentConsumed;     /* consumed bytes from parents */
    xmlEntityPtr entity;              /* entity, if any */
};

/**
 * xmlParserNodeInfo:
 *
 * The parser can be asked to collect Node information, i.e. at what
 * place in the file they were detected.
 * NOTE: This is off by default and not very well tested.
 */
typedef struct _xmlParserNodeInfo xmlParserNodeInfo;
typedef xmlParserNodeInfo *xmlParserNodeInfoPtr;

struct _xmlParserNodeInfo {
  const struct _xmlNode* node;
  /* Position & line # that text that created the node begins & ends on */
  unsigned long begin_pos;
  unsigned long begin_line;
  unsigned long end_pos;
  unsigned long end_line;
};

typedef struct _xmlParserNodeInfoSeq xmlParserNodeInfoSeq;
typedef xmlParserNodeInfoSeq *xmlParserNodeInfoSeqPtr;
struct _xmlParserNodeInfoSeq {
  unsigned long maximum;
  unsigned long length;
  xmlParserNodeInfo* buffer;
};

/**
 * xmlParserInputState:
 *
 * The parser is now working also as a state based parser.
 * The recursive one use the state info for entities processing.
 */
typedef enum {
    XML_PARSER_EOF = -1,	/* nothing is to be parsed */
    XML_PARSER_START = 0,	/* nothing has been parsed */
    XML_PARSER_MISC,		/* Misc* before int subset */
    XML_PARSER_PI,		/* Within a processing instruction */
    XML_PARSER_DTD,		/* within some DTD content */
    XML_PARSER_PROLOG,		/* Misc* after internal subset */
    XML_PARSER_COMMENT,		/* within a comment */
    XML_PARSER_START_TAG,	/* within a start tag */
    XML_PARSER_CONTENT,		/* within the content */
    XML_PARSER_CDATA_SECTION,	/* within a CDATA section */
    XML_PARSER_END_TAG,		/* within a closing tag */
    XML_PARSER_ENTITY_DECL,	/* within an entity declaration */
    XML_PARSER_ENTITY_VALUE,	/* within an entity value in a decl */
    XML_PARSER_ATTRIBUTE_VALUE,	/* within an attribute value */
    XML_PARSER_SYSTEM_LITERAL,	/* within a SYSTEM value */
    XML_PARSER_EPILOG,		/* the Misc* after the last end tag */
    XML_PARSER_IGNORE,		/* within an IGNORED section */
    XML_PARSER_PUBLIC_LITERAL,	/* within a PUBLIC value */
    XML_PARSER_XML_DECL         /* before XML decl (but after BOM) */
} xmlParserInputState;

/**
 * XML_DETECT_IDS:
 *
 * Bit in the loadsubset context field to tell to do ID/REFs lookups.
 * Use it to initialize xmlLoadExtDtdDefaultValue.
 */
#define XML_DETECT_IDS		2

/**
 * XML_COMPLETE_ATTRS:
 *
 * Bit in the loadsubset context field to tell to do complete the
 * elements attributes lists with the ones defaulted from the DTDs.
 * Use it to initialize xmlLoadExtDtdDefaultValue.
 */
#define XML_COMPLETE_ATTRS	4

/**
 * XML_SKIP_IDS:
 *
 * Bit in the loadsubset context field to tell to not do ID/REFs registration.
 * Used to initialize xmlLoadExtDtdDefaultValue in some special cases.
 */
#define XML_SKIP_IDS		8

/**
 * xmlParserMode:
 *
 * A parser can operate in various modes
 */
typedef enum {
    XML_PARSE_UNKNOWN = 0,
    XML_PARSE_DOM = 1,
    XML_PARSE_SAX = 2,
    XML_PARSE_PUSH_DOM = 3,
    XML_PARSE_PUSH_SAX = 4,
    XML_PARSE_READER = 5
} xmlParserMode;

typedef struct _xmlStartTag xmlStartTag;
typedef struct _xmlParserNsData xmlParserNsData;
typedef struct _xmlAttrHashBucket xmlAttrHashBucket;

/**
 * xmlParserCtxt:
 *
 * The parser context.
 * NOTE This doesn't completely define the parser state, the (current ?)
 *      design of the parser uses recursive function calls since this allow
 *      and easy mapping from the production rules of the specification
 *      to the actual code. The drawback is that the actual function call
 *      also reflect the parser state. However most of the parsing routines
 *      takes as the only argument the parser context pointer, so migrating
 *      to a state based parser for progressive parsing shouldn't be too hard.
 */
struct _xmlParserCtxt {
    struct _xmlSAXHandler *sax;       /* The SAX handler */
    void            *userData;        /* For SAX interface only, used by DOM build */
    xmlDocPtr           myDoc;        /* the document being built */
    int            wellFormed;        /* is the document well formed */
    int       replaceEntities;        /* shall we replace entities ? */
    const xmlChar    *version;        /* the XML version string */
    const xmlChar   *encoding;        /* the declared encoding, if any */
    int            standalone;        /* standalone document */
    int                  html;        /* an HTML(1) document
                                       * 3 is HTML after <head>
                                       * 10 is HTML after <body>
                                       */

    /* Input stream stack */
    xmlParserInputPtr  input;         /* Current input stream */
    int                inputNr;       /* Number of current input streams */
    int                inputMax;      /* Max number of input streams */
    xmlParserInputPtr *inputTab;      /* stack of inputs */

    /* Node analysis stack only used for DOM building */
    xmlNodePtr         node;          /* Current parsed Node */
    int                nodeNr;        /* Depth of the parsing stack */
    int                nodeMax;       /* Max depth of the parsing stack */
    xmlNodePtr        *nodeTab;       /* array of nodes */

    int record_info;                  /* Whether node info should be kept */
    xmlParserNodeInfoSeq node_seq;    /* info about each node parsed */

    int errNo;                        /* error code */

    int     hasExternalSubset;        /* reference and external subset */
    int             hasPErefs;        /* the internal subset has PE refs */
    int              external;        /* are we parsing an external entity */

    int                 valid;        /* is the document valid */
    int              validate;        /* shall we try to validate ? */
    xmlValidCtxt        vctxt;        /* The validity context */

    xmlParserInputState instate;      /* current type of input */
    int                 token;        /* next char look-ahead */

    char           *directory;        /* the data directory */

    /* Node name stack */
    const xmlChar     *name;          /* Current parsed Node */
    int                nameNr;        /* Depth of the parsing stack */
    int                nameMax;       /* Max depth of the parsing stack */
    const xmlChar *   *nameTab;       /* array of nodes */

    long               nbChars;       /* unused */
    long            checkIndex;       /* used by progressive parsing lookup */
    int             keepBlanks;       /* ugly but ... */
    int             disableSAX;       /* SAX callbacks are disabled */
    int               inSubset;       /* Parsing is in int 1/ext 2 subset */
    const xmlChar *    intSubName;    /* name of subset */
    xmlChar *          extSubURI;     /* URI of external subset */
    xmlChar *          extSubSystem;  /* SYSTEM ID of external subset */

    /* xml:space values */
    int *              space;         /* Should the parser preserve spaces */
    int                spaceNr;       /* Depth of the parsing stack */
    int                spaceMax;      /* Max depth of the parsing stack */
    int *              spaceTab;      /* array of space infos */

    int                depth;         /* to prevent entity substitution loops */
    xmlParserInputPtr  entity;        /* used to check entities boundaries */
    int                charset;       /* unused */
    int                nodelen;       /* Those two fields are there to */
    int                nodemem;       /* Speed up large node parsing */
    int                pedantic;      /* signal pedantic warnings */
    void              *_private;      /* For user data, libxml won't touch it */

    int                loadsubset;    /* should the external subset be loaded */
    int                linenumbers;   /* set line number in element content */
    void              *catalogs;      /* document's own catalog */
    int                recovery;      /* run in recovery mode */
    int                progressive;   /* is this a progressive parsing */
    xmlDictPtr         dict;          /* dictionary for the parser */
    const xmlChar *   *atts;          /* array for the attributes callbacks */
    int                maxatts;       /* the size of the array */
    int                docdict;       /* use strings from dict to build tree */

    /*
     * pre-interned strings
     */
    const xmlChar *str_xml;
    const xmlChar *str_xmlns;
    const xmlChar *str_xml_ns;

    /*
     * Everything below is used only by the new SAX mode
     */
    int                sax2;          /* operating in the new SAX mode */
    int                nsNr;          /* the number of inherited namespaces */
    int                nsMax;         /* the size of the arrays */
    const xmlChar *   *nsTab;         /* the array of prefix/namespace name */
    unsigned          *attallocs;     /* which attribute were allocated */
    xmlStartTag       *pushTab;       /* array of data for push */
    xmlHashTablePtr    attsDefault;   /* defaulted attributes if any */
    xmlHashTablePtr    attsSpecial;   /* non-CDATA attributes if any */
    int                nsWellFormed;  /* is the document XML Namespace okay */
    int                options;       /* Extra options */

    /*
     * Those fields are needed only for streaming parsing so far
     */
    int               dictNames;    /* Use dictionary names for the tree */
    int               freeElemsNr;  /* number of freed element nodes */
    xmlNodePtr        freeElems;    /* List of freed element nodes */
    int               freeAttrsNr;  /* number of freed attributes nodes */
    xmlAttrPtr        freeAttrs;    /* List of freed attributes nodes */

    /*
     * the complete error information for the last error.
     */
    xmlError          lastError;
    xmlParserMode     parseMode;    /* the parser mode */
    unsigned long    nbentities;    /* unused */
    unsigned long  sizeentities;    /* size of parsed entities */

    /* for use by HTML non-recursive parser */
    xmlParserNodeInfo *nodeInfo;      /* Current NodeInfo */
    int                nodeInfoNr;    /* Depth of the parsing stack */
    int                nodeInfoMax;   /* Max depth of the parsing stack */
    xmlParserNodeInfo *nodeInfoTab;   /* array of nodeInfos */

    int                input_id;      /* we need to label inputs */
    unsigned long      sizeentcopy;   /* volume of entity copy */

    int           endCheckState;    /* quote state for push parser */
    unsigned short     nbErrors;    /* number of errors */
    unsigned short   nbWarnings;    /* number of warnings */
    unsigned            maxAmpl;    /* maximum amplification factor */

    xmlParserNsData       *nsdb;    /* namespace database */
    unsigned        attrHashMax;    /* allocated size */
    xmlAttrHashBucket *attrHash;    /* atttribute hash table */
};

/**
 * xmlSAXLocator:
 *
 * A SAX Locator.
 */
struct _xmlSAXLocator {
    const xmlChar *(*getPublicId)(void *ctx);
    const xmlChar *(*getSystemId)(void *ctx);
    int (*getLineNumber)(void *ctx);
    int (*getColumnNumber)(void *ctx);
};

/**
 * xmlSAXHandler:
 *
 * A SAX handler is bunch of callbacks called by the parser when processing
 * of the input generate data or structure information.
 */

/**
 * resolveEntitySAXFunc:
 * @ctx:  the user data (XML parser context)
 * @publicId: The public ID of the entity
 * @systemId: The system ID of the entity
 *
 * Callback:
 * The entity loader, to control the loading of external entities,
 * the application can either:
 *    - override this resolveEntity() callback in the SAX block
 *    - or better use the xmlSetExternalEntityLoader() function to
 *      set up it's own entity resolution routine
 *
 * Returns the xmlParserInputPtr if inlined or NULL for DOM behaviour.
 */
typedef xmlParserInputPtr (*resolveEntitySAXFunc) (void *ctx,
				const xmlChar *publicId,
				const xmlChar *systemId);
/**
 * internalSubsetSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  the root element name
 * @ExternalID:  the external ID
 * @SystemID:  the SYSTEM ID (e.g. filename or URL)
 *
 * Callback on internal subset declaration.
 */
typedef void (*internalSubsetSAXFunc) (void *ctx,
				const xmlChar *name,
				const xmlChar *ExternalID,
				const xmlChar *SystemID);
/**
 * externalSubsetSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  the root element name
 * @ExternalID:  the external ID
 * @SystemID:  the SYSTEM ID (e.g. filename or URL)
 *
 * Callback on external subset declaration.
 */
typedef void (*externalSubsetSAXFunc) (void *ctx,
				const xmlChar *name,
				const xmlChar *ExternalID,
				const xmlChar *SystemID);
/**
 * getEntitySAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name: The entity name
 *
 * Get an entity by name.
 *
 * Returns the xmlEntityPtr if found.
 */
typedef xmlEntityPtr (*getEntitySAXFunc) (void *ctx,
				const xmlChar *name);
/**
 * getParameterEntitySAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name: The entity name
 *
 * Get a parameter entity by name.
 *
 * Returns the xmlEntityPtr if found.
 */
typedef xmlEntityPtr (*getParameterEntitySAXFunc) (void *ctx,
				const xmlChar *name);
/**
 * entityDeclSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  the entity name
 * @type:  the entity type
 * @publicId: The public ID of the entity
 * @systemId: The system ID of the entity
 * @content: the entity value (without processing).
 *
 * An entity definition has been parsed.
 */
typedef void (*entityDeclSAXFunc) (void *ctx,
				const xmlChar *name,
				int type,
				const xmlChar *publicId,
				const xmlChar *systemId,
				xmlChar *content);
/**
 * notationDeclSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name: The name of the notation
 * @publicId: The public ID of the entity
 * @systemId: The system ID of the entity
 *
 * What to do when a notation declaration has been parsed.
 */
typedef void (*notationDeclSAXFunc)(void *ctx,
				const xmlChar *name,
				const xmlChar *publicId,
				const xmlChar *systemId);
/**
 * attributeDeclSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @elem:  the name of the element
 * @fullname:  the attribute name
 * @type:  the attribute type
 * @def:  the type of default value
 * @defaultValue: the attribute default value
 * @tree:  the tree of enumerated value set
 *
 * An attribute definition has been parsed.
 */
typedef void (*attributeDeclSAXFunc)(void *ctx,
				const xmlChar *elem,
				const xmlChar *fullname,
				int type,
				int def,
				const xmlChar *defaultValue,
				xmlEnumerationPtr tree);
/**
 * elementDeclSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  the element name
 * @type:  the element type
 * @content: the element value tree
 *
 * An element definition has been parsed.
 */
typedef void (*elementDeclSAXFunc)(void *ctx,
				const xmlChar *name,
				int type,
				xmlElementContentPtr content);
/**
 * unparsedEntityDeclSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name: The name of the entity
 * @publicId: The public ID of the entity
 * @systemId: The system ID of the entity
 * @notationName: the name of the notation
 *
 * What to do when an unparsed entity declaration is parsed.
 */
typedef void (*unparsedEntityDeclSAXFunc)(void *ctx,
				const xmlChar *name,
				const xmlChar *publicId,
				const xmlChar *systemId,
				const xmlChar *notationName);
/**
 * setDocumentLocatorSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @loc: A SAX Locator
 *
 * Receive the document locator at startup, actually xmlDefaultSAXLocator.
 * Everything is available on the context, so this is useless in our case.
 */
typedef void (*setDocumentLocatorSAXFunc) (void *ctx,
				xmlSAXLocatorPtr loc);
/**
 * startDocumentSAXFunc:
 * @ctx:  the user data (XML parser context)
 *
 * Called when the document start being processed.
 */
typedef void (*startDocumentSAXFunc) (void *ctx);
/**
 * endDocumentSAXFunc:
 * @ctx:  the user data (XML parser context)
 *
 * Called when the document end has been detected.
 */
typedef void (*endDocumentSAXFunc) (void *ctx);
/**
 * startElementSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  The element name, including namespace prefix
 * @atts:  An array of name/value attributes pairs, NULL terminated
 *
 * Called when an opening tag has been processed.
 */
typedef void (*startElementSAXFunc) (void *ctx,
				const xmlChar *name,
				const xmlChar **atts);
/**
 * endElementSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  The element name
 *
 * Called when the end of an element has been detected.
 */
typedef void (*endElementSAXFunc) (void *ctx,
				const xmlChar *name);
/**
 * attributeSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  The attribute name, including namespace prefix
 * @value:  The attribute value
 *
 * Handle an attribute that has been read by the parser.
 * The default handling is to convert the attribute into an
 * DOM subtree and past it in a new xmlAttr element added to
 * the element.
 */
typedef void (*attributeSAXFunc) (void *ctx,
				const xmlChar *name,
				const xmlChar *value);
/**
 * referenceSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @name:  The entity name
 *
 * Called when an entity reference is detected.
 */
typedef void (*referenceSAXFunc) (void *ctx,
				const xmlChar *name);
/**
 * charactersSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @ch:  a xmlChar string
 * @len: the number of xmlChar
 *
 * Receiving some chars from the parser.
 */
typedef void (*charactersSAXFunc) (void *ctx,
				const xmlChar *ch,
				int len);
/**
 * ignorableWhitespaceSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @ch:  a xmlChar string
 * @len: the number of xmlChar
 *
 * Receiving some ignorable whitespaces from the parser.
 * UNUSED: by default the DOM building will use characters.
 */
typedef void (*ignorableWhitespaceSAXFunc) (void *ctx,
				const xmlChar *ch,
				int len);
/**
 * processingInstructionSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @target:  the target name
 * @data: the PI data's
 *
 * A processing instruction has been parsed.
 */
typedef void (*processingInstructionSAXFunc) (void *ctx,
				const xmlChar *target,
				const xmlChar *data);
/**
 * commentSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @value:  the comment content
 *
 * A comment has been parsed.
 */
typedef void (*commentSAXFunc) (void *ctx,
				const xmlChar *value);
/**
 * cdataBlockSAXFunc:
 * @ctx:  the user data (XML parser context)
 * @value:  The pcdata content
 * @len:  the block length
 *
 * Called when a pcdata block has been parsed.
 */
typedef void (*cdataBlockSAXFunc) (
	                        void *ctx,
				const xmlChar *value,
				int len);
/**
 * warningSAXFunc:
 * @ctx:  an XML parser context
 * @msg:  the message to display/transmit
 * @...:  extra parameters for the message display
 *
 * Display and format a warning messages, callback.
 */
typedef void (*warningSAXFunc) (void *ctx,
				const char *msg, ...) LIBXML_ATTR_FORMAT(2,3);
/**
 * errorSAXFunc:
 * @ctx:  an XML parser context
 * @msg:  the message to display/transmit
 * @...:  extra parameters for the message display
 *
 * Display and format an error messages, callback.
 */
typedef void (*errorSAXFunc) (void *ctx,
				const char *msg, ...) LIBXML_ATTR_FORMAT(2,3);
/**
 * fatalErrorSAXFunc:
 * @ctx:  an XML parser context
 * @msg:  the message to display/transmit
 * @...:  extra parameters for the message display
 *
 * Display and format fatal error messages, callback.
 * Note: so far fatalError() SAX callbacks are not used, error()
 *       get all the callbacks for errors.
 */
typedef void (*fatalErrorSAXFunc) (void *ctx,
				const char *msg, ...) LIBXML_ATTR_FORMAT(2,3);
/**
 * isStandaloneSAXFunc:
 * @ctx:  the user data (XML parser context)
 *
 * Is this document tagged standalone?
 *
 * Returns 1 if true
 */
typedef int (*isStandaloneSAXFunc) (void *ctx);
/**
 * hasInternalSubsetSAXFunc:
 * @ctx:  the user data (XML parser context)
 *
 * Does this document has an internal subset.
 *
 * Returns 1 if true
 */
typedef int (*hasInternalSubsetSAXFunc) (void *ctx);

/**
 * hasExternalSubsetSAXFunc:
 * @ctx:  the user data (XML parser context)
 *
 * Does this document has an external subset?
 *
 * Returns 1 if true
 */
typedef int (*hasExternalSubsetSAXFunc) (void *ctx);

/************************************************************************
 *									*
 *			The SAX version 2 API extensions		*
 *									*
 ************************************************************************/
/**
 * XML_SAX2_MAGIC:
 *
 * Special constant found in SAX2 blocks initialized fields
 */
#define XML_SAX2_MAGIC 0xDEEDBEAF

/**
 * startElementNsSAX2Func:
 * @ctx:  the user data (XML parser context)
 * @localname:  the local name of the element
 * @prefix:  the element namespace prefix if available
 * @URI:  the element namespace name if available
 * @nb_namespaces:  number of namespace definitions on that node
 * @namespaces:  pointer to the array of prefix/URI pairs namespace definitions
 * @nb_attributes:  the number of attributes on that node
 * @nb_defaulted:  the number of defaulted attributes. The defaulted
 *                  ones are at the end of the array
 * @attributes:  pointer to the array of (localname/prefix/URI/value/end)
 *               attribute values.
 *
 * SAX2 callback when an element start has been detected by the parser.
 * It provides the namespace information for the element, as well as
 * the new namespace declarations on the element.
 */

typedef void (*startElementNsSAX2Func) (void *ctx,
					const xmlChar *localname,
					const xmlChar *prefix,
					const xmlChar *URI,
					int nb_namespaces,
					const xmlChar **namespaces,
					int nb_attributes,
					int nb_defaulted,
					const xmlChar **attributes);

/**
 * endElementNsSAX2Func:
 * @ctx:  the user data (XML parser context)
 * @localname:  the local name of the element
 * @prefix:  the element namespace prefix if available
 * @URI:  the element namespace name if available
 *
 * SAX2 callback when an element end has been detected by the parser.
 * It provides the namespace information for the element.
 */

typedef void (*endElementNsSAX2Func)   (void *ctx,
					const xmlChar *localname,
					const xmlChar *prefix,
					const xmlChar *URI);


struct _xmlSAXHandler {
    internalSubsetSAXFunc internalSubset;
    isStandaloneSAXFunc isStandalone;
    hasInternalSubsetSAXFunc hasInternalSubset;
    hasExternalSubsetSAXFunc hasExternalSubset;
    resolveEntitySAXFunc resolveEntity;
    getEntitySAXFunc getEntity;
    entityDeclSAXFunc entityDecl;
    notationDeclSAXFunc notationDecl;
    attributeDeclSAXFunc attributeDecl;
    elementDeclSAXFunc elementDecl;
    unparsedEntityDeclSAXFunc unparsedEntityDecl;
    setDocumentLocatorSAXFunc setDocumentLocator;
    startDocumentSAXFunc startDocument;
    endDocumentSAXFunc endDocument;
    /*
     * `startElement` and `endElement` are only used by the legacy SAX1
     * interface and should not be used in new software. If you really
     * have to enable SAX1, the preferred way is set the `initialized`
     * member to 1 instead of XML_SAX2_MAGIC.
     *
     * For backward compatibility, it's also possible to set the
     * `startElementNs` and `endElementNs` handlers to NULL.
     *
     * You can also set the XML_PARSE_SAX1 parser option, but versions
     * older than 2.12.0 will probably crash if this option is provided
     * together with custom SAX callbacks.
     */
    startElementSAXFunc startElement;
    endElementSAXFunc endElement;
    referenceSAXFunc reference;
    charactersSAXFunc characters;
    ignorableWhitespaceSAXFunc ignorableWhitespace;
    processingInstructionSAXFunc processingInstruction;
    commentSAXFunc comment;
    warningSAXFunc warning;
    errorSAXFunc error;
    fatalErrorSAXFunc fatalError; /* unused error() get all the errors */
    getParameterEntitySAXFunc getParameterEntity;
    cdataBlockSAXFunc cdataBlock;
    externalSubsetSAXFunc externalSubset;
    /*
     * `initialized` should always be set to XML_SAX2_MAGIC to enable the
     * modern SAX2 interface.
     */
    unsigned int initialized;
    /*
     * The following members are only used by the SAX2 interface.
     */
    void *_private;
    startElementNsSAX2Func startElementNs;
    endElementNsSAX2Func endElementNs;
    xmlStructuredErrorFunc serror;
};

/*
 * SAX Version 1
 */
typedef struct _xmlSAXHandlerV1 xmlSAXHandlerV1;
typedef xmlSAXHandlerV1 *xmlSAXHandlerV1Ptr;
struct _xmlSAXHandlerV1 {
    internalSubsetSAXFunc internalSubset;
    isStandaloneSAXFunc isStandalone;
    hasInternalSubsetSAXFunc hasInternalSubset;
    hasExternalSubsetSAXFunc hasExternalSubset;
    resolveEntitySAXFunc resolveEntity;
    getEntitySAXFunc getEntity;
    entityDeclSAXFunc entityDecl;
    notationDeclSAXFunc notationDecl;
    attributeDeclSAXFunc attributeDecl;
    elementDeclSAXFunc elementDecl;
    unparsedEntityDeclSAXFunc unparsedEntityDecl;
    setDocumentLocatorSAXFunc setDocumentLocator;
    startDocumentSAXFunc startDocument;
    endDocumentSAXFunc endDocument;
    startElementSAXFunc startElement;
    endElementSAXFunc endElement;
    referenceSAXFunc reference;
    charactersSAXFunc characters;
    ignorableWhitespaceSAXFunc ignorableWhitespace;
    processingInstructionSAXFunc processingInstruction;
    commentSAXFunc comment;
    warningSAXFunc warning;
    errorSAXFunc error;
    fatalErrorSAXFunc fatalError; /* unused error() get all the errors */
    getParameterEntitySAXFunc getParameterEntity;
    cdataBlockSAXFunc cdataBlock;
    externalSubsetSAXFunc externalSubset;
    unsigned int initialized;
};


/**
 * xmlExternalEntityLoader:
 * @URL: The System ID of the resource requested
 * @ID: The Public ID of the resource requested
 * @context: the XML parser context
 *
 * External entity loaders types.
 *
 * Returns the entity input parser.
 */
typedef xmlParserInputPtr (*xmlExternalEntityLoader) (const char *URL,
					 const char *ID,
					 xmlParserCtxtPtr context);

/*
 * Variables
 */

XMLPUBVAR const char *const xmlParserVersion;
#ifdef LIBXML_THREAD_ENABLED
/* backward compatibility */
XMLPUBFUN const char *const *__xmlParserVersion(void);
#endif

/** DOC_DISABLE */
#define XML_GLOBALS_PARSER_CORE \
  XML_OP(oldXMLWDcompatibility, int, XML_DEPRECATED) \
  XML_OP(xmlDefaultSAXLocator, xmlSAXLocator, XML_DEPRECATED) \
  XML_OP(xmlDoValidityCheckingDefaultValue, int, XML_DEPRECATED) \
  XML_OP(xmlGetWarningsDefaultValue, int, XML_DEPRECATED) \
  XML_OP(xmlKeepBlanksDefaultValue, int, XML_DEPRECATED) \
  XML_OP(xmlLineNumbersDefaultValue, int, XML_DEPRECATED) \
  XML_OP(xmlLoadExtDtdDefaultValue, int, XML_DEPRECATED) \
  XML_OP(xmlParserDebugEntities, int, XML_DEPRECATED) \
  XML_OP(xmlPedanticParserDefaultValue, int, XML_DEPRECATED) \
  XML_OP(xmlSubstituteEntitiesDefaultValue, int, XML_DEPRECATED)

#ifdef LIBXML_OUTPUT_ENABLED
  #define XML_GLOBALS_PARSER_OUTPUT \
    XML_OP(xmlIndentTreeOutput, int, XML_NO_ATTR) \
    XML_OP(xmlTreeIndentString, const char *, XML_NO_ATTR) \
    XML_OP(xmlSaveNoEmptyTags, int, XML_NO_ATTR)
#else
  #define XML_GLOBALS_PARSER_OUTPUT
#endif

#ifdef LIBXML_SAX1_ENABLED
  #define XML_GLOBALS_PARSER_SAX1 \
    XML_OP(xmlDefaultSAXHandler, xmlSAXHandlerV1, XML_DEPRECATED)
#else
  #define XML_GLOBALS_PARSER_SAX1
#endif

#define XML_GLOBALS_PARSER \
  XML_GLOBALS_PARSER_CORE \
  XML_GLOBALS_PARSER_OUTPUT \
  XML_GLOBALS_PARSER_SAX1

#define XML_OP XML_DECLARE_GLOBAL
XML_GLOBALS_PARSER
#undef XML_OP

#if defined(LIBXML_THREAD_ENABLED) && !defined(XML_GLOBALS_NO_REDEFINITION)
  #define oldXMLWDcompatibility XML_GLOBAL_MACRO(oldXMLWDcompatibility)
  #define xmlDefaultSAXHandler XML_GLOBAL_MACRO(xmlDefaultSAXHandler)
  #define xmlDefaultSAXLocator XML_GLOBAL_MACRO(xmlDefaultSAXLocator)
  #define xmlDoValidityCheckingDefaultValue \
    XML_GLOBAL_MACRO(xmlDoValidityCheckingDefaultValue)
  #define xmlGetWarningsDefaultValue \
    XML_GLOBAL_MACRO(xmlGetWarningsDefaultValue)
  #define xmlKeepBlanksDefaultValue XML_GLOBAL_MACRO(xmlKeepBlanksDefaultValue)
  #define xmlLineNumbersDefaultValue \
    XML_GLOBAL_MACRO(xmlLineNumbersDefaultValue)
  #define xmlLoadExtDtdDefaultValue XML_GLOBAL_MACRO(xmlLoadExtDtdDefaultValue)
  #define xmlParserDebugEntities XML_GLOBAL_MACRO(xmlParserDebugEntities)
  #define xmlPedanticParserDefaultValue \
    XML_GLOBAL_MACRO(xmlPedanticParserDefaultValue)
  #define xmlSubstituteEntitiesDefaultValue \
    XML_GLOBAL_MACRO(xmlSubstituteEntitiesDefaultValue)
  #ifdef LIBXML_OUTPUT_ENABLED
    #define xmlIndentTreeOutput XML_GLOBAL_MACRO(xmlIndentTreeOutput)
    #define xmlTreeIndentString XML_GLOBAL_MACRO(xmlTreeIndentString)
    #define xmlSaveNoEmptyTags XML_GLOBAL_MACRO(xmlSaveNoEmptyTags)
  #endif
#endif
/** DOC_ENABLE */

/*
 * Init/Cleanup
 */
XMLPUBFUN void
		xmlInitParser		(void);
XMLPUBFUN void
		xmlCleanupParser	(void);
XML_DEPRECATED
XMLPUBFUN void
		xmlInitGlobals		(void);
XML_DEPRECATED
XMLPUBFUN void
		xmlCleanupGlobals	(void);

/*
 * Input functions
 */
XML_DEPRECATED
XMLPUBFUN int
		xmlParserInputRead	(xmlParserInputPtr in,
					 int len);
XML_DEPRECATED
XMLPUBFUN int
		xmlParserInputGrow	(xmlParserInputPtr in,
					 int len);

/*
 * Basic parsing Interfaces
 */
#ifdef LIBXML_SAX1_ENABLED
XMLPUBFUN xmlDocPtr
		xmlParseDoc		(const xmlChar *cur);
XMLPUBFUN xmlDocPtr
		xmlParseFile		(const char *filename);
XMLPUBFUN xmlDocPtr
		xmlParseMemory		(const char *buffer,
					 int size);
#endif /* LIBXML_SAX1_ENABLED */
XML_DEPRECATED XMLPUBFUN int
		xmlSubstituteEntitiesDefault(int val);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefSubstituteEntitiesDefaultValue(int v);
XML_DEPRECATED XMLPUBFUN int
		xmlKeepBlanksDefault	(int val);
XML_DEPRECATED XMLPUBFUN int
		xmlThrDefKeepBlanksDefaultValue(int v);
XMLPUBFUN void
		xmlStopParser		(xmlParserCtxtPtr ctxt);
XML_DEPRECATED XMLPUBFUN int
		xmlPedanticParserDefault(int val);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefPedanticParserDefaultValue(int v);
XML_DEPRECATED XMLPUBFUN int
		xmlLineNumbersDefault	(int val);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefLineNumbersDefaultValue(int v);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefDoValidityCheckingDefaultValue(int v);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefGetWarningsDefaultValue(int v);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefLoadExtDtdDefaultValue(int v);
XML_DEPRECATED XMLPUBFUN int
                xmlThrDefParserDebugEntities(int v);

#ifdef LIBXML_SAX1_ENABLED
/*
 * Recovery mode
 */
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlRecoverDoc		(const xmlChar *cur);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlRecoverMemory	(const char *buffer,
					 int size);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlRecoverFile		(const char *filename);
#endif /* LIBXML_SAX1_ENABLED */

/*
 * Less common routines and SAX interfaces
 */
XMLPUBFUN int
		xmlParseDocument	(xmlParserCtxtPtr ctxt);
XMLPUBFUN int
		xmlParseExtParsedEnt	(xmlParserCtxtPtr ctxt);
#ifdef LIBXML_SAX1_ENABLED
XML_DEPRECATED
XMLPUBFUN int
		xmlSAXUserParseFile	(xmlSAXHandlerPtr sax,
					 void *user_data,
					 const char *filename);
XML_DEPRECATED
XMLPUBFUN int
		xmlSAXUserParseMemory	(xmlSAXHandlerPtr sax,
					 void *user_data,
					 const char *buffer,
					 int size);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlSAXParseDoc		(xmlSAXHandlerPtr sax,
					 const xmlChar *cur,
					 int recovery);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlSAXParseMemory	(xmlSAXHandlerPtr sax,
					 const char *buffer,
					 int size,
					 int recovery);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlSAXParseMemoryWithData (xmlSAXHandlerPtr sax,
					 const char *buffer,
					 int size,
					 int recovery,
					 void *data);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlSAXParseFile		(xmlSAXHandlerPtr sax,
					 const char *filename,
					 int recovery);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlSAXParseFileWithData	(xmlSAXHandlerPtr sax,
					 const char *filename,
					 int recovery,
					 void *data);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlSAXParseEntity	(xmlSAXHandlerPtr sax,
					 const char *filename);
XML_DEPRECATED
XMLPUBFUN xmlDocPtr
		xmlParseEntity		(const char *filename);
#endif /* LIBXML_SAX1_ENABLED */

#ifdef LIBXML_VALID_ENABLED
XML_DEPRECATED
XMLPUBFUN xmlDtdPtr
		xmlSAXParseDTD		(xmlSAXHandlerPtr sax,
					 const xmlChar *ExternalID,
					 const xmlChar *SystemID);
XMLPUBFUN xmlDtdPtr
		xmlParseDTD		(const xmlChar *ExternalID,
					 const xmlChar *SystemID);
XMLPUBFUN xmlDtdPtr
		xmlIOParseDTD		(xmlSAXHandlerPtr sax,
					 xmlParserInputBufferPtr input,
					 xmlCharEncoding enc);
#endif /* LIBXML_VALID_ENABLE */
#ifdef LIBXML_SAX1_ENABLED
XMLPUBFUN int
		xmlParseBalancedChunkMemory(xmlDocPtr doc,
					 xmlSAXHandlerPtr sax,
					 void *user_data,
					 int depth,
					 const xmlChar *string,
					 xmlNodePtr *lst);
#endif /* LIBXML_SAX1_ENABLED */
XMLPUBFUN xmlParserErrors
		xmlParseInNodeContext	(xmlNodePtr node,
					 const char *data,
					 int datalen,
					 int options,
					 xmlNodePtr *lst);
#ifdef LIBXML_SAX1_ENABLED
XMLPUBFUN int
		xmlParseBalancedChunkMemoryRecover(xmlDocPtr doc,
                     xmlSAXHandlerPtr sax,
                     void *user_data,
                     int depth,
                     const xmlChar *string,
                     xmlNodePtr *lst,
                     int recover);
XML_DEPRECATED
XMLPUBFUN int
		xmlParseExternalEntity	(xmlDocPtr doc,
					 xmlSAXHandlerPtr sax,
					 void *user_data,
					 int depth,
					 const xmlChar *URL,
					 const xmlChar *ID,
					 xmlNodePtr *lst);
#endif /* LIBXML_SAX1_ENABLED */
XMLPUBFUN int
		xmlParseCtxtExternalEntity(xmlParserCtxtPtr ctx,
					 const xmlChar *URL,
					 const xmlChar *ID,
					 xmlNodePtr *lst);

/*
 * Parser contexts handling.
 */
XMLPUBFUN xmlParserCtxtPtr
		xmlNewParserCtxt	(void);
XMLPUBFUN xmlParserCtxtPtr
		xmlNewSAXParserCtxt	(const xmlSAXHandler *sax,
					 void *userData);
XMLPUBFUN int
		xmlInitParserCtxt	(xmlParserCtxtPtr ctxt);
XMLPUBFUN void
		xmlClearParserCtxt	(xmlParserCtxtPtr ctxt);
XMLPUBFUN void
		xmlFreeParserCtxt	(xmlParserCtxtPtr ctxt);
#ifdef LIBXML_SAX1_ENABLED
XML_DEPRECATED
XMLPUBFUN void
		xmlSetupParserForBuffer	(xmlParserCtxtPtr ctxt,
					 const xmlChar* buffer,
					 const char *filename);
#endif /* LIBXML_SAX1_ENABLED */
XMLPUBFUN xmlParserCtxtPtr
		xmlCreateDocParserCtxt	(const xmlChar *cur);

#ifdef LIBXML_LEGACY_ENABLED
/*
 * Reading/setting optional parsing features.
 */
XML_DEPRECATED
XMLPUBFUN int
		xmlGetFeaturesList	(int *len,
					 const char **result);
XML_DEPRECATED
XMLPUBFUN int
		xmlGetFeature		(xmlParserCtxtPtr ctxt,
					 const char *name,
					 void *result);
XML_DEPRECATED
XMLPUBFUN int
		xmlSetFeature		(xmlParserCtxtPtr ctxt,
					 const char *name,
					 void *value);
#endif /* LIBXML_LEGACY_ENABLED */

#ifdef LIBXML_PUSH_ENABLED
/*
 * Interfaces for the Push mode.
 */
XMLPUBFUN xmlParserCtxtPtr
		xmlCreatePushParserCtxt(xmlSAXHandlerPtr sax,
					 void *user_data,
					 const char *chunk,
					 int size,
					 const char *filename);
XMLPUBFUN int
		xmlParseChunk		(xmlParserCtxtPtr ctxt,
					 const char *chunk,
					 int size,
					 int terminate);
#endif /* LIBXML_PUSH_ENABLED */

/*
 * Special I/O mode.
 */

XMLPUBFUN xmlParserCtxtPtr
		xmlCreateIOParserCtxt	(xmlSAXHandlerPtr sax,
					 void *user_data,
					 xmlInputReadCallback   ioread,
					 xmlInputCloseCallback  ioclose,
					 void *ioctx,
					 xmlCharEncoding enc);

XMLPUBFUN xmlParserInputPtr
		xmlNewIOInputStream	(xmlParserCtxtPtr ctxt,
					 xmlParserInputBufferPtr input,
					 xmlCharEncoding enc);

/*
 * Node infos.
 */
XMLPUBFUN const xmlParserNodeInfo*
		xmlParserFindNodeInfo	(const xmlParserCtxtPtr ctxt,
				         const xmlNodePtr node);
XMLPUBFUN void
		xmlInitNodeInfoSeq	(xmlParserNodeInfoSeqPtr seq);
XMLPUBFUN void
		xmlClearNodeInfoSeq	(xmlParserNodeInfoSeqPtr seq);
XMLPUBFUN unsigned long
		xmlParserFindNodeInfoIndex(const xmlParserNodeInfoSeqPtr seq,
                                         const xmlNodePtr node);
XMLPUBFUN void
		xmlParserAddNodeInfo	(xmlParserCtxtPtr ctxt,
					 const xmlParserNodeInfoPtr info);

/*
 * External entities handling actually implemented in xmlIO.
 */

XMLPUBFUN void
		xmlSetExternalEntityLoader(xmlExternalEntityLoader f);
XMLPUBFUN xmlExternalEntityLoader
		xmlGetExternalEntityLoader(void);
XMLPUBFUN xmlParserInputPtr
		xmlLoadExternalEntity	(const char *URL,
					 const char *ID,
					 xmlParserCtxtPtr ctxt);

/*
 * Index lookup, actually implemented in the encoding module
 */
XMLPUBFUN long
		xmlByteConsumed		(xmlParserCtxtPtr ctxt);

/*
 * New set of simpler/more flexible APIs
 */
/**
 * xmlParserOption:
 *
 * This is the set of XML parser options that can be passed down
 * to the xmlReadDoc() and similar calls.
 */
typedef enum {
    XML_PARSE_RECOVER	= 1<<0,	/* recover on errors */
    XML_PARSE_NOENT	= 1<<1,	/* substitute entities */
    XML_PARSE_DTDLOAD	= 1<<2,	/* load the external subset */
    XML_PARSE_DTDATTR	= 1<<3,	/* default DTD attributes */
    XML_PARSE_DTDVALID	= 1<<4,	/* validate with the DTD */
    XML_PARSE_NOERROR	= 1<<5,	/* suppress error reports */
    XML_PARSE_NOWARNING	= 1<<6,	/* suppress warning reports */
    XML_PARSE_PEDANTIC	= 1<<7,	/* pedantic error reporting */
    XML_PARSE_NOBLANKS	= 1<<8,	/* remove blank nodes */
    XML_PARSE_SAX1	= 1<<9,	/* use the SAX1 interface internally */
    XML_PARSE_XINCLUDE	= 1<<10,/* Implement XInclude substitution  */
    XML_PARSE_NONET	= 1<<11,/* Forbid network access */
    XML_PARSE_NODICT	= 1<<12,/* Do not reuse the context dictionary */
    XML_PARSE_NSCLEAN	= 1<<13,/* remove redundant namespaces declarations */
    XML_PARSE_NOCDATA	= 1<<14,/* merge CDATA as text nodes */
    XML_PARSE_NOXINCNODE= 1<<15,/* do not generate XINCLUDE START/END nodes */
    XML_PARSE_COMPACT   = 1<<16,/* compact small text nodes; no modification of
                                   the tree allowed afterwards (will possibly
				   crash if you try to modify the tree) */
    XML_PARSE_OLD10	= 1<<17,/* parse using XML-1.0 before update 5 */
    XML_PARSE_NOBASEFIX = 1<<18,/* do not fixup XINCLUDE xml:base uris */
    XML_PARSE_HUGE      = 1<<19,/* relax any hardcoded limit from the parser */
    XML_PARSE_OLDSAX    = 1<<20,/* parse using SAX2 interface before 2.7.0 */
    XML_PARSE_IGNORE_ENC= 1<<21,/* ignore internal document encoding hint */
    XML_PARSE_BIG_LINES = 1<<22 /* Store big lines numbers in text PSVI field */
} xmlParserOption;

XMLPUBFUN void
		xmlCtxtReset		(xmlParserCtxtPtr ctxt);
XMLPUBFUN int
		xmlCtxtResetPush	(xmlParserCtxtPtr ctxt,
					 const char *chunk,
					 int size,
					 const char *filename,
					 const char *encoding);
XMLPUBFUN int
		xmlCtxtUseOptions	(xmlParserCtxtPtr ctxt,
					 int options);
XMLPUBFUN void
		xmlCtxtSetMaxAmplification(xmlParserCtxtPtr ctxt,
					 unsigned maxAmpl);
XMLPUBFUN xmlDocPtr
		xmlReadDoc		(const xmlChar *cur,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlReadFile		(const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlReadMemory		(const char *buffer,
					 int size,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlReadFd		(int fd,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlReadIO		(xmlInputReadCallback ioread,
					 xmlInputCloseCallback ioclose,
					 void *ioctx,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlCtxtReadDoc		(xmlParserCtxtPtr ctxt,
					 const xmlChar *cur,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlCtxtReadFile		(xmlParserCtxtPtr ctxt,
					 const char *filename,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlCtxtReadMemory		(xmlParserCtxtPtr ctxt,
					 const char *buffer,
					 int size,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlCtxtReadFd		(xmlParserCtxtPtr ctxt,
					 int fd,
					 const char *URL,
					 const char *encoding,
					 int options);
XMLPUBFUN xmlDocPtr
		xmlCtxtReadIO		(xmlParserCtxtPtr ctxt,
					 xmlInputReadCallback ioread,
					 xmlInputCloseCallback ioclose,
					 void *ioctx,
					 const char *URL,
					 const char *encoding,
					 int options);

/*
 * Library wide options
 */
/**
 * xmlFeature:
 *
 * Used to examine the existence of features that can be enabled
 * or disabled at compile-time.
 * They used to be called XML_FEATURE_xxx but this clashed with Expat
 */
typedef enum {
    XML_WITH_THREAD = 1,
    XML_WITH_TREE = 2,
    XML_WITH_OUTPUT = 3,
    XML_WITH_PUSH = 4,
    XML_WITH_READER = 5,
    XML_WITH_PATTERN = 6,
    XML_WITH_WRITER = 7,
    XML_WITH_SAX1 = 8,
    XML_WITH_FTP = 9,
    XML_WITH_HTTP = 10,
    XML_WITH_VALID = 11,
    XML_WITH_HTML = 12,
    XML_WITH_LEGACY = 13,
    XML_WITH_C14N = 14,
    XML_WITH_CATALOG = 15,
    XML_WITH_XPATH = 16,
    XML_WITH_XPTR = 17,
    XML_WITH_XINCLUDE = 18,
    XML_WITH_ICONV = 19,
    XML_WITH_ISO8859X = 20,
    XML_WITH_UNICODE = 21,
    XML_WITH_REGEXP = 22,
    XML_WITH_AUTOMATA = 23,
    XML_WITH_EXPR = 24,
    XML_WITH_SCHEMAS = 25,
    XML_WITH_SCHEMATRON = 26,
    XML_WITH_MODULES = 27,
    XML_WITH_DEBUG = 28,
    XML_WITH_DEBUG_MEM = 29,
    XML_WITH_DEBUG_RUN = 30,
    XML_WITH_ZLIB = 31,
    XML_WITH_ICU = 32,
    XML_WITH_LZMA = 33,
    XML_WITH_NONE = 99999 /* just to be sure of allocation size */
} xmlFeature;

XMLPUBFUN int
		xmlHasFeature		(xmlFeature feature);

#ifdef __cplusplus
}
#endif
#endif /* __XML_PARSER_H__ */
