# -*- coding: utf-8 -*-
# JUAN PABLO YAÑEZ CHAPITAL
{
    "name": "Product Brand Management",
    "author": "JUAN PABLO YAÑEZ CHAPITAL",
    "website": "http://www.chapital.com.mx",
    "support": "compraschapital@hotmail.com",
    "license": "OPL-1",
    "category": "Productivity",
    "summary": "Manage Brand Products, Search Brand Wise Product App, Filter Product By Brand, Select Brand Product Module, Group By Product Brands, Choose Brand Product, Get Particular Brand Product, Assign Products Brand Odoo",

    "description": """Do you want to get brand-wise products? Currently, in odoo, you can"t manage products by brands. This module allows for managing product brands. It also helps to search, filter and group by-products by brand, it also shows how many products in a particular brand.""",

    "version": "15.0.4",
    "depends": [
        "sale_management", 'purchase'
    ],
    "application": True,
    "data": [
        # "security/product_brand_security.xml",
        "security/ir.model.access.csv",
        "views/sh_product_brand_view.xml",
        "views/sh_product_view.xml",
        "views/sh_brand_other_view.xml",
    ],
    "auto_install": False,
    "installable": True,
    "price": 0,
    "currency": "EUR"
}
