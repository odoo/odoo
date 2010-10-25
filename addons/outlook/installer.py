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
from tools import config

import base64

class outlook_installer(osv.osv_memory):
    _name = 'outlook.installer'
    _inherit = 'res.config.installer'

    def default_get(self, cr, uid, fields, context={}):
        data = super(outlook_installer, self).default_get(cr, uid, fields, context)
        data['doc_file'] = 'http://doc.openerp.com/book/2/2_6_Comms/2_6_Comms_outlook.html'
        file = open(config['addons_path'] + "/outlook/plugin/openerp-outlook-plugin.zip", 'r')
        data['plugin_file'] = base64.encodestring(file.read())
        return data

    _columns = {
        'name':fields.char('File name', size=34),
        'doc_name':fields.char('File name', size=64),
        'outlook':fields.boolean('Outlook Plug-in ', help="Allows you to select an object that you’d like to add to your email and its attachments."),
        'plugin_file':fields.binary('Outlook Plug-in', readonly=True, help="outlook plug-in file. Save as this file and install this plug-in in outlook."),
        'doc_file':fields.char('Installation Manual',size="264",help="The documentation file :- how to install Outlook Plug-in.", readonly=True),
        'description':fields.text('Description', readonly=True)
        }

    _defaults = {
        'outlook' : True,
        'name' : 'OpenERP-Outlook-PlugIn.zip',
        'doc_name' : 'Installation Guide to OpenERP Outlook Plug-in.doc',
        'description' : """
* Save the Outlook plug­-in.
* Follows these steps to install outlook plug­in.
Pre-requirements :
    1. Python 2.6+ .
    2. Python for Windows extensions - PyWin32 this module for python must be installed for appropriate version of the Python.
    3. If you are using MS Outlook 2007 than you are required to install "Microsoft Exchange Server MAPI Client and Collaboration Data Objects 1.2.1 (CDO 1.21)".

How to install openerp-outlook plug-in?
    1. Extract zip file  “openerp-outlook-plugin.zip” .
    2. Open the folder openerp-outlook-plugin.
    3. Run “Register-plugin.bat” file.
    4. Run Outlook and Check addon has been registered.
    5. Tools->OpenERP Configuration and test your connection.
    6. See User Guide for more information.
    7. Keep All extratced files in some safe places
        (e.g. python installation Directory "C:\pythonXX\" or Windows installation Directory "C:\Program Files\"  ).

Note :
    Please refer README file for dependecies external link, openobject-addons/outlook/README.
"""
        }
outlook_installer()
