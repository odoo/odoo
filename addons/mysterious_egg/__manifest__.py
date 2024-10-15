# -*- coding: utf-8 -*-
{
    'name': "mysterious egg",

    'summary': "Oh? An egg is hatching!",

    'description': """
    Oh? An egg is hatching!
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'auto_install': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'html_editor', 'website'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'mysterious_egg/static/src/builder/**/*',
            ('remove', 'mysterious_egg/static/src/builder/**/*'),
        ],
        # this bundle is lazy loaded when the editor is ready
        'website.assets_builder': [
            'mysterious_egg/static/src/builder/**/*',
        ]
    },
}
