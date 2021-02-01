# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gift Card",
    'summary': "Use gift card in your sales orders",
    'description': """Integrate gift card mechanism in sales orders.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale'],
    'data': [
        'data/gift_card_template_email.xml',
        'data/gift_card_data.xml',
        'views/views.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
    ]
}
