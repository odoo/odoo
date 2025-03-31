# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Check Printing Base',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Check printing basic features',
    'description': """
This module offers the basic functionalities to make payments by printing checks.
It must be used as a dependency for modules that provide country-specific check templates.
The check settings are located in the accounting journals configuration page.
    """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_check_printing_data.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/print_prenumbered_checks_views.xml'
    ],
    'installable': True,
    'post_init_hook': 'create_check_sequence_on_bank_journals',
    'license': 'LGPL-3',
}
