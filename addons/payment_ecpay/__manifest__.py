# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Payment Provider: ECPay",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A payment provider based in Taiwan.",
    "depends": ["payment"],
    "data": [
        "views/payment_ecpay_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
