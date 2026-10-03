# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Philippines - Discount Privileges on POS Orders",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ph"],
    "category": "Accounting/Localizations/Point of Sale",
    "summary": "Apply Philippine SC/PWD discount privileges on restaurant POS orders.",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html",
    "depends": [
        "l10n_ph_invoice",
        "pos_restaurant",
    ],
    "data": [
        "security/ir.access.csv",
        "views/res_partner_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ph_pos_restaurant/static/src/app/**/*",
        ],
        "web.assets_tests": [
            "l10n_ph_pos_restaurant/static/tests/tours/**/*",
        ],
    },
    "license": "LGPL-3",
}
