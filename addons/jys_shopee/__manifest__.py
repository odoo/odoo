# -*- coding: utf-8 -*-
{
    'name': 'JYS Shopee Integration for Odoo17',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Shopee Integration',
    'description': 'Shopee Integration for Odoo17',
    'author': 'Jova Software',
    'maintainer': 'Jova Software',
    'company': 'Jova Software',
    'website': 'https://www.jovasoftware.com',
    'depends': ['web','base', 'contacts', 'delivery', 'sale', 'product', 'sale_management', 'stock'],
    'data': [
        'security/shopee_group.xml',
        'security/ir.model.access.csv',


        'wizard/shopee_add_product_views.xml',
        'wizard/shopee_update_product_views.xml',
        'wizard/shopee_get_order_views.xml',
        'wizard/shopee_get_item_views.xml',
        'wizard/delete_confirmation_wizard_views.xml',


        'views/product_template_views.xml',
        'views/delivery_carrier_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/shopee_attribute_views.xml',
        'views/shopee_category_views.xml',
        'views/shopee_history_api_views.xml',
        'views/shopee_item_views.xml',
        'views/shopee_order_views.xml',
        'views/shopee_shop_views.xml',
        'views/res_company_views.xml',
        
        'views/jys_shopee_menu.xml',
        'views/shopee_assets.xml'

    ],

    'license': 'Other proprietary',
    'installable': True,
}
