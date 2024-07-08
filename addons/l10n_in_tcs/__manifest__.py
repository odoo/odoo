# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indian TCS',
    'version': '1.0',
    'description': """
Indian TCS
==================
This module provides TCS (Tax Collected at Source) for India.
    """,
    'category': 'Accounting/Localizations',
    'depends': ['l10n_in'],
    'data': [
        'data/account_tax_report_tcs_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
