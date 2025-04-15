# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Austria - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['at'],
    'version': '3.2.1',
    'author': 'WT-IO-IT GmbH, Wolfgang Taferner (https://www.wt-io-it.at)',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'summary': 'Austrian Standardized Charts & Tax',
    'description': """

Austrian charts of accounts (Einheitskontenrahmen 2010).
==========================================================

    * Defines the following chart of account templates:
        * Austrian General Chart of accounts 2010
    * Defines templates for VAT on sales and purchases
    * Defines tax templates
    * Defines fiscal positions for Austrian fiscal legislation
    * Defines tax reports U1/U30

    """,
    'depends': [
        'account',
        'base_iban',
        'base_vat',
        'l10n_din5008',
    ],
    'data': [
        'data/res.country.state.csv',
        'data/account_account_tag.xml',
        'data/account.account.tag.csv',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
