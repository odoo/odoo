# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Egypt - Accounting',
    'description': """
This is the base module to manage the accounting chart for Egypt in Odoo.
==============================================================================
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
        'views/account_tax.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
    'license': 'LGPL-3',
}
