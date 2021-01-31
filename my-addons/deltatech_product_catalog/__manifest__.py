# ©  2008-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


{
    "name": "Product Catalog",
    "version": "14.0.1.0.0",
    "summary": """This module helps to print the catalog of the multi products""",
    "category": "Inventory",
    "author": "Terrabit, Dorin Hongu",
    "company": "Terrabit",
    "maintainer": "Terrabit",
    "website": "https://www.terrabit.ro",
    "depends": ["product", "deltatech_alternative", "website_sale"],
    "data": ["report/product_catalog_report.xml", "report/product_catalog_template.xml"],
    "images": ["static/description/main_screenshot.png"],
    "license": "AGPL-3",
    "installable": True,
    "development_status": "stable",
    "maintainers": ["dhongu"],
}
