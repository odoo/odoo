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
    "name": "CalDAV for task management",
    "version": "1.1",
    "author": "OpenERP SA",
    "category": "Project Management",
    "description": """ Synchronize between Project task and Caldav Vtodo.""",
    "depends": ["project", "caldav", "base_calendar"],
    "init_xml": ["project_caldav_data.xml", 'project_caldav_setup.xml', ],
    "demo_xml": [],
    "update_xml": ["project_caldav_view.xml"],
    "active": False,
    "website": "http://www.openerp.com",
    "installable": True,
    "certificate" : "001114200456808204637",
}
