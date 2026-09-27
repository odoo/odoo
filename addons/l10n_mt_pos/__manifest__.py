# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Malta - Point of Sale",
    "category": "Accounting/Localizations/Point of Sale",
    "description": """Malta Compliance Letter for EXO Number""",
    "countries": ["mt"],
    "depends": [
        "point_of_sale",
    ],
    "data": [
        'wizards/compliance_letter_view.xml',
        'reports/compliance_letter_report.xml',
        'security/ir.access.csv',
    ],
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
