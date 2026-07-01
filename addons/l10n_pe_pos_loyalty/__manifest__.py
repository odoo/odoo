# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Peru POS - Loyalty",
    "version": "1.0",
    "category": "Accounting/Localizations/Point of Sale",
    "summary": "Link module between l10n_pe_pos and pos_loyalty",
    "description": """
Peruvian Point of Sale loyalty extension.
Fixes eWallet/gift card tax rounding when both modules are installed.
    """,
    "depends": [
        "l10n_pe_pos",
        "pos_loyalty",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_pe_pos_loyalty/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "l10n_pe_pos_loyalty/static/src/**/*",
            "l10n_pe_pos_loyalty/static/tests/unit/**/*",
        ],
    },
    "installable": True,
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
