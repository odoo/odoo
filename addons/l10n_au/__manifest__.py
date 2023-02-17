# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Australian - Accounting',
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Australian Accounting Module
============================

Australian accounting basic charts and localizations.

Also:
    - activates a number of regional currencies.
    - sets up Australian taxes.
    """,
    'author': 'Richard deMeester - Willow IT',
    'website': 'http://www.willowit.com',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/res_currency_data.xml',
        'views/menuitems.xml',
        'views/report_invoice.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
