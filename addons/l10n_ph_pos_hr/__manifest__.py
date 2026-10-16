# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Philippines - Point of Sale with Employees",
    "category": "Accounting/Localizations/Point of Sale",
    "countries": ["ph"],
    "summary": "Employee-based line void auditing for Philippines Point of Sale.",
    "depends": [
        "l10n_ph_pos",
        "pos_hr",
    ],
    "auto_install": True,
    "data": [
        "security/ir.access.csv",
        "views/hr_employee_views.xml",
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
        "views/pos_line_void_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ph_pos_hr/static/src/**/*",
        ],
        "web.assets_tests": [
            "l10n_ph_pos_hr/static/tests/tours/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
