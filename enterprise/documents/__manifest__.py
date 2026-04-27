# -*- coding: utf-8 -*-
{
    'name': "Documents",

    'summary': "Collect, organize and share documents.",

    'description': """
App to upload and manage your documents.
    """,

    'category': 'Productivity/Documents',
    'sequence': 80,
    'version': '1.4',
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
        'data/documents_tag_data.xml',
        'data/documents_document_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/documents_tour.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/documents_access_views.xml',
        'views/documents_document_views.xml',
        'views/documents_folder_views.xml',
        'views/documents_tag_views.xml',
        'views/mail_activity_views.xml',
        'views/mail_activity_plan_views.xml',
        'views/mail_alias_views.xml',
        'views/documents_menu_views.xml',
        'views/documents_templates_portal.xml',
        'views/documents_templates_share.xml',
        'wizard/documents_link_to_record_wizard_views.xml',
        'wizard/documents_request_wizard_views.xml',
        # Need the `ir.actions.act_window` to exist
        'data/ir_actions_server_data.xml',
    ],

    'demo': [
        'demo/documents_document_demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'documents/static/src/model/**/*',
            'documents/static/src/scss/documents_views.scss',
            'documents/static/src/scss/documents_kanban_view.scss',
            'documents/static/src/attachments/**/*',
            'documents/static/src/core/**/*',
            'documents/static/src/js/**/*',
            'documents/static/src/mail/**/*',
            'documents/static/src/owl/**/*',
            'documents/static/src/utils.js',
            'documents/static/src/views/**/*',
            'documents/static/src/webclient/webclient.js',
            ('remove', 'documents/static/src/views/activity/**'),
            ('after', 'web/static/src/core/errors/error_dialogs.xml', 'documents/static/src/web/error_dialog/error_dialog_patch.xml'),
            'documents/static/src/web/**/*',
            'documents/static/src/components/**/*',
        ],
        'web.assets_backend_lazy': [
            'documents/static/src/views/activity/**',
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
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'documents/static/src/scss/documents_public_pages.scss',
        ],
        'documents.webclient': [
            ('include', 'web.assets_backend'),
            # documents webclient overrides
            'documents/static/src/portal_webclient/**/*',
            'web/static/src/start.js',
        ],
        'web.tests_assets': [
            'documents/static/tests/legacy/helpers/**/*',
        ],
        'web.assets_tests': [
            'documents/static/tests/tours/*',
        ],
        'web.assets_unit_tests': [
            'documents/static/tests/**/*',
            ('remove', 'documents/static/tests/legacy/**/*'),
        ],
        'web.qunit_suite_tests': [
            'documents/static/tests/legacy/**/*',
            ('remove', 'documents/static/tests/legacy/**/*mobile_tests.js'),
        ],
        'web.qunit_mobile_suite_tests': [
            'documents/static/tests/legacy/documents_test_utils.js',
            'documents/static/tests/legacy/documents_kanban_mobile_tests.js',
        ],
    }
}
