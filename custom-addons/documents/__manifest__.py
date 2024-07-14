# -*- coding: utf-8 -*-
{
    'name': "Documents",

    'summary': "Document management",

    'description': """
App to upload and manage your documents.
    """,

    'author': "Odoo",
    'category': 'Productivity/Documents',
    'sequence': 80,
    'version': '1.3',
    'application': True,
    'website': 'https://www.odoo.com/app/documents',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'portal', 'web_enterprise', 'attachment_indexation', 'digest'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'data/mail_template_data.xml',
        'data/mail_activity_type_data.xml',
        'data/documents_folder_data.xml',
        'data/documents_facet_data.xml',
        'data/documents_tag_data.xml',
        'data/documents_share_data.xml',
        'data/documents_document_data.xml',
        'data/documents_workflow_data.xml',
        'data/ir_asset_data.xml',
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/documents_document_views.xml',
        'views/documents_facet_views.xml',
        'views/documents_folder_views.xml',
        'views/documents_share_views.xml',
        'views/documents_tag_views.xml',
        'views/documents_workflow_action_views.xml',
        'views/documents_workflow_rule_views.xml',
        'views/mail_activity_views.xml',
        'views/mail_activity_plan_views.xml',
        'views/documents_menu_views.xml',
        'views/documents_templates_share.xml',
        'wizard/documents_link_to_record_wizard_views.xml',
        'wizard/documents_request_wizard_views.xml',
    ],

    'demo': [
        'demo/documents_folder_demo.xml',
        'demo/documents_document_demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'documents/static/src/scss/documents_views.scss',
            'documents/static/src/scss/documents_kanban_view.scss',
            'documents/static/src/attachments/**/*',
            'documents/static/src/core/**/*',
            'documents/static/src/js/**/*',
            'documents/static/src/owl/**/*',
            'documents/static/src/views/**/*',
            'documents/static/src/web/**/*',
        ],
        'web._assets_primary_variables': [
            'documents/static/src/scss/documents.variables.scss',
        ],
        "web.dark_mode_variables": [
            ('before', 'documents/static/src/scss/documents.variables.scss', 'documents/static/src/scss/documents.variables.dark.scss'),
        ],
        'documents.public_page_assets': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'documents/static/src/scss/documents_public_pages.scss',
        ],
        'documents.pdf_js_assets': [
            ('include', 'web.pdf_js_lib'),
        ],
        'web.tests_assets': [
            'documents/static/tests/helpers/**/*',
        ],
        'web.assets_tests': [
            'documents/static/tests/tours/*',
        ],
        'web.qunit_suite_tests': [
            'documents/static/tests/**/*',
            ('remove', 'documents/static/tests/**/*mobile_tests.js'),
            ('remove', 'documents/static/tests/helpers/**/*'),
            ('remove', 'documents/static/tests/tours/*'),
        ],
        'web.qunit_mobile_suite_tests': [
            'documents/static/tests/documents_test_utils.js',
            'documents/static/tests/documents_kanban_mobile_tests.js',
        ],
    }
}
