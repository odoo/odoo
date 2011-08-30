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

from osv import fields
from osv import osv
import addons

import base64

class outlook_installer(osv.osv_memory):
    _name = 'outlook.installer'
    _inherit = 'res.config.installer'

    def default_get(self, cr, uid, fields, context=None):
        data = super(outlook_installer, self).default_get(cr, uid, fields, context=context)
        data['doc_file'] = 'http://doc.openerp.com/v6.0/book/2/3_CRM_Contacts/communicate.html#managing-your-crm-from-microsoft-outlook'
        file = open(addons.get_module_resource('outlook','plugin','openerp-outlook-addin.exe'), 'r')
        data['plugin_file'] = base64.encodestring(file.read())
        return data

    _columns = {
        'name':fields.char('File name', size=34),
        'doc_name':fields.char('File name', size=64),
        'outlook':fields.boolean('Outlook Plug-in ', help="Allows you to select an object that you would like to add to your email and its attachments."),
        'plugin_file':fields.binary('Outlook Plug-in', readonly=True, help="outlook plug-in file. Save as this file and install this plug-in in outlook."),
        'doc_file':fields.char('Installation Manual',size="264",help="The documentation file :- how to install Outlook Plug-in.", readonly=True),
        'description':fields.text('Description', readonly=True)
        }

    _defaults = {
        'outlook' : True,
        'name' : 'Openerp-Outlook-Addin.exe',
        'doc_name' : 'Installation Guide to OpenERP Outlook Plug-in.doc',
        'description' : """
* Save the Outlook plug­-in.
* Follows these steps to install outlook plug­in.
Pre-requirements :
    1. Python 2.6+ .
    2. Python for Windows extensions - PyWin32 this module for python must be installed for appropriate version of the Python.
    3.1 If With MS Outlook 2007 it is required to install externally "Collaboration Data Objects, version 1.2.1".
          http://www.microsoft.com/downloads/en/details.aspx?FamilyId=2714320D-C997-4DE1-986F-24F081725D36&displaylang=en
    3.2 With MS Outlook2003 Install inbuilt Collaboration Data Objects(CDO) while installing Outlook.

How to install openerp-outlook plug-in?
    1. Save the executable plug-in file.
    2. Close Outlook Application if Running.
    3. Run executable plug-in file and the folllow the instruction.

Note :
    Please refer README file for dependecies external link, openobject-addons/outlook/README.
"""
        }
outlook_installer()
