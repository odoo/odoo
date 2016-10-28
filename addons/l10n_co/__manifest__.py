# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Colombian Acounting - Common Base',
    'version': '1.0',
    'category': 'Localization',
    'description': 'Colombian Accounting Common Base for NIIF/Dual and OLD Charts',
    'author': 'David Arnold (DevCO Colombia)',
    'website': 'http://www.devco.co',
    'depends': ['account'],
    'data': [
        'data/account_tax_group_data.xml',
        'data/account_type_data.xml',
        'data/account_account_template_data.xml',
        'data/menuitem_data.xml',
    ],
}
