# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet', 'mail', 'web_enterprise'],
    'data': [
        'security/ir.model.access.csv',
        'views/spreadsheet_views.xml',
        'data/mail_template_layouts.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'spreadsheet_edition/static/src/bundle/**/*.js',
            'spreadsheet_edition/static/src/bundle/**/filter_editor_side_panel.xml',
            'spreadsheet_edition/static/src/bundle/**/*.xml',
            ('remove', 'spreadsheet_edition/static/src/bundle/pivot/pivot.xml'),
        ],
        'spreadsheet.assets_print': [
            'spreadsheet_edition/static/src/print_assets/**/*',
        ],
        'web.assets_backend': [
            'spreadsheet_edition/static/src/**/*.scss',
            ('remove', 'spreadsheet_edition/static/src/**/*.dark.scss'),
            'spreadsheet_edition/static/src/assets/**/*',
            ('remove', 'spreadsheet_edition/static/src/assets/graph_view/**'),
            ('remove', 'spreadsheet_edition/static/src/assets/pivot_view/**'),
        ],
        'web.assets_web_dark': [
            'spreadsheet_edition/static/src/**/*.dark.scss',
        ],
        'web.assets_backend_lazy': [
            'spreadsheet_edition/static/src/assets/graph_view/**',
            'spreadsheet_edition/static/src/assets/pivot_view/**',
            'spreadsheet_edition/static/src/bundle/pivot/pivot.xml',
        ],
        'web.qunit_suite_tests': [
            'spreadsheet_edition/static/tests/legacy/**/*',
        ],
        'web.qunit_mobile_suite_tests': [
            'spreadsheet_edition/static/tests/legacy/disable_patch.js',
        ],
        'web.assets_unit_tests': [
            'spreadsheet_edition/static/tests/**/*',
            ('remove', 'spreadsheet_edition/static/tests/legacy/**/*'),  # to remove when all legacy tests are ported
        ],
    }
}
