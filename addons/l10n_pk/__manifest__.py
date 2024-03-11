# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pakistan - Accounting',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """ This is the base module to manage chart of accounts and localization for the Pakistan """,
    'depends': ['account'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/l10n_pk_chart_data.xml',
        'data/account.group.template.csv',
        'data/account_tax_group.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml'
    ],
    'license': 'LGPL-3',
}
