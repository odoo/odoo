# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

{
    "name": "Deltatech SMS Sale",
    "version": "14.0.1.0.0",
    "author": "Terrabit, Dorin Hongu, Dan Stoica",
    "website": "https://www.terrabit.ro",
    "category": "Hidden",
    "depends": ["sale", "sales_team", "sms"],
    "license": "LGPL-3",
    "data": [
        "data/sms_data.xml",
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv",
        "security/sms_security.xml",
    ],
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
}
