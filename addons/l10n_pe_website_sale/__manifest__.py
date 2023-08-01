# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Peruvian eCommerce",
    "version": "0.1",
    "summary": "Be able to see Identification Type in ecommerce checkout form.",
    "category": "Accounting/Localizations/Website",
    "author": "Vauxoo, Odoo",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
        "l10n_pe",
    ],
    "data": [
        "data/ir_model_fields.xml",
        "views/templates.xml",
    ],
    "demo": [
        "demo/website_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_pe_website_sale/static/src/js/website_sale.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
