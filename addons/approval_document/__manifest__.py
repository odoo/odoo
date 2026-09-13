{
    "name": "Document Access Requests",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Ask for access to a document or folder through the approval engine",
    "description": """
Document Access Requests
========================

A user holding a link to a document or folder they cannot open asks to view or
to edit it. The request goes to the document's owner, and a documents
administrator may decide it too. Approving it shares the document with the
user, the way the share dialog would, so the access propagates to what the
folder holds.

A bridge rather than a dependency of ``document``, so a database without the
approval engine keeps sharing by hand and installs nothing more.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "approval",
        "document",
    ],
    "data": [
        "data/approval_category_data.xml",
        "views/document_templates.xml",
    ],
    "auto_install": True,
}
