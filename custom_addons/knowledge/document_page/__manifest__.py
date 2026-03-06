# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    "name": "Document Page",
    "version": "19.0.2.1.0",
    "category": "Knowledge Management",
    "author": "OpenERP SA, Odoo Community Association (OCA)",
    "images": [
        "images/category_list.png",
        "images/create_category.png",
        "images/page_list.png",
        "images/create_page.png",
        "images/customer_invoice.jpeg",
        "images/page_history.png",
    ],
    "website": "https://github.com/OCA/knowledge",
    "license": "AGPL-3",
    "depends": ["mail", "document_knowledge", "html_editor"],
    "data": [
        "security/document_page_security.xml",
        "security/ir.model.access.csv",
        "wizard/document_page_create_menu.xml",
        "wizard/document_page_show_diff.xml",
        "views/document_page.xml",
        "views/document_page_category.xml",
        "views/document_page_history.xml",
        "views/report_document_page.xml",
    ],
    "demo": ["demo/document_page.xml"],
    "assets": {
        "web._assets_primary_variables": [
            "document_page/static/src/**/document_page_variables.scss",
        ],
        "web.assets_backend": [
            "document_page/static/src/scss/document_page.scss",
            "document_page/static/src/js/document_page_kanban_controller.esm.js",
            "document_page/static/src/js/document_page_kanban_view.esm.js",
        ],
    },
}

