{
    'name': 'North Macedonia - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mk'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
    Chart Of Account and Taxes for North Macedonia.
    """,
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
    ],
    'data': [
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
