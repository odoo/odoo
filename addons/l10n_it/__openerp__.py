# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - Accounting',
    'version': '0.2',
    'depends': ['base_vat','base_iban'],
    'author': 'OpenERP Italian Community',
    'description': """
Piano dei conti italiano di un'impresa generica.
================================================

Italian accounting chart and localization.
    """,
    'category': 'Localization/Account Charts',
    'website': 'http://www.openerp-italia.org/',
    'data': [
        'data/account.account.template.csv',
        'account_chart.xml',
        'data/account.tax.template.csv',
        'data/account.fiscal.position.template.csv',
        'l10n_chart_it_generic.xml',
        ],
    'demo': [],
    'installable': False,
    'auto_install': False,
}
