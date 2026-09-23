{
    "name": "Spain - Veri*Factu for Point of Sale",
    "version": "1.0",
    "category": "Accounting/Localizations/Point of Sale",
    "summary": "Add Veri*Factu support to Point of Sale",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "l10n_es_edi_verifactu",
        "point_of_sale",
    ],
    "data": [
        "security/ir.access.csv",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_es_edi_verifactu_pos/static/src/**/*",
        ],
    },
    "auto_install": True,
}
