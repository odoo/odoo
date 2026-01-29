# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Peruvian - Point of Sale with Pe Doc",
    "version": "1.0",
    "category": "Accounting/Localizations/Point of Sale",
    "author": "Vauxoo, Odoo S.A.",
    "description": """
This module brings the technical requirement for the Peruvian regulation.
Install this if you are using the Point of Sale app in Peru.
    """,
    "depends": [
        "l10n_pe",
        "point_of_sale",
    ],
    "countries": [
        "pe",
    ],
    "data": [
        "data/res_partner_data.xml",
        "views/templates.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": ["l10n_pe_pos/static/src/**/*"],
    },
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
