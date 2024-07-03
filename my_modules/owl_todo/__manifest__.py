# -*- coding: utf-8 -*-
{
    'name': "TODO",
    'summary': "Todo list by owl",
    'description': """""",
    'author': "Odoo-love",
    'website': "https://www.odoo.com/owl_todo",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Owl',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],
    'license': 'LGPL-3',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/todo_list.xml',
        'views/res_partner.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'owl_todo/static/src/components/*/*.js',
            'owl_todo/static/src/components/*/*.xml',
            'owl_todo/static/src/components/*/*.scss',
        ],
    },
    'application': True
}