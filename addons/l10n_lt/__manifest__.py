# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Lithuania - Accounting',
    'version': '1.0.0',
    'description': """
        Chart of Accounts (COA) Template for Lithuania's Accounting.

        This module also includes:

        * List of available banks in Lithuania.
        * Tax groups.
        * Most common Lithuanian Taxes.
        * Fiscal positions.
        * Account Tags.
    """,
    'license': 'LGPL-3',
    'author': 'Focusate',
    'website': 'http://www.focusate.eu',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_account_tag_data.xml',
        'data/res_bank_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
}
