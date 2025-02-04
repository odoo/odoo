# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Jordan - Accounting',
    'countries': ['jo'],
    'description': """
This is the base module to manage the accounting chart for Jordan in Odoo.
==============================================================================

Jordan accounting basic charts and localization.

Activates:

- Chart of accounts

- Taxes

- Tax report

- Fiscal positions
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
