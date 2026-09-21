{
    "name": "Documents - Speech",
    "version": "19.0.1.1.0",
    "category": "Hidden",
    "summary": "Transcribe a stored recording, and file spoken text as a document",
    "description": """
Documents - Speech
==================

The bridge is small because the interesting half needs no code. A document's
``index_content`` is related from its attachment, and a transcript IS that
attachment's index content, so a recording becomes findable by what is said in
it through the search field Documents already had. Nothing here indexes
anything.

What is left is the two actions a person needs: transcribe this recording, and
file this text as audio.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "document",
        "speech",
    ],
    "data": [
        "views/document_document_views.xml",
    ],
    "auto_install": True,
}
