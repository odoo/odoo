# -*- coding: utf-8 -*-
{
    'name': 'JYS Tiktok Integration for Odoo17',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Tiktok Integration',
    'description': 'Tiktok Integration for Odoo17',
    'author': 'Jova Software',
    'maintainer': 'Jova Software',
    'company': 'Jova Software',
    'website': 'https://www.jovasoftware.com',
    'depends': ['web','base', 'contacts', 'delivery', 'sale', 'product', 'sale_management', 'stock'],
    'data': [
        'security/tiktok_group.xml',
        'security/ir.model.access.csv',


        'wizard/tiktok_add_product_views.xml',
        'wizard/tiktok_update_product_views.xml',
        'wizard/tiktok_get_order_views.xml',
        'wizard/tiktok_get_item_views.xml',
        'wizard/tiktok_get_category_views.xml',
        'wizard/tiktok_get_attribute_views.xml',
        'wizard/tiktok_get_brand_views.xml',
        'wizard/tiktok_get_product_views.xml',
        'wizard/delete_confirmation_wizard_views.xml',
        'wizard/upload_image_wizard_views.xml',
        'wizard/tiktok_shipping_label_views.xml',

        'views/product_template_views.xml',
        'views/delivery_carrier_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',

        'views/tiktok_attribute_views.xml',
        'views/tiktok_category_views.xml',
        'views/tiktok_history_api_views.xml',
        'views/tiktok_item_views.xml',
        'views/tiktok_order_views.xml',
        'views/tiktok_shop_views.xml',
        'views/res_company_views.xml',
        'views/tiktok_token_views.xml',
        'views/tiktok_product_image_views.xml',
        'views/tiktok_brand_views.xml',
        
        'views/jys_tiktok_menu.xml',
        'views/tiktok_assets.xml'

    ],

    'license': 'Other proprietary',
    'installable': True,
}
