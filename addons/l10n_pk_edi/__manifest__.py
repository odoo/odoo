# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': """Pakistan - E-invoicing""",
    'version': "1.0",
    'countries': ['pk'],
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'point_of_sale',
        'l10n_pk'
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
        'data/res_partner.xml',
        'views/account_move_views.xml',
        'views/product_template_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_pk_edi/static/src/**/*',
        ],
    },
    'installable': True,
    'license': "LGPL-3",
}
