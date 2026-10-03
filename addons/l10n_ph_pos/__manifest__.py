# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Philippines - Point of Sale",
    "category": "Accounting/Localizations/Point of Sale",
    "countries": ["ph"],
    "summary": "Philippine-specific Point of Sale extensions.",
    "depends": [
        "l10n_ph",
        "point_of_sale",
    ],
    "auto_install": [
        "l10n_ph",
        "point_of_sale",
    ],
    "data": [
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
