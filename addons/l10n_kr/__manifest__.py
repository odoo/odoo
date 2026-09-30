{
    'name': "Republic of Korea - Accounting",
    'icon': '/account/static/description/l10n.png',
    'countries': ['kr'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Accounting Module for the Republic of Korea
===========================================
This provides a base chart of accounts and taxes template for use in Odoo.
    """,
    'depends': ['account'],
    'auto_install': ['account'],
    'data': [
        'data/res_country_data.xml',
        'data/general_tax_report.xml',
        'data/simplified_tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
