# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Document Page Reference",
    "summary": """
        Include references on document pages""",
    "version": "19.0.2.1.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/knowledge",
    "depends": ["document_page"],
    "data": [
        "views/document_page.xml",
        "views/report_document_page.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "document_page_reference/static/src/js/editor.esm.js",
        ],
    },
    "maintainers": ["etobella"],
}

