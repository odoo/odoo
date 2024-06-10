{
    'name': "HTML Editor Playground",

    'summary': """
        Experimental playground
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
    'depends': ['base', 'web', 'html_editor'],
    'application': True,
    'installable': True,
    'data': [
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'html_editor_playground/static/src/**/*',
        ],
    },
    'license': 'AGPL-3'
}
