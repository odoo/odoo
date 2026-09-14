{
    "name": "Payment Provider: Buckaroo",
    "version": "2.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A Dutch payment provider covering several countries in Europe.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_buckaroo_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
