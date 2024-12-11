{
    'name': 'Cyprus - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['cy'],
    'description': """
Basic package for Cyprus that contains the chart of accounts, taxes, tax reports,...
    """,
    'license': 'LGPL-3',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'data/menuitem_data.xml',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
