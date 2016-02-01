# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'eCommerce',
    'category': 'Website',
    'sequence': 55,
    'summary': 'Sell Your Products Online',
    'website': 'https://www.odoo.com/page/e-commerce',
    'description': """
Odoo E-Commerce
==================

        """,
    'depends': ['website', 'sale', 'payment', 'website_payment', 'website_portal_sale', 'website_mail', 'rating'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_sale.xml',
        'data/crm_team_data.xml',
        'data/ir_actions_data.xml',
        'data/product_style_data.xml',
        'data/web_planner_data.xml',
        'data/website_menu_data.xml',
        'data/website_pricelist_data.xml',
        'views/payment_transaction_views.xml',
        'views/product_templates.xml',
        'views/product_views.xml',
        'views/report_shop_saleorder.xml',
        'views/sale_order_views.xml',
        'views/snippets.xml',
        'views/website_config_settings_view.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'application': True,
}
