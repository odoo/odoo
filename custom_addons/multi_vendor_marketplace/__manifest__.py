# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': "Odoo Multi Vendor Marketplace",
    'version': "16.0.1.0.0",
    'category': 'eCommerce,Sales ,Warehouse',
    'summary': 'Odoo Multi Vendor Marketplace, Odoo16, Multi Vendor',
    'description': 'The Multi-Vendor Marketplace module in Odoo enables '
                   'businesses to establish an online platform where multiple'
                   'vendors can offer their products or services to customers.'
                   'Vendors can manage their own profiles, products, and '
                   'orders, while the admin can set commission rates, manage '
                   'payments, maintain quality control. The module provides'
                   'customization options, and user-friendly interfaces for a '
                   'seamless marketplace experience. ',
    'author': 'Cybrosys Techno solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'sale_management', 'account', 'website', 'stock',
                'website_sale'],
    'data': [
        'security/multi_vendor_marketplace_groups.xml',
        'security/inventory_request_security.xml',
        'security/product_template_security.xml',
        'security/sale_order_line_security.xml',
        'security/seller_payment_security.xml',
        'security/seller_shop_security.xml',
        'security/stock_picking_security.xml',
        'security/ir.model.access.csv',
        'data/res_users_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/social_media_data.xml',
        'data/account_journal_data.xml',
        'data/product_template_data.xml',
        'data/email_template_data.xml',
        'data/website_menu_data.xml',
        'views/vendor_dashboard_views.xml',
        'views/stock_moves_views.xml',
        'views/sell_page_templates.xml',
        'views/res_partner_views.xml',
        'views/seller_payment_views.xml',
        'views/request_payment_views.xml',
        'views/multi_vendor_pricelist_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/seller_shop_views.xml',
        'views/res_config_settings_views.xml',
        'views/seller_review_views.xml',
        'views/helpful_info_views.xml',
        'views/product_public_category_views.xml',
        'views/account_payment_method_views.xml',
        'views/stock_picking_views.xml',
        'views/inventory_request_views.xml',
        'views/seller_recommend_views.xml',
        'views/social_media_views.xml',
        'views/seller_web_templates.xml',
        'views/seller_product_templates.xml',
        'views/sale_order_line_views.xml',
        'views/multi_vendor_marketplace_menus.xml',
        'views/seller_shop_information_templates.xml',
        'views/seller_list_templates.xml',
        'wizard/settings_view_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'multi_vendor_marketplace/static/src/xml/saller_dashboard.xml',
            'multi_vendor_marketplace/static/src/js/seller_dashboard_action.js',
        ],
        'web.assets_frontend': [
            'multi_vendor_marketplace/static/src/js/rating.js',
            'multi_vendor_marketplace/static/src/scss/partner_rating.css',
            'https://unpkg.com/sweetalert/dist/sweetalert.min.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto install': False,
    'pre_init_hook': 'test_pre_init_hook',
}
