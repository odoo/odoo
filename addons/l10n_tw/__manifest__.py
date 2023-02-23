# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Taiwan - Accounting',
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
    'data': [
        'data/res.country.state.csv',
        'data/res_currency_data.xml',
        'data/res_country_data.xml',
        'data/res.city.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'icon': '/base/static/img/country_flags/tw.png',
    'license': 'LGPL-3',
}
