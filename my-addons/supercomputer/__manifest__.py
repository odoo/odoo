# -*- coding: utf-8 -*-
{
    'name': "supercomputer",

    'summary': """
        Super computer inc.""",

    'description': """
        Super computer inc. training module
    """,

    'author': "SuperComputer",
    'website': "http://www.supercomputer.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'sale'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/product_com.xml',
        'views/views.xml',
        'views/templates.xml',
        'report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
