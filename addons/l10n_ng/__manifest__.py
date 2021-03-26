# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nigeria - Accounting',
    'category': 'Account Charts',
    'description': """
This is the base module to manage the accounting chart for Nigeria.
==============================================================================

* Chart of Accounts.
* VAT and Withholding Taxes

    """,
    'author': 'erpSOFTapp',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'account_accountant',
                'base'

    ],
    'data': [
        'data/l10n_ng_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.group.csv',
        'data/account_tax_data.xml',
        'data/res.country.state.csv',
        'data/account_chart_template_data.xml'
    ],
    'test': [

    ],
    'demo': [

    ],
    'installable': True,
    'website': 'https://www.erpsoftapp.com',
}
