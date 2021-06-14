# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Loyalty - Ecommerce',
    'summary': 'Bridge module loyalty using the website ecommerce.',
    'description': 'Bridge module to allow website ecommerce to use loyalty programs.',
    'category': 'Sale',
    'depends': [
        'loyalty',
        'sale_reward',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/loyalty_views.xml',
        'views/portal_templates.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sale_views.xml',
        'views/website_sale_loyalty_views.xml',
        'views/website_sale_templates.xml',
    ],
    'demo': [
        'data/loyalty_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/website_sale_loyalty/static/src/scss/website_sale_loyalty.scss',
            '/website_sale_loyalty/static/src/js/website_sale_loyalty_add_reward_button.js',
        ],
        'web.assets_tests': [
            '/website_sale_loyalty/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
