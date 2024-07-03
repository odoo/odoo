# -*- coding: utf-8 -*-
{
    'name': "validator",

    'summary': "",

    'description': """
    """,

    'author': "Odoo-love",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Phone',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],
    'application': True,
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'validator/static/src/components/*/*.js',
            'validator/static/src/components/*/*.xml',
            'validator/static/src/components/*/*.scss',
        ],
    }
}

