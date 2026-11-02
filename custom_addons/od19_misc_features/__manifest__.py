# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Misc Features",
    "version": "19.0.1.0.0",
    "summary": "Consolidation of small missing features (logo ISO, sequence constraint skip, data link mixin, runtime guard, repeat customer report)",
    "author": "OD19",
    "category": "Tools",
    "depends": ["base", "mail", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "views/runtime_guard_views.xml",
        "views/repeat_customer_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_misc_features/static/description/icon.svg",
}
