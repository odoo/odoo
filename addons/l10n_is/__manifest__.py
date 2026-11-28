# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Iceland - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['is'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Accounting localization for Iceland
===================================

* Chart of accounts following Icelandic practice (revenue 1xxx, expenses 2xxx,
  assets 3xxx, liabilities 4xxx, equity 5xxx), split by VAT rate as required by Skatturinn
* VAT 24% and 11%, zero-rated (Art. 12) and exempt (Art. 2) taxes, import VAT paid at customs
* Fiscal positions: domestic, foreign business, foreign consumer, export of goods
* VAT return (RSK 10.01)
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
