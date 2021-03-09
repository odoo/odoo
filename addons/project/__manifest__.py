# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project',
    'version': '1.1',
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
            # inside .
            'project/static/src/css/project.css',
            # inside .
            'project/static/src/js/project_form.js',
            # inside .
            'project/static/src/js/project_kanban.js',
            # inside .
            'project/static/src/js/project_list.js',
            # inside .
            'project/static/src/js/project_rating_reporting.js',
            # inside .
            'project/static/src/js/project_task_kanban_examples.js',
            # inside .
            'project/static/src/js/tours/project.js',
            # inside .
            'project/static/src/js/project_calendar.js',
            # inside .
            'project/static/src/scss/project_dashboard.scss',
        ],
        'web.assets_frontend': [
            # inside .
            'project/static/src/scss/portal_rating.scss',
            # inside .
            'project/static/src/js/portal_rating.js',
        ],
        'web.assets_qweb': [
            'project/static/src/xml/project_templates.xml',
        ],
    }
}
