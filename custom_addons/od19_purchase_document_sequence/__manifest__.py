# -*- coding: utf-8 -*-
{
    "name": "Purchase Document Sequence (OD19)",
    "version": "19.0.1.0.0",
    "summary": "ISO document numbering per department for Purchase Request and Purchase Order",
    "description": """
Adds department-based document sequences for purchase documents.
Each department can have its own Purchase Request and Purchase Order sequence
(prefixes like PRI, PRB, PB, PT, IT, IB, II, ...).
    """,
    "author": "OD19 Custom",
    "category": "Purchases",
    "license": "LGPL-3",
    "depends": [
        "purchase_request",
        "purchase",
        "hr",
        "od19_purchase_request_extend",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "views/hr_department_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_purchase_document_sequence/static/description/icon.svg",
}
