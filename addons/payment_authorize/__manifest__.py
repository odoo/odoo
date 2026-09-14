{
    "name": "Payment Provider: Authorize.Net",
    "version": "2.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "An payment provider covering the US, Australia, and Canada.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_authorize_templates.xml",
        "views/payment_provider_views.xml",
        "views/payment_token_views.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_authorize/static/src/interactions/payment_form.js",
            "payment_authorize/static/src/scss/payment_authorize.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
