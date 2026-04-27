# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Marketing Automation",
    'version': "1.0",
    'summary': "Build automated mailing campaigns",
    'website': 'https://www.odoo.com/app/marketing-automation',
    'category': "Marketing/Marketing Automation",
    'sequence': 195,
    'depends': ['mass_mailing'],
    'data': [
        'security/marketing_automation_security.xml',
        'security/ir.model.access.csv',
        'views/ir_actions_views.xml',
        'views/ir_model_views.xml',
        'views/marketing_automation_menus.xml',
        'wizard/marketing_campaign_test_views.xml',
        'views/link_tracker_views.xml',
        'views/mailing_mailing_views.xml',
        'views/mailing_trace_views.xml',
        'views/marketing_activity_views.xml',
        'views/marketing_participant_views.xml',
        'views/marketing_trace_views.xml',
        'views/marketing_campaign_views.xml',
        'data/ir_cron_data.xml',
        'data/marketing_activity_data_templates.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web._assets_primary_variables': [
            'marketing_automation/static/src/scss/variables.scss',
        ],
        'web.assets_backend': [
            'marketing_automation/static/src/js/**/*.js',
            'marketing_automation/static/src/js/*.js',
            'marketing_automation/static/src/scss/*.scss',
            'marketing_automation/static/src/xml/*.xml',
            'marketing_automation/static/src/components/**/*',

            # Don't include dark mode files in light mode
            ('remove', 'marketing_automation/static/src/scss/*.dark.scss'),
        ],
        "web.assets_web_dark": [
            'marketing_automation/static/src/scss/*.dark.scss',
        ],
        'web.qunit_suite_tests': [
            'marketing_automation/static/tests/hierarchy_kanban_tests.js',
        ],
        'web.assets_unit_tests': [
            'marketing_automation/static/tests/campaign_picker.test.js'
        ],
    }
}
