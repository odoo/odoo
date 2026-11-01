# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Thai Localization Base",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "Thai localization base: Sarabun font default, Buddhist year, company config",
    "author": "Custom",
    "website": "https://github.com/OCA/l10n-thailand",
    "license": "LGPL-3",
    "depends": [
        "od19_thai_font_support",
        "l10n_th",
        "l10n_th_base_utils",
        "l10n_th_base_sequence",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "icon": "/od19_thai_localization_base/static/description/icon.svg",
}
