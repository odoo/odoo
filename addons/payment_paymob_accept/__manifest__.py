{
    "name": "Payment Provider: Paymob",
    "version": "1.0",
    "category": "Accounting/Payment Providers",
    "author": "Paymob",
    "company": "Paymob",
    "maintainer": "Paymob",
    "website": "https://www.paymob.com",
    "sequence": 350,
    "summary": "Paymob is the leading financial services enabler in the MENA-P region.",
    "description": "Odoo plugin for paymob first fintech company to receive the Central Bank of Egypt’s (CBE) Payments Facilitator license in 2018. We launched operations in Pakistan in 2021 and in the UAE in 2022. Paymob received Saudi Payments PTSP certification in May 2023 enabling us to launch operations in KSA. In December 2023 Paymob became the first international fintech company to receive Oman’s PSP",
    "depends": ["payment"],
    "data": [
        "views/payment_provider_views.xml",
        "views/payment_paymob_templates.xml",
        "views/payment_method_views.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "/payment_paymob_accept/static/src/**/*",
        ],
    },
    "images": ["static/description/banner.jpg"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "license": "LGPL-3",
}
