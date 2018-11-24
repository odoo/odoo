# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - Accounting',
    'version': '0.3',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'author': 'Odoo Italian Community',
    'description': """
Piano dei conti italiano di un'impresa generica.
================================================

Italian accounting chart and localization.
    """,
    'category': 'Localization',
    'website': 'https://github.com/OCA/l10n-italy',
    'data': [
        'data/l10n_it_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.tax.group.csv',
        'data/account.tax.template.csv',
        'data/account.fiscal.position.template.csv',
        'data/account.chart.template.csv',
        'data/account_chart_template_data.xml',
        ],
}
