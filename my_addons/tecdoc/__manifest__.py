# -*- coding: utf-8 -*-
{
    'name': "Tecdoc",
    'application': True,
    'summary': """
        Tecdoc Database """,

    'description': """
        This module propose the full catalog of auto's parts 
    """,
    'category_id': 'Tecdoc',
    'author': "Alain LEGRAND",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tecdoc',
    'version': '0.02',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/manufacturer_vehicle.xml',
        'views/criterias_keys.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
