# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Event',
    'version': '0.1',
    'category': 'Generic Modules/Association',
    'description': """Organization and management of events.

    This module allow you
        * to manage your events and their registrations
        * to use emails to automatically confirm and send acknowledgements for any registration to an event
        * ...

    Note that:
    - You can define new types of events in
                Events / Configuration / Types of Events
    - You can access predefined reports about number of registration per event or per event category in :
                Events / Reporting
""",
    'author': 'Tiny',
    'depends': ['crm', 'base_contact', 'account'],
    'init_xml': ['event_data.xml'],
    'update_xml': [
        'event_wizard.xml',
        'event_view.xml',
        'event_sequence.xml',
        'security/event_security.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': ['event_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0083059161581',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
