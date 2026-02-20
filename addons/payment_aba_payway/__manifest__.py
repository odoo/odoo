# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Payment Provider: ABA PayWay",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A payment provider based in Cambodia.",
    "depends": ["payment"],
    "data": [
        'views/payment_form_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_aba_payway/static/src/interactions/payment_form.js',
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
