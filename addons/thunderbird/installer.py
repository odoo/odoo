# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class thunderbird_installer(osv.osv_memory):
    _name = 'thunderbird.installer'
    _inherit = 'res.config.installer'

    def default_get(self, cr, uid, fields, context={}):
        data = super(thunderbird_installer, self).default_get(cr, uid, fields, context)
        pdf_file = open(config['addons_path'] + "/thunderbird/doc/Installation Guide to OpenERP Thunderbid Plug-in.pdf", 'r')
        data['pdf_file'] = base64.encodestring(pdf_file.read())
        file = open(config['addons_path'] + "/thunderbird/plugin/tiny_plugin-2.0.xpi", 'r')
        data['plugin_file'] = base64.encodestring(file.read())
        return data

    _columns = {
        'name':fields.char('File name', size=34),
        'pdf_name':fields.char('File name', size=64),
        'thunderbird':fields.boolean('Thunderbird Module ', help="Allows you to select an object that you’d like to add to your email and its attachments."),
        'plugin_file':fields.binary('Thunderbird Plug-in', readonly=True, help="Thunderbird plug-in file. Save as this file and install this plug-in in thunderbird."),
        'pdf_file':fields.binary('Installation Manual', help="The documentation file :- how to install Thunderbird Plug-in.", readonly=True),
        'description':fields.text('Description', readonly=True)
        }

    _defaults = {
        'thunderbird' : True,
        'name' : 'OpenERP_plugin-2.0.xpi',
        'pdf_name' : 'Installation Guide to OpenERP Thunderbid Plug-in.pdf',
        'description' : """ * Save the Thunderbird plug­in. \n * Follow the steps to install Thunderbird plug­in. \n -> 1.From Menu Bar of Thunderbird, open Tools ­> Addons. \n -> 2. Click on install button and a browser window appears. \n -> 3. Select the plug-in(.xpi file) and click Ok. \n -> 4. Software installation window appears and within a short time “Install Now” button will be enabled \n -> 5. Click "Install Now". \n -> 6. Restart Thunderbird. \n Follow the steps to configure OpenERP in Thunderbird. \n -> 1. Go to Tools > OpenERP Synchronization. \n -> 2. Check  data (configured by default) \n -> 3. Click Test  Connection. \n -> 4. A message appears with state of your connection. \n -> 5. If your connection failed, check if your database is open, and check your data. \n -> 6. If you have a good connection, click Ok and start to archive mail in OpenERP. """
        }

thunderbird_installer()
