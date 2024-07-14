# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Avatax Brazil for Services",
    "version": "1.0",
    "category": "Accounting/Accounting",
    "depends": ["l10n_br_avatax", "base_address_extended"],
    "data": [
        "security/ir_rule.xml",
        "data/ir.model.access.csv",
        "data/l10n_br.ncm.code.csv",
        "data/res_country_data.xml",
        "data/res.city.csv",
        "views/product_template_views.xml",
        "views/l10n_br_service_code_views.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/res_city_demo.xml",
        "demo/res_partner_demo.xml",
        "demo/l10n_br_service_code_demo.xml",
        "demo/product_product_demo.xml",
    ],
    "license": "OEEL-1",
    "auto_install": ["l10n_br_avatax"],
}
