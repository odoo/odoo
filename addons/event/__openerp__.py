# -*- coding: utf-8 -*-
{
    'name': 'Events Organisation',
    'version': '0.1',
    'website': 'https://www.odoo.com/page/events',
    'category': 'Tools',
    'summary': 'Trainings, Conferences, Meetings, Exhibitions, Registrations',
    'description': """
Organization and management of Events.
======================================

The event module allows you to efficiently organise events and all related tasks: planification, registration tracking,
attendances, etc.

Key Features
------------
* Manage your Events and Registrations
* Use emails to automatically confirm and send acknowledgements for any event registration
""",
    'author': 'OpenERP SA',
    'depends': ['base_setup', 'board', 'email_template', 'marketing'],
    'data': [
        'security/event_security.xml',
        'security/ir.model.access.csv',
        'wizard/event_confirm_view.xml',
        'report/report_event_registration_view.xml',
        'event_view.xml',
        'event_data.xml',
        'res_config_view.xml',
        'email_template.xml',
        'views/event.xml',
        'event_report.xml',
        'views/report_registrationbadge.xml',
    ],
    'demo': [
        'event_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'images': ['images/1_event_type_list.jpeg', 'images/2_events.jpeg', 'images/3_registrations.jpeg', 'images/events_kanban.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
