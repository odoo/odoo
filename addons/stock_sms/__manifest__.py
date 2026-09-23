{
    "name": "Stock - SMS",
    "version": "1.1",
    "category": "Supply Chain/Inventory",
    "summary": "Send text messages when final stock move",
    "description": "Send text messages when final stock move",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "sms",
    ],
    "data": [
        "data/sms_data.xml",
        "views/res_config_settings_views.xml",
        "wizards/confirm_stock_sms_views.xml",
        "security/ir.access.csv",
    ],
    "auto_install": True,
    "post_init_hook": "_update_default_sms_template",
    "uninstall_hook": "_reset_sms_text_confirmation",
}
