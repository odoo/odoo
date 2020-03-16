# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Finnish Localization",
    "version": "13.0.1.0.0",
    "author": "Avoin.Systems, "
              "Tawasta, "
              "Vizucom",
    "category": "Localization",
    "website": "https://avoin.systems",
    "depends": [
        "account",
    ],
    "installable": True,
    "data": [
        "data/res_partner_operator_einvoice_data.xml",
        "security/ir.model.access.csv",
        "views/menuitems.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_operator_einvoice_views.xml",
        "views/res_partner_views.xml",
    ]
}
