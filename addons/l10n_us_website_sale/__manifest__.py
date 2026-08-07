# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "United States eCommerce",
    "icon": "/base/static/img/country_flags/us.png",
    "countries": ["us"],
    "category": "Accounting/Localizations/Website",
    "description": "Bridge eCommerce for the United States",
    "depends": ["l10n_us", "website_sale"],
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "post_init_hook": "_post_init_hook",
}
