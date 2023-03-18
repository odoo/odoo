# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Kuwait - Accounting',
    'author': 'Walnut Software Solutions',
    'category': 'Accounting/Localizations/Account Charts',
    'summary': """Kuwait accounting chart and localization""",
    'description': """
Kuwait accounting chart and localization.
=========================================
    """,
    'depends': ['base', 'account'],
    'data': [
        'data/l10n_kw_chart_data.xml',
        'data/account.account.template.csv',
        'data/res.bank.csv',
        'data/l10n_kw_chart_post_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'website': 'https://www.walnutit.com',
    'license': 'LGPL-3',
}
