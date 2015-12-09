# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Products Catalog',
    'category': 'Sales Management',
    'depends': ['product'],
    'description': """
Manage your products and services from one app.
========================================================

It is the central place to manage your products and services, its variants, unit of measures and other properties.
    """,
    'data': [
        'views/product_catalog_settings_views.xml',
    ],
    'application': True,

}
