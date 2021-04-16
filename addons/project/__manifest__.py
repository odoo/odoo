# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project',
    'version': '1.2',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Services/Project',
    'sequence': 45,
    'summary': 'Organize and plan your projects',
    'depends': [
        'analytic',
        'base_setup',
        'mail',
        'portal',
        'rating',
        'resource',
        'web',
        'web_tour',
        'digest',
    ],
    'description': "",
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'report/project_report_views.xml',
        'report/project_task_burndown_chart_report_views.xml',
        'views/analytic_views.xml',
        'views/digest_views.xml',
        'views/rating_views.xml',
        'views/project_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/mail_activity_views.xml',
        'views/project_portal_templates.xml',
        'data/ir_cron_data.xml',
        'data/mail_data.xml',
        'data/mail_template_data.xml',
        'wizard/project_delete_wizard_views.xml',
        'wizard/project_task_type_delete_views.xml',
    ],
    'demo': ['data/project_demo.xml'],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'project/static/src/css/project.css',
            'project/static/src/js/project_form.js',
            'project/static/src/js/project_kanban.js',
            'project/static/src/js/project_list.js',
            'project/static/src/js/project_rating_reporting.js',
            'project/static/src/js/project_name_with_subtask_count_widget.js',
            'project/static/src/js/project_task_kanban_examples.js',
            'project/static/src/js/tours/project.js',
            'project/static/src/js/project_calendar.js',
            'project/static/src/js/burndown_chart/*',
            'project/static/src/models/message/message.js',
            'project/static/src/scss/project_dashboard.scss',
            'project/static/src/scss/project_form.scss',
        ],
        'web.assets_frontend': [
            'project/static/src/scss/portal_rating.scss',
            'project/static/src/js/portal_rating.js',
        ],
        'web.assets_qweb': [
            'project/static/src/xml/**/*',
            'project/static/src/components/thread_needaction_preview/thread_needaction_preview.xml',
            'project/static/src/components/thread_preview/thread_preview.xml',
        ],
        'web.qunit_suite_tests': [
            'project/static/tests/burndown_chart_tests.js',
        ]
    }
}
