#!/usr/bin/env python
#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    mga@tinyerp.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    "name" : "Fetchmail Server",
    "version" : "1.0",
    "depends" : ["base", 'email'],
    "author" : "OpenERP SA",
    "description": """Fetchmail:
    * Fetch email from Pop / IMAP server
    * Support SSL
    * Integrated with all Modules
    * Automatic Email Receive
    * Email based Records (Add, Update)
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        "fetchmail_view.xml",
        "fetchmail_data.xml",
        'security/ir.model.access.csv',
    ],
    'demo_xml': [

    ],
    'installable': True,
    'active': False,
    'certificate' : '00692978332890137453',
}
