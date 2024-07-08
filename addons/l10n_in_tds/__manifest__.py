# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indian TDS',
    'version': '1.0',
    'description': """
Indian TDS
==================
This module provides TDS (Tax Deducted at Source) for India.
    """,
    'category': 'Accounting/Localizations',
    'depends': ['l10n_in'],
    'data': [
        'data/account_tax_report_tds_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
