# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Payment Provider: QFPay",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A payment provider covering the Hong Kong Market.",
    "description": " ",  # Non-empty string to avoid loading the README file.
    "depends": ["payment"],
    "data": [
        "views/payment_qfpay_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_method_data.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "assets": {"web.assets_frontend": ["payment_qfpay/static/src/interactions/payment_form.js"]},
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
