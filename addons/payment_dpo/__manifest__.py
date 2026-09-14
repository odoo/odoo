{
    "name": "Payment Provider: DPO",
    "version": "1.1",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A Kenyan payment provider covering several African countries.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_dpo_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
