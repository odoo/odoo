# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
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
    'depends': ['base', 'mail', 'base_action_rule', 'web_calendar'],
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
    'website': 'https://www.odoo.com/page/crm',
    'demo': ['calendar_demo.xml'],
    'data': [
        'calendar_cron.xml',
        'security/ir.model.access.csv',
        'security/calendar_security.xml',
        'calendar_view.xml',
        'calendar_data.xml',
        'views/calendar.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'test': [
        'test/calendar_test.yml',
        'test/test_calendar_recurrent_event_case2.yml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
