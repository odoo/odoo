# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gift Card for sales module",
    'summary': "Use gift card in your sales orders",
    'description': """Integrate gift card mechanism in sales orders.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['gift_card', 'sale'],
    'auto_install': True,
    'data': [
        'data/gift_card_data.xml',
        'data/mail_template_data.xml',
        'views/sale_order_view.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}
