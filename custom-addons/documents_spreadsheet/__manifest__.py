# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Documents Spreadsheet",
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Documents Spreadsheet',
    'description': 'Documents Spreadsheet',
    'depends': ['documents', 'spreadsheet_edition'],
    'data': [
        'data/documents_folder_data.xml',
        'data/res_company_data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/documents_document_views.xml',
        'views/spreadsheet_template_views.xml',
        'views/documents_templates_share.xml',
        'views/sharing_templates.xml',
        'views/res_config_settings_views.xml',
        'wizard/save_spreadsheet_template.xml',
    ],
    'demo': [
        'demo/documents_document_demo.xml'
    ],

    'installable': True,
    'auto_install': ['documents'],
    'license': 'OEEL-1',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'documents_spreadsheet/static/src/bundle/**/*.js',
            'documents_spreadsheet/static/src/bundle/**/*.xml',
            ('remove', 'documents_spreadsheet/static/src/bundle/components/control_panel/spreadsheet_breadcrumbs.xml'),
        ],
        'web.assets_backend': [
            'documents_spreadsheet/static/src/bundle/**/*.scss',
            'documents_spreadsheet/static/src/documents_view/**/*',
            'documents_spreadsheet/static/src/spreadsheet_clone_xlsx_dialog/**/*',
            'documents_spreadsheet/static/src/spreadsheet_selector_dialog/**/*',
            'documents_spreadsheet/static/src/spreadsheet_template/**/*',
            'documents_spreadsheet/static/src/helpers.js',
            'documents_spreadsheet/static/src/spreadsheet_action_loader.js',
            'documents_spreadsheet/static/src/view_insertion.js',
            'documents_spreadsheet/static/src/bundle/components/control_panel/spreadsheet_breadcrumbs.xml',
        ],
        'web.assets_tests': [
            'documents_spreadsheet/static/tests/utils/tour.js',
            'documents_spreadsheet/static/tests/tours/*',
        ],
        'web.qunit_suite_tests': [
            'documents_spreadsheet/static/tests/**/*',
        ]
    }
}
