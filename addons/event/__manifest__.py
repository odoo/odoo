# -*- coding: utf-8 -*-
{
    'name': 'Events Organization',
    'version': '1.3',
    'website': 'https://www.odoo.com/page/events',
    'category': 'Marketing/Events',
    'summary': 'Trainings, Conferences, Meetings, Exhibitions, Registrations',
    'description': """
Organization and management of Events.
======================================

The event module allows you to efficiently organize events and all related tasks: planning, registration tracking,
attendances, etc.

Key Features
------------
* Manage your Events and Registrations
* Use emails to automatically confirm and send acknowledgments for any event registration
""",
    'depends': ['base_setup', 'mail', 'portal', 'utm'],
    'data': [
        'security/event_security.xml',
        'security/ir.model.access.csv',
        'views/event_menu_views.xml',
        'views/event_ticket_views.xml',
        'views/event_views.xml',
        'views/event_stage_views.xml',
        'report/event_event_templates.xml',
        'report/event_event_reports.xml',
        'data/email_template_data.xml',
        'data/event_data.xml',
        'views/res_config_settings_views.xml',
        'views/event_templates.xml',
        'views/res_partner_views.xml',
        'views/event_tag_views.xml'
    ],
    'demo': [
        'data/res_users_demo.xml',
        'data/res_partner_demo.xml',
        'data/event_demo_misc.xml',
        'data/event_demo.xml',
        'data/event_registration_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
