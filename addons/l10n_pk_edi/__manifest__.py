# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Pakistan - E-invoicing",
    'version': '1.0',
    'countries': ['pk'],
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_pk',
        'account_debit_note',
    ],
    'description': """
Pakistan - E-invoicing
======================
To submit invoicing through API to the government.

Step 1: First you need to create an API Token in the E-invoice portal.
Step 2: Switch to company related to that Token
Step 3: Set that Token in Odoo (Goto: Invoicing/Accounting -> Configuration -> Settings -> Customer Invoices or find "E-invoice" in search bar)
Step 4: Repeat steps 1,2,3 for all Token you have in odoo.
    """,
    'data': [
        'data/uom_data.xml',
        'views/report_templates.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/uom_uom_views.xml',
        'views/product_views.xml',
        'views/account_move_views.xml',
        'wizard/account_debit_note_view.xml',
        'wizard/account_move_reversal_view.xml',
        'wizard/account_move_send_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
