{
    "name": "France - Time Off",
    "version": "1.1",
    "category": "Human Resources/Time Off",
    "summary": "Management of leaves for part-time workers in France",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr_holidays",
    ],
    "countries": [
        "fr",
    ],
    "data": [
        "security/ir.access.csv",
        "views/res_config_settings_views.xml",
        "views/l10n_fr_hr_holidays_menus.xml",
    ],
    "demo": [
        "demo/l10n_fr_hr_holidays_demo.xml",
    ],
    "auto_install": [
        "hr_holidays",
    ],
}
