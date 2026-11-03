# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Philippines - Discount Privileges on POS Orders with Loyalty",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ph"],
    "category": "Accounting/Localizations/Point of Sale",
    "summary": "Keep loyalty discounts off SC/PWD privileged POS order lines.",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html",
    "depends": [
        "l10n_ph_pos",
        "pos_loyalty",
    ],
    "auto_install": True,
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ph_pos_loyalty/static/src/app/**/*",
        ],
        "web.assets_tests": [
            "l10n_ph_pos_loyalty/static/tests/tours/**/*",
        ],
    },
    "license": "LGPL-3",
}
