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
        data['doc_file'] = 'http://doc.openerp.com/book/2/2_6_Comms/2_6_Comms_outlook.html'
        file = open(addons.get_module_resource('outlook','static','openerp-outlook-plugin','OpenERPOutlookPluginSetup','Release','OpenERPOutlookPluginSetup.msi'), 'r')
        data['plugin_file'] = base64.encodestring(file.read())
        return data

    _columns = {
        'name':fields.char('File name', size=34),
        'doc_name':fields.char('File name', size=64),
        'outlook':fields.boolean('Outlook Plug-in ', help="Allows you to select an object that you would like to add to your email and its attachments."),
        'plugin_file':fields.binary('Outlook Plug-in', readonly=True, help="outlook plug-in file. Save as this file and install this plug-in in outlook."),
        'doc_file':fields.char('Installation Manual',size=264,help="The documentation file :- how to install Outlook Plug-in.", readonly=True),
        'description':fields.text('Description', readonly=True)
        }

    _defaults = {
        'outlook' : True,
        'name' : 'OpenERPOutlookPlugin.msi',
        'doc_name' : 'Installation Guide to OpenERP Outlook Plug-in.doc',
        'description' : """
System requirements:
    1.  MS Outlook 2005 or above.
    2.  MS .Net Framework 3.5 .
    

Plugin installation:
    1.  Save the msi plug-in file.
    2.  Close the Outlook application if it is open.
    3.  Run the executable plug-in file (OpenERPOutlookPlugin.msi).
"""
        }
outlook_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
