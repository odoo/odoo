# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/spreadsheet_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'spreadsheet_edition/static/src/bundle/**/*.js',
            'spreadsheet_edition/static/src/bundle/**/filter_editor_side_panel.xml',
            'spreadsheet_edition/static/src/bundle/**/*.xml',
            ('remove', 'spreadsheet_edition/static/src/bundle/actions/control_panel/spreadsheet_breadcrumbs.xml'),
            ('remove', 'spreadsheet_edition/static/src/bundle/pivot/pivot.xml'),
        ],
        'spreadsheet.assets_print': [
            'spreadsheet_edition/static/src/print_assets/**/*',
        ],
        'web.assets_backend': [
            'spreadsheet_edition/static/src/**/*.scss',
            'spreadsheet_edition/static/src/bundle/pivot/pivot.xml',
            'spreadsheet_edition/static/src/bundle/actions/control_panel/spreadsheet_breadcrumbs.xml',
            'spreadsheet_edition/static/src/assets/**/*',
        ],
        'web.qunit_suite_tests': [
            'spreadsheet_edition/static/tests/**/*',
        ],
        'web.qunit_mobile_suite_tests': [
            'spreadsheet_edition/static/tests/utils/mock_server.js',
        ],
    }
}
