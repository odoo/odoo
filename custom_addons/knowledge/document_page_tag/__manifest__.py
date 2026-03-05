# Copyright 2015-2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Document Page Tag",
    "version": "19.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/knowledge",
    "license": "AGPL-3",
    "category": "Knowledge Management",
    "summary": "Allows you to assign tags or keywords to pages and search for "
    "them afterwards",
    "depends": ["document_page"],
    "data": [
        "views/document_page_tag.xml",
        "views/document_page.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}

