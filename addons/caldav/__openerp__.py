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
    "name" : "Share Calendar using CalDAV",
    "version" : "1.1",
    "depends" : [
                    "base",
                    "document_webdav",
                ],
     'description': """
This module contains basic functionality for Caldav system.
===========================================================

  - Webdav server that provides remote access to calendar
  - Synchronisation of calendar using WebDAV
  - Customize calendar event and todo attribute with any of OpenERP model
  - Provides iCal Import/Export functionality

To access Calendars using CalDAV clients, point them to:
    http://HOSTNAME:PORT/webdav/DATABASE_NAME/calendars/users/USERNAME/c

To access OpenERP Calendar using WebCal to remote site use the URL like:
    http://HOSTNAME:PORT/webdav/DATABASE_NAME/Calendars/CALENDAR_NAME.ics

    Where,
        HOSTNAME: Host on which OpenERP server(With webdav) is running
        PORT : Port on which OpenERP server is running (By Default : 8069)
        DATABASE_NAME: Name of database on which OpenERP Calendar is created
        CALENDAR_NAME: Name of calendar to access
""",
    "author" : "OpenERP SA",
    'category': 'Generic Modules/Others',
    'website': 'http://www.openerp.com',
    "init_xml" : ["caldav_data.xml"],
    "demo_xml" : [],
    "update_xml" : [
                    'security/ir.model.access.csv',
                    'wizard/calendar_event_export_view.xml',
                    'wizard/calendar_event_import_view.xml',
                    'wizard/calendar_event_subscribe_view.xml',
                    'wizard/caldav_browse_view.xml',
                    'caldav_view.xml',
                    'caldav_setup.xml'
                    ],
    "installable" : True,
    "active" : False,
    "certificate" : "00924841426645403741",
    'images': ['images/calendar_collections.jpeg','images/calendars.jpeg','images/export_ics_file.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
