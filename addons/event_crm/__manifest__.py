# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event CRM',
    'version': '1.0',
    'category': 'Marketing/Events',
    'website': 'https://www.odoo.com/app/events',
    'description': "Create leads from event registrations.",
    'depends': ['event', 'crm'],
    'data': [
        'security/event_crm_security.xml',
        'security/ir.model.access.csv',
        'data/crm_lead_merge_template.xml',
        'data/ir_action_data.xml',
        'data/ir_cron_data.xml',
        'views/crm_lead_views.xml',
        'views/event_registration_views.xml',
        'views/event_lead_rule_views.xml',
        'views/event_event_views.xml',
        'views/event_question_views.xml',
    ],
    'demo': [
        'data/event_crm_demo.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'event_crm/static/tests/tours/*.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
