{
    'name': 'Albania - Accounting',
    'summary': 'Chart of accounts, VAT taxes and monthly VAT return for Albania',
    'icon': '/account/static/description/l10n.png',
    'countries': ['al'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Accounting localization for Albania.
====================================

General chart of accounts (Plani Kontabël i Përgjithshëm), VAT taxes under Law No. 92/2014 on Value Added Tax,
fiscal positions and the monthly VAT return (DTVSH).
    """,
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
