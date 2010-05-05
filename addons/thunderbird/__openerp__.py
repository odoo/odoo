# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (c) 2004 Axelor SPRL. (http://www.axelor.com) All Rights Reserved.
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
    "name" : "Thunderbird Interface",
    "version" : "1.0",
    "author" : "Axelor",
    "website" : "http://www.axelor.com/",
    "depends" : ["base","crm"],
    "category" : "Generic Modules/Thunderbird interface",
    "description": '''
      This module is required for the thuderbird plug-in to work
      properly.

      This allows you to select an object that you’d like to add
      to your email and its attachments. You can select a partner, a task,
      a project, an analytical account, or any other object and attach selected
      mail as .eml file in attachment of selected record.

      You can create new case in crm using Create Case button.
      Select a section for which you want to create case.''',
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ['thunderbird_installer.xml',
                    'security/ir.model.access.csv'],
    "active": False,
    "installable": True
}
