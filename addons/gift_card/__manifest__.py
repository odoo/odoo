# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gift Card",
    'summary': "Use gift card",
    'description': """Integrate gift card mechanism""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['product'],
    'data': [
        'data/gift_card_data.xml',
        'views/views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}
