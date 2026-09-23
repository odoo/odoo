{
    "name": "Sale Loyalty",
    "version": "1.1",
    "category": "Sales/Sales",
    "summary": "Use discounts and loyalty programs in sales orders",
    "description": "Integrate discount and loyalty programs mechanisms in sales orders.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "loyalty",
    ],
    "data": [
        "security/ir.access.csv",
        "data/sale_loyalty_data.xml",
        "wizards/sale_loyalty_coupon_wizard_views.xml",
        "wizards/sale_loyalty_reward_wizard_views.xml",
        "views/loyalty_card_views.xml",
        "views/loyalty_program_views.xml",
        "views/sale_order_views.xml",
        "views/sale_portal_templates.xml",
        "views/res_partner_views.xml",
        "views/sale_loyalty_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_loyalty/static/src/**/*",
        ],
    },
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
