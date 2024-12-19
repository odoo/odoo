{
    "name": "l10n_tw_edi_ecpay_website_sale",
    "summary": """ECpay invoice eshop module""",
    "category": "",
    "version": "1.0",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": [
        "website_sale",
        "l10n_tw_edi_ecpay",
    ],
    "data": [
        "views/payment_form.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_tw_edi_ecpay_website_sale/static/src/**/*"
        ]
    },
}
