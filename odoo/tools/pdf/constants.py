class TrailerKeys:
    """
    Constants representing standard keys used in the PDF Trailer dictionary.

    These keys are defined in **ISO 32000-1 (Section 7.5.5)** and are used
    to locate critical parts of the document structure.
    """
    ROOT = "/Root"  # Points to the Document Catalog (root of the object graph)
    ENCRYPT = "/Encrypt"  # Points to the Encryption Dictionary (if protected)
    ID = "/ID"  # An array of two byte-strings forming the unique file identifier
    INFO = "/Info"  # Points to the Information Dictionary (Metadata: Author, Title...)
    SIZE = "/Size"  # Total number of objects in the document's XRef table
    PREV = "/Prev"  # Byte offset to the previous XRef table (essential for incremental updates)

class Resources:
    """TABLE 3.30 Entries in a resource dictionary."""

    EXT_G_STATE = "/ExtGState"  # dictionary, optional
    COLOR_SPACE = "/ColorSpace"  # dictionary, optional
    PATTERN = "/Pattern"  # dictionary, optional
    SHADING = "/Shading"  # dictionary, optional
    XOBJECT = "/XObject"  # dictionary, optional
    FONT = "/Font"  # dictionary, optional
    PROC_SET = "/ProcSet"  # array, optional
    PROPERTIES = "/Properties"  # dictionary, optional

class PageAttributes:
    """TABLE 3.27 Entries in a page object."""

    TYPE = "/Type"  # name, required; must be /Page
    RESOURCES = "/Resources"  # dictionary, required if there are any
    CONTENTS = "/Contents"  # stream or array, optional
    ANNOTS = "/Annots"  # array, optional; an array of annotations
    ID = "/ID"  # byte string, optional

class CatalogDictionary:
    """§7.7.2 of the 1.7 and 2.0 references."""

    Fields = "/Fields"
    ACRO_FORM = "/AcroForm"  # dictionary, optional

class InteractiveFormDictEntries:
    SigFlags = "/SigFlags"
