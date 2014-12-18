# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Scott Saunders. Copyright Asphalt Zipper, Inc.
# Contributors: Matt Taylor

{
    "name": "MRP LLC",
    "version": "2.2",
    "summary": "MRP Low Level Code",
    "category": "Manufacturing",
    "author": "scosist",
    "website": "http://www.github.com/asphaltzipper/azi-odoo-modules",
    'description': """
MRP Calculation by low level code.
    """,
    "depends": ["mrp"],
    "data" : [
        'security/ir.model.access.csv',
    ],
    "demo": [],
    "test":[],
    "js":[],
    "css":[],
    "installable": True,
    "auto_install": False,
}
