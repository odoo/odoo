# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Philippines - Discount Privileges on POS Orders",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ph"],
    "category": "Accounting/Localizations/Point of Sale",
    "summary": "Apply Philippine SC/PWD discount privileges on POS orders.",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html",
    "depends": [
        "l10n_ph_invoice",
        "point_of_sale",
    ],
    "data": [
        "security/ir.access.csv",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ph_pos/static/src/app/**/*",
        ],
        "web.assets_tests": [
            "l10n_ph_pos/static/tests/tours/**/*",
        ],
    },
    "license": "LGPL-3",
}
