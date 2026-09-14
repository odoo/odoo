{
    "name": "Payment Provider: Adyen",
    "version": "2.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A Dutch payment provider covering Europe and the US.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_adyen_templates.xml",
        "views/payment_form_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
        "wizards/payment_capture_wizard_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_adyen/static/src/interactions/payment_form.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
