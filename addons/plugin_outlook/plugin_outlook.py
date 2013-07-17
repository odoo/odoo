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

from openerp.osv import fields
from openerp.osv import osv
from openerp import addons
import base64

class outlook_installer(osv.osv_memory):
    _name = 'outlook.installer'
    _inherit = 'res.config.installer'
    _columns = {
        'plugin32': fields.char('Outlook Plug-in 32bits', size=256, readonly=True, help="Outlook plug-in file. Save this file and install it in Outlook."),
        'plugin64': fields.char('Outlook Plug-in 64bits', size=256, readonly=True, help="Outlook plug-in file. Save this file and install it in Outlook."),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(outlook_installer, self).default_get(cr, uid, fields, context)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        res['plugin32'] = base_url + '/plugin_outlook/static/openerp-outlook-plugin/OpenERPOutlookPluginSetup32.msi'
        res['plugin64'] = base_url + '/plugin_outlook/static/openerp-outlook-plugin/OpenERPOutlookPluginSetup64.msi'
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
