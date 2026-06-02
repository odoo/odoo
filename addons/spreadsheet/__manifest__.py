# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['bus', 'web', 'portal'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/public_readonly_spreadsheet_templates.xml',
    ],
    'assets': {
        'web.chartjs_lib': [
            'spreadsheet/static/lib/chartjs-chart-geo/chartjs-chart-geo.js',
            'spreadsheet/static/lib/chart_js_treemap.js',
        ],
        'spreadsheet.o_spreadsheet_core': [
            'web/static/src/views/graph/graph_model.js',
            'web/static/src/views/pivot/pivot_model.js',
            'web/static/src/polyfills/clipboard.js',
            ('include', 'web.chartjs_lib'),
            'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
            'spreadsheet/static/src/**/*.js',
            # Load all o_spreadsheet templates first to allow to inherit them
            'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.xml',
            'spreadsheet/static/src/**/*.xml',
            ('remove', 'spreadsheet/static/src/assets_backend/**/*'),
            ('remove', 'spreadsheet/static/src/public_spreadsheet/**/*'),
        ],
        'spreadsheet.o_spreadsheet': [
            ('include', 'spreadsheet.o_spreadsheet_core'),
        ],
        'web.assets_web_print': [
            'spreadsheet/static/src/print_assets/**/*',
        ],
        'spreadsheet.public_spreadsheet': [
            ('include', 'web.assets_frontend'),
            ('include', 'spreadsheet.o_spreadsheet_core'),
            'web/static/src/model/**/*.js',
            'web/static/src/views/**/*.js',
            'web/static/src/search/**/*.js',
            'web/static/src/core/commands/command_hook.js',
            'web/static/src/webclient/menus/menu_helpers.js',
            ('remove', 'spreadsheet/static/src/ir_ui_menu/spreadsheet_link_service.js'),
            'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.css',
            'spreadsheet/static/src/**/*.scss',
            'spreadsheet/static/src/public_spreadsheet/**/*',
        ],
        'web.assets_backend': [
            'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.css',
            'spreadsheet/static/src/**/*.scss',
            'spreadsheet/static/src/assets_backend/**/*',
            ('remove', 'spreadsheet/static/src/print_assets/**/*'),
        ],
        'web.assets_unit_tests': [
            'spreadsheet/static/tests/**/*',
            ('include', 'spreadsheet.o_spreadsheet'),
        ],
    }
}
