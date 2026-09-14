{
    "name": "Payment Provider: Paypal",
    "version": "2.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "An American payment provider for online payments all over the world.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_form_templates.xml",
        "views/payment_provider_views.xml",
        "views/payment_transaction_views.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_paypal/static/src/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
