# -*- coding: utf-8 -*-
{
    'name': "Grid View",

    'summary': "Basic 2D Grid view for odoo",
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['web'],
    'assets': {
        'web.assets_backend_lazy': [
            'web_grid/static/src/**/*',

            # Don't include dark mode files in light mode
            ('remove', 'web_grid/static/src/**/*.dark.scss'),
        ],
        'web.assets_backend_lazy_dark': [
            'web_grid/static/src/**/*.dark.scss',
        ],
        'web.assets_unit_tests': [
            'web_grid/static/tests/**/*.test.js',
            'web_grid/static/tests/grid_mock_server.js',
        ],
        'web.qunit_suite_tests': [
            'web_grid/static/tests/legacy/helpers.js',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
