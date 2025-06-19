# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Uruguayan - Point of Sale",
    "version": "1.0",
    "category": "Accounting/Localizations/Point of Sale",
    "description": """
This module brings the technical requirement for the Uruguayan regulation.
Install this if you are using the Point of Sale app in Uruguay.
    """,
    "depends": [
        "l10n_uy",
        "point_of_sale",
    ],
    "assets": {
        "point_of_sale._assets_pos": ["l10n_uy_pos/static/src/**/*"],
    },
    "installable": True,
    "auto_install": True,
    'author': 'Odoo S.A.',
    "license": "LGPL-3",
}
