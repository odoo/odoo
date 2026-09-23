{
    "name": "Shopper's Wishlist",
    "version": "1.0",
    "category": "Website/Website",
    "summary": "Allow shoppers to enlist products",
    "description": """
Allow shoppers of your eCommerce store to create personalized collections of products they want to buy and save them for future reference.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
    ],
    "data": [
        "security/ir.access.csv",
        "views/website_sale_wishlist_template.xml",
        "views/website_sale_wishlist_template_svg.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_sale_wishlist/static/src/interactions/**/*",
            "website_sale_wishlist/static/src/scss/**/*",
            "website_sale_wishlist/static/src/js/**/*",
        ],
        "web.assets_tests": [
            "website_sale_wishlist/static/tests/**/*",
        ],
        "website.website_builder_assets": [
            "website_sale_wishlist/static/src/website_builder/**/*",
        ],
    },
    "auto_install": True,
}
