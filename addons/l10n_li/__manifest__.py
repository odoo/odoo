# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Liechtenstein - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['li'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Liechtenstein localization
==========================
Chart of accounts based on the Swiss SME chart (KMU), VAT taxes and the VAT return
for Liechtenstein.
    """,
    'depends': [
        'account',
        'l10n_din5008',
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
