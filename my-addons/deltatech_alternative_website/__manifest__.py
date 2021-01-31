# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


{
    "name": "Website alternative code",
    "version": "14.0.1.0.0",
    "author": "Terrabit, Dorin Hongu",
    "license": "LGPL-3",
    "website": "https://www.terrabit.ro",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Website",
    "depends": ["website_sale", "deltatech_alternative"],
    "data": ["views/product_view.xml", "views/templates.xml"],
    "images": ["images/main_screenshot.png"],
    "development_status": "stable",
    "maintainers": ["dhongu"],
}
