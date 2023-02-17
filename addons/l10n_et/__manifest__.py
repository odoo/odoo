# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ethiopia - Accounting',
    'version': '2.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Base Module for Ethiopian Localization
======================================

This is the latest Ethiopian Odoo localization and consists of:
    - Chart of Accounts
    - VAT tax structure
    - Withholding tax structure
    - Regional State listings
    """,
    'author': 'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website': 'http://miketelahun.wordpress.com',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
