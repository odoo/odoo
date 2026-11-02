# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Billing Request (คำขอเปิดบิลกลาง)",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Unified AR/AP billing request from IN/OUT/SO/PO",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "purchase",
        "stock",
        "account",
        "hr",
        "od19_sales_billing_evidence",
        "od19_document_pull",
    ],
    "data": [
        "security/od19_billing_request_security.xml",
        "security/ir.model.access.csv",
        "data/od19_billing_request_data.xml",
        "views/billing_request_views.xml",
        "views/billing_request_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
