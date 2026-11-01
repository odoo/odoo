# -*- coding: utf-8 -*-
{
    "name": "Partner Document Sequence (OD19)",
    "version": "19.0.1.0.0",
    "summary": "Customer (C) and Vendor (V) reference numbering",
    "description": """
Auto-generates partner reference codes:
- Customer: C#### (e.g. C0001)
- Vendor: V#### (e.g. V0001)
    """,
    "author": "OD19 Custom",
    "category": "Sales/CRM",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_partner_document_sequence/static/description/icon.svg",
}
