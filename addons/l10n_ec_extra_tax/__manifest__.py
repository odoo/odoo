# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Accounting',
    'version': '3.3',
    'description': '''
        This module adds seldom used taxes for l10n_ec.
    ''',
    'author': 'OPA CONSULTING & TRESCLOUD',
    'category': 'Accounting/Localizations',
    'maintainer': 'OPA CONSULTING',
    'website': 'https://opa-consulting.com',
    'license': 'OEEL-1',
    'depends': [
        'l10n_ec'
    ],   
    'data': [
        'data/account_tax_template_withhold_profit_data.xml',
        
    ],
    'demo': [
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
