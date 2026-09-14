{
    "name": "Payment Provider: Mercado Pago",
    "version": "1.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A payment provider covering several countries in Latin America.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_form_templates.xml",
        "views/payment_mercado_pago_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_mercado_pago/static/src/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
