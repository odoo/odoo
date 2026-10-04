# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Laos - Accounting',
    'summary': 'Chart of accounts, VAT taxes and monthly VAT return for Laos',
    'icon': '/account/static/description/l10n.png',
    'countries': ['la'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Chart of Accounts for Laos.
===========================

Chart of accounts for non-public-interest entities, as set by the Ministry of Finance
Decision No. 0369 of 4 February 2020.
    """,
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
        'l10n_account_withholding_tax',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
