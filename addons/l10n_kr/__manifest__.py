{
    'name': "Korea - Accounting",
    'icon': '/account/static/description/l10n.png',
    'countries': ['kr'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Korean Accounting Module
========================
This provides a base chart of accounts and taxes template for use in Odoo.
    """,
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/res_country_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
