# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Coupons, Promotions, Gift Card and Loyalty for eCommerce",
    'summary': """Use coupon, promotion, gift cards and loyalty programs in your eCommerce store""",
    'description': """
Create coupon, promotion codes, gift cards and loyalty programs to boost your sales (free products, discounts, etc.). Shoppers can use them in the eCommerce checkout.

Coupon & promotion programs can be edited in the Catalog menu of the Website app.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale', 'website_links', 'sale_loyalty'],
    'data': [
        'security/ir.model.access.csv',

        'views/loyalty_card_views.xml',
        'views/loyalty_program_views.xml',
        'views/snippets.xml',
        'views/website_sale_templates.xml',
        'views/website_sale_loyalty_menus.xml',

        'wizard/coupon_share_views.xml',
        'wizard/res_config_settings_views.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'auto_install': ['website_sale', 'sale_loyalty'],
    'assets': {
        'web.assets_frontend': [
            'website_sale_loyalty/static/src/js/coupon_toaster_widget.js',
            'website_sale_loyalty/static/src/js/website_sale_gift_card.js',
            'website_sale_loyalty/static/src/js/website_sale_loyalty_delivery.js',
        ],
        'web.assets_tests': [
            'website_sale_loyalty/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
