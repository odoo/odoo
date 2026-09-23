{
    "name": "Accounting - Payment Providers",
    "version": "2.2",
    "category": "Accounting/Accounting",
    "summary": "Enable customers to pay invoices on the portal and post payments when transactions are processed.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
        "payment",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "security/ir.access.csv",
        "views/account_payment_menus.xml",
        "views/account_portal_templates.xml",
        "views/account_move_views.xml",
        "views/account_journal_views.xml",
        "views/account_payment_views.xml",
        "views/payment_form_templates.xml",
        "views/payment_provider_views.xml",
        "views/payment_transaction_views.xml",
        "wizards/account_payment_register_views.xml",
        "wizards/payment_link_wizard_views.xml",
        "wizards/payment_refund_wizard_views.xml",
        "wizards/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_unit_tests": [
            "web/static/src/public/minimal_dom.js",
            "account_payment_provider/static/src/interactions/**/*",
            "account_payment_provider/static/tests/interactions/**/*",
        ],
        "web.assets_frontend": [
            "account_payment_provider/static/src/interactions/**/*",
        ],
    },
    "auto_install": [
        "account",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
