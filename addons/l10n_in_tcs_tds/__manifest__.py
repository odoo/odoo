# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Indian - TCS/TDS Accounting Report and Taxes",
    'version': '1.0',
    'description': """
Tax Report TCS/TDS for India
====================================

This module adds TCS and TDS Tax Report and load related Taxes in Indian Company.
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_in'],
    'data': [
        'data/account_tax_group_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_report_tcs_data.xml',
        'data/account_tax_template_tcs_data.xml',
        'data/account_tax_report_tds_data.xml',
        'data/account_tax_template_tds_data.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'l10n_in_post_init',
    'license': 'LGPL-3',
}
