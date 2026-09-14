{
    "name": "Payment Provider: Stripe",
    "version": "2.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "An Irish-American payment provider covering the US and many others.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_provider_views.xml",
        "views/payment_stripe_templates.xml",
        "views/payment_templates.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_stripe/static/src/interactions/**/*",
            "payment_stripe/static/src/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
