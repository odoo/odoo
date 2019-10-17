# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Saudi Arabia - Accounting',
    'version': '1.1',
    'author': 'DVIT.ME',
    'category': 'Localization/Account Charts',
    'description': """
Odoo Arabic localization for most arabic countries and Saudi Arabia.

This initially includes chart of accounts of USA translated to Arabic.

In future this module will include some payroll rules for ME .
""",
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account', 'l10n_multilang'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/l10n_sa_chart_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
    'post_init_hook': 'load_translations',
}
