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
    'name': 'Calendar',
    'version': '1.0',
    'depends': ['base', 'base_status', 'mail', 'base_action_rule'],
    'summary': 'Personal & Shared Calendar',
    'description': """
This is a full-featured calendar system.
========================================

It supports:
------------
    - Calendar of events
    - Recurring events

If you need to manage your meetings, you should install the CRM module.
    """,
    'author': 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'website': 'http://www.openerp.com',
    'demo': ['crm_meeting_demo.xml'],
    'data': [
        'security/calendar_security.xml',
        'security/ir.model.access.csv',
        'base_calendar_view.xml',
        'crm_meeting_view.xml',
        'base_calendar_data.xml',
        'crm_meeting_data.xml',
    ],
    'test' : ['test/base_calendar_test.yml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['images/base_calendar1.jpeg','images/base_calendar2.jpeg','images/base_calendar3.jpeg','images/base_calendar4.jpeg',],
}
