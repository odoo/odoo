# -*- encoding: utf-8 -*-
# Author: Odoo House ApS <info@odoohouse.dk> 

# Copyright (c) 2018 - Present | Odoo House ApS - https://odoohouse.dk
# All rights reserved.

{
    'name': 'Denmark - Accounting Reports',
    'version': '2.2',
    'author': 'Odoo House ApS',
    'website': 'https://odoohouse.dk',
    'category': 'Localization',
    'description': """
Accounting reports for Denmark
=================================
    """,
    'depends': ['l10n_dk', 'account_reports','account_accountant'],
    'data': [
        'data/res_config_data.xml',
        'data/account_income_statement_html_report_data.xml',
        'data/account_balance_dk_html_report_data.xml'
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'license': 'OEEL-1',
}