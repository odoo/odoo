{
    'name': "Pakistan - E-invoicing",
    'version': '1.0',
    'countries': ['pk'],
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'iap',
        'l10n_pk',
    ],
    'summary': "Electronic Invoicing for Pakistan FBR(v1.12)",
    'description': """
Pakistan - E-invoicing
======================
To submit invoices through API to the Pakistan government,
Step 1: Generate an API token from the Pakistan E-Invoice portal.
Step 2: Switch to the company associated with that API token in Odoo.
Step 3: Configure the token in Odoo:
    Go to Invoicing/Accounting → Configuration → Settings, then search for “Pakistan Electronic Invoicing” and paste the token.
Step 4: Create a customer invoice and use Send & Print to submit it to the Pakistan E-Invoicing system.
    """,
    'data': [
        'views/account_move_views.xml',
        'views/product_views.xml',
        'views/report_invoice.xml',
        'views/report_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
