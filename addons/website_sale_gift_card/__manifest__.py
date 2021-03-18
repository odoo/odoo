# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Website Sale Gift Card",
    'summary': "Use gift card in eCommerce",
    'description': """Integrate gift card mechanism in your ecommerce.""",
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale', 'gift_card'],
    'data': [
        'views/template.xml',
        'views/gift_card_views.xml',
        'views/product_views.xml',
        'views/gift_card_menus.xml',
        'views/assets.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
}
