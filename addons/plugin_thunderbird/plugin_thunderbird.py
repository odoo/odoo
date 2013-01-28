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

from openerp.osv import fields, osv

class plugin_thunderbird_installer(osv.osv_memory):
    _name = 'plugin_thunderbird.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'thunderbird': fields.boolean('Thunderbird Plug-in', help="Allows you to select an object that you would like to add to your email and its attachments."),
        'plugin_name': fields.char('File name', size=64),
        'plugin_file': fields.char('Thunderbird Plug-in', size=256, readonly=True, help="Thunderbird plug-in file. Save this file and install it in Thunderbird."),
    }

    _defaults = {
        'thunderbird': True,
        'plugin_name': 'openerp_plugin.xpi',
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(plugin_thunderbird_installer, self).default_get(cr, uid, fields, context)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        res['plugin_file'] = base_url + '/plugin_thunderbird/static/openerp_plugin.xpi'
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
