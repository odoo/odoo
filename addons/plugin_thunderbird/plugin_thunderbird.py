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

class plugin_thunderbird_installer(osv.osv_memory):
    _name = 'plugin_thunderbird.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'name':fields.char('File name', size=34),
        'pdf_name':fields.char('File name', size=64),
        'thunderbird':fields.boolean('Thunderbird Plug-in', help="Allows you to select an object that you would like to add to your email and its attachments."),
        'plugin_file':fields.char('Thunderbird Plug-in', size=256, readonly=True, help="Thunderbird plug-in file. Save as this file and install this plug-in in thunderbird."),
        'pdf_file':fields.char('Installation Manual', size=264, help="The documentation file :- how to install Thunderbird Plug-in.", readonly=True),
        'description':fields.text('Description', readonly=True)
    }
    def default_get(self, cr, uid, fields, context=None):
        res = {}
        plugin_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')  + '/plugin_thunderbird/static/openerp_plugin.xpi'
        description = """
Thunderbird plugin installation:
    1.  Save the Thunderbird plug-in.
    2.  From the Thunderbird menubar: Tools ­> Add-ons -> Screwdriver/Wrench Icon -> Install add-on from file...
    4.  Select the plug-in (the file named openerp_plugin.xpi).
    5.  Click "Install Now".
    6.  Restart Thunderbird.
    7.  From the Thunderbird menubar: OpenERP -> Configuration.
    8.  Configure your openerp server.
"""
        res['thunderbird'] = True,
        res['name'] = 'openerp_plugin.xpi'
        res['plugin_file'] = plugin_url
        res['pdf_file'] = 'http://doc.openerp.com/book/2/2_6_Comms/2_6_Comms_thunderbird.html',
        res['description'] = description
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: