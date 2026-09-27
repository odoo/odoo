{
    "name": "Pakistan - Point of Sale",
    "countries": ["pk"],
    "category": "Accounting/Localizations/Point of Sale",
    "author": "Odoo S.A.",
    "description": """
This module brings the technical requirement for the Pakistan regulation.
Install this if you are using the Point of Sale app in Pakistan.
    """,
    "depends": [
        "l10n_pk",
        "pos_discount",
        "iap",
        "stock_delivery",
    ],
    "data": [
        "data/l10n_pk_edi_pos_data.xml",
        "receipt/pos_order_receipt.xml",
        "data/product_data.xml",
        "views/product_views.xml",
        "views/pos_order_views.xml",
        "views/pos_payment_method_views.xml",
        "views/report_invoice.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_pk_edi_pos/static/src/**/*",
        ],
        "web.assets_tests": [
            "l10n_pk_edi_pos/static/tests/tours/**/*",
        ],
    },
    "license": "LGPL-3",
}
