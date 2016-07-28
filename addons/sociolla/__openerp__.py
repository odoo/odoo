# -*- coding: utf-8 -*-
{
    'name': "Sociolla",

    'summary': """
        Sociolla addon for odoo""",

    'description': """This module addon is for PT. Social Bella Indonesia
    """,

    'author': "Sociolla Internal Developer, PT. Social Bella Indonesia",
    'website': "http://www.sociolla.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Addon',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}