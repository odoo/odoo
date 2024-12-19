{
    "name": "l10n_tw_edi_ecpay_pos",
    "summary": """ECpay invoice pos module""",
    "category": "",
    "version": "1.0",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": [
        "point_of_sale",
        "l10n_tw_edi_ecpay",
    ],
    "data": [
        "data/res_partner_data.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_tw_edi_ecpay_pos/static/src/scss/**/*",
            "l10n_tw_edi_ecpay_pos/static/src/xml/**/*",
            "l10n_tw_edi_ecpay_pos/static/src/js/**/*",
        ],
    },
}
