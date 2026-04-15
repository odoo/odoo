{
    'name': "test_search_panel",
    'description': "Tests for the search panel python methods",

    'category': 'Hidden/Tests',
    'version': '0.1',

    'depends': ['web', 'test_orm', 'test_tools'],

    'data': ['ir.access.csv'],

    'assets': {
        'web.assets_tests': [
            'test_web/static/tests/tours/*.js',
        ],
    },

    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
