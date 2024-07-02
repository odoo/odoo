# -*- coding: utf-8 -*-
{
    'name': "Test Module",
    'summary': "Test Module by owl",
    'description': """""",
    'author': "Odoo-love",
    'website': "https://www.odoo.com/test_module",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/test_mod.xml',
    ],
}