# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Uruguay - Accounting',
    'version': '0.1',
    'author': 'Uruguay l10n Team, Guillem Barba',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
General Chart of Accounts.
==========================

Provide Templates for Chart of Accounts, Taxes for Uruguay.

""",
    'depends': ['account'],
    'data': [
        'data/l10n_uy_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_uy_chart_post_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
