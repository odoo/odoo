
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Events Organisation',
    'version': '0.1',
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
    'depends': ['base_setup', 'board', 'email_template'],
    'data': [
        'security/event_security.xml',
        'security/ir.model.access.csv',
        'wizard/event_confirm_view.xml',
        'event_view.xml',
        'event_data.xml',
        'report/report_event_registration_view.xml',
        'board_association_view.xml',
        'res_partner_view.xml',
        'email_template.xml',
    ],
    'demo': ['event_demo.xml'],
    'test': ['test/process/event_draft2done.yml'],
    'css': ['static/src/css/event.css'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['images/1_event_type_list.jpeg','images/2_events.jpeg','images/3_registrations.jpeg','images/events_kanban.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
