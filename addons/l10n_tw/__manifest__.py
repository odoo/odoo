# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Taiwan - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['tw'],
    'author': 'Odoo PS',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Taiwan in Odoo.
==============================================================================
    """,
    'depends': [
        'account',
        'base_address_extended',
    ],
    'auto_install': ['account'],
    'data': [
        'data/res_currency_data.xml',
        'data/res_country_data.xml',
        'data/res.city.csv',
        'data/tax_report_401.xml',
        'data/tax_report_403.xml',
        'data/tax_report_404.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
