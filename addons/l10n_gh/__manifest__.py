# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ghana - Accounting',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Ghana.
==============================================================================

* Chart of Accounts.

    """,
    'author': 'erpSOFTapp',
    'website': 'https://www.erpsoftapp.com',
    'depends': [
        'account',
    ],

    'data': [
        'data/l10n_gh_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.group.csv',
        'data/account_tax_data.xml',
        'data/res.country.state.csv',
        'data/account_chart_template_data.xml',
    ],

    'installable': True
}
