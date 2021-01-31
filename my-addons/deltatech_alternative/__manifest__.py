# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


{
    "name": "Products Alternative",
    "version": "14.0.1.0.0",
    "author": "Terrabit, Dorin Hongu",
    "website": "https://www.terrabit.ro",
    "summary": "Alternative product codes",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Sales",
    "depends": ["product", "stock"],
    "license": "LGPL-3",
    "data": ["views/product_view.xml", "security/ir.model.access.csv"],
    "images": ["images/main_screenshot.png"],
    "development_status": "stable",
    "maintainers": ["dhongu"],
}
