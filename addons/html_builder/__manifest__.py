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
            'html_builder/static/src/**/*',
            ('remove', 'html_builder/static/src/builder/**/*.js'),
            ('remove', 'html_builder/static/src/builder/**/*.xml'),
            ('remove', 'html_builder/static/src/builder/**/*.inside.scss'),
        ],
        # this bundle is lazy loaded when the editor is ready
        'website.assets_builder': [
            ('include', 'web._assets_helpers'),

            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',

            'html_builder/static/src/builder/**/*.js',
            'html_builder/static/src/builder/**/*.xml',

            'html_builder/static/src/builder/add_snippet_dialog/snippet_viewer.scss'
        ],
        'html_builder.inside_builder_style': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_primary_variables'),
            'web/static/src/scss/bootstrap_overridden.scss',
            'html_builder/static/src/builder/**/*.inside.scss',
        ],
        'html_builder.iframe_add_dialog': [
            ('include', 'web.assets_frontend'),
            'html_builder/static/src/builder/add_snippet_dialog/snippet_viewer.scss'
        ],
        'web.assets_unit_tests': [
            'html_builder/static/tests/**/*',
            ('include', 'website.assets_builder'),
        ],
    },
    'license': 'LGPL-3',
}
