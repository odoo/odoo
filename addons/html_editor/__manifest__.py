# -*- coding: utf-8 -*-
{
    'name': "HTML Editor",

    'summary': """
        Experimental implementation
    """,

    'description': """
        New implementation for html editor
    """,

    'author': "GED",
    'website': "https://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tutorial',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],
    'application': True,
    'installable': True,
    'data': [
        'views/views.xml',
    ],
    'assets': {
        'html_editor.assets': [
            'html_editor/static/src/editor/*',
        ],
        'web.assets_backend': [
            'html_editor/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'html_editor/static/tests/**/*',
        ],

    },
    'license': 'AGPL-3'
}
