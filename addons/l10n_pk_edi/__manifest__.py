# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Pakistan - E-invoicing""",
    "version": "1.0",
    'countries': ['pk'],
    "category": "Accounting/Localizations/EDI",
    "depends": ["l10n_pk"],
    "description": """
Pakistan - E-invoicing
======================
To submit invoicing through API to the government.

Step 1: First you need to create an API Token in the E-invoice portal.
Step 2: Switch to company related to that Token
Step 3: Set that Token in Odoo (Goto: Invoicing/Accounting -> Configuration -> Settings -> Customer Invoices or find "E-invoice" in search bar)
Step 4: Repeat steps 1,2,3 for all Token you have in odoo.
    """,
    "data": [
        "security/ir.model.access.csv",
        "data/uom_data.xml",
        "data/l10n_pk_edi_sale_type.xml",
        "data/l10n_pk_edi_schedule_code.xml",
        "views/res_config_settings_views.xml",
        "views/uom_uom_views.xml",
        "views/product_views.xml",
        "views/account_move_views.xml",
        'wizard/account_move_send_views.xml',
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
