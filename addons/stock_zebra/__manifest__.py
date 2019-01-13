# -*- coding: utf-8 -*-
{
    'name': "stock_zebra",

    'summary': """
        Zebra printers integration for stock module""",

    'description': """
        This module bring templates to produce labels in the Stock app (and derivatives) for Zebra printers. Those devices print thermal barcode label and shipping labels. Printers make label from ZPL script which is built in Odoo.""",

    'author': "Odoo SA",
    'website': "https://www.odoo.com",

    'category': 'stock',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'stock'],

    # always loaded
    'data': [
        'report/package_templates.xml',
        'report/picking_templates.xml',
        'report/product_templates.xml',
        'report/product_packaging.xml',
        'report/stock_reports.xml',
    ],
}
