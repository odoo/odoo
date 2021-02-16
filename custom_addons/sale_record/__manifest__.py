# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'sale_record',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 12,
    'description': """Make a record rule such that user can view sale orders for which he is assigned as sales person""",
    'category': '',
    'depends': [
            'base',
            'contacts',
            'partner_autocomplete',
            'sale_management',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        'security/sale_user.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
