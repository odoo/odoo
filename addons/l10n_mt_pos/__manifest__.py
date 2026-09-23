{
    "name": "Malta - Point of Sale",
    "version": "1.0",
    "category": "Accounting/Localizations/Point of Sale",
    "description": "Malta Compliance Letter for EXO Number",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "countries": [
        "mt",
    ],
    "data": [
        "security/ir.access.csv",
        "wizards/compliance_letter_view.xml",
        "reports/compliance_letter_report.xml",
        "views/l10n_mt_pos_menus.xml",
    ],
    "auto_install": True,
}
