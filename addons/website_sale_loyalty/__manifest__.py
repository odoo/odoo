{
    "name": "Coupons, Promotions, Gift Card and Loyalty for eCommerce",
    "version": "1.0",
    "category": "Website/Website",
    "summary": "Use coupon, promotion, gift cards and loyalty programs in your eCommerce store",
    "description": """
Create coupon, promotion codes, gift cards and loyalty programs to boost your sales (free products, discounts, etc.). Shoppers can use them in the eCommerce checkout.

Coupon & promotion programs can be edited in the Catalog menu of the Website app.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
        "website_links",
        "sale_loyalty",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/loyalty_card_views.xml",
        "views/loyalty_program_views.xml",
        "views/website_sale_templates.xml",
        "views/website_sale_loyalty_menus.xml",
        "wizards/coupon_share_views.xml",
        "wizards/res_config_settings_views.xml",
    ],
    "demo": [
        "demo/product_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_sale_loyalty/static/src/js/**/*",
            "website_sale_loyalty/static/src/interactions/**/*",
        ],
        "web.assets_tests": [
            "website_sale_loyalty/static/tests/**/*",
        ],
        "website.website_builder_assets": [
            "website_sale_loyalty/static/src/website_builder/**/*",
        ],
    },
    "auto_install": [
        "website_sale",
        "sale_loyalty",
    ],
}
