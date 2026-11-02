# -*- coding: utf-8 -*-
{
    "name": "Purchase Revision (OD19)",
    "version": "19.0.1.0.0",
    "summary": "ISO-style revision control for Purchase Orders "
    "(create /R00, /R01, ... revisions)",
    "description": """
Adds document revision control to Purchase Orders.

A confirmed purchase order can be revised by creating a new document that is
linked to the previous one. The new document keeps the same base reference
with a revision suffix (``/R00``, ``/R01``, ...) while the previous document is
locked as read-only.
    """,
    "author": "OD19 Custom",
    "website": "https://www.trae.ai",
    "category": "Purchases",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "od19_purchase_procurement_core",
    ],
    "data": [
        "security/purchase_revision_security.xml",
        "views/purchase_order_views.xml",
        "views/purchase_order_report.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_purchase_revision/static/description/icon.svg",
}
