{
    "name": "Coupons & Loyalty",
    "version": "1.2",
    "category": "Sales/Sales",
    "summary": "Use discounts, gift card, eWallets and loyalty programs in different sales channels",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/loyalty_security.xml",
        "reports/loyalty_report_templates.xml",
        "reports/loyalty_report.xml",
        "data/mail_template_data.xml",
        "data/loyalty_data.xml",
        "wizards/loyalty_card_update_balance_views.xml",
        "wizards/loyalty_generate_wizard_views.xml",
        "views/loyalty_card_views.xml",
        "views/loyalty_history_views.xml",
        "views/loyalty_mail_views.xml",
        "views/loyalty_program_views.xml",
        "views/loyalty_reward_views.xml",
        "views/loyalty_rule_views.xml",
        "views/portal_templates.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/loyalty_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "loyalty/static/src/js/**/*.js",
            "loyalty/static/src/scss/*.scss",
            "loyalty/static/src/xml/*.xml",
            (
                "remove",
                "loyalty/static/src/js/portal/**/*",
            ),
        ],
        "web.assets_web_dark": [],
        "web.assets_unit_tests": [
            "loyalty/static/tests/unit/**/*",
        ],
        "web.assets_frontend": [
            "loyalty/static/src/js/portal/**/*",
            "loyalty/static/src/interactions/*",
        ],
    },
}
