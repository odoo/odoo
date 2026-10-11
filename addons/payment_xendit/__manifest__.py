# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Payment Provider: Xendit",
    "version": "1.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A payment provider for Southeast Asia.",
    "description": " ",  # Non-empty string to avoid loading the README file.
    "depends": ["payment"],
    "data": [
        "views/payment_provider_views.xml",
        "data/payment_method_data.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "assets": {"web.assets_frontend": ["payment_xendit/static/src/**/*"]},
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
