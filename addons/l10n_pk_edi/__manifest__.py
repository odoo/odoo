{
    'name': "Pakistan - E-invoicing",
    'author': 'Odoo S.A.',
    'countries': ['pk'],
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'account_debit_note',
        'iap',
        'l10n_pk',
        'stock_delivery',
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
        'security/ir.access.csv',
        'data/uom.uom.csv',
        'data/ir_config_data.xml',
        'data/l10n_pk_edi_sro_data.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/l10n_pk_edi_sro.xml',
        'views/l10n_pk_edi_sro_item.xml',
        'views/l10n_pk_edi_test_log.xml',
        'views/l10n_pk_edi_menus.xml',
        'views/product_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/uom_uom_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_pk_edi/static/src/webclient/**/*',
        ],
    },
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
