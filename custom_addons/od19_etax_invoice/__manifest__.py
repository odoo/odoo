# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 e-Tax Invoice & e-Receipt",
    "version": "19.0.1.2.3",
    "author": "OD19",
    "category": "Accounting/Localizations",
    "summary": "Thai e-Tax Invoice & e-Receipt (ขมธอ.3-2560) XML with XAdES digital signature",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "od19_partner_thai_fields",
        "od19_accounting_dncn",
    ],
    "external_dependencies": {
        "python": [
            "lxml",
            "signxml",
            "cryptography",
            "pikepdf",
            "qrcode",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/etax_certificate_views.xml",
        "views/etax_document_views.xml",
        "views/etax_submission_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
        "report/etax_document_report.xml",
    ],
    "installable": True,
    "application": True,
    "icon": "/od19_etax_invoice/static/description/icon.svg",
}
