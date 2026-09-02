# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Canada eCommerce",
    "icon": "/base/static/img/country_flags/ca.png",
    "countries": ["ca"],
    "category": "Accounting/Localizations/Website",
    "description": "Bridge eCommerce for the Canada",
    "depends": ["l10n_ca", "website_sale"],
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "post_init_hook": "_post_init_hook",
}
