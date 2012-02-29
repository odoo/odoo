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

from osv import fields, osv

class crm_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
        'crm_caldav' : fields.boolean("Use caldav to synchronize Meetings",
                                    help="Install crm_caldav module: Caldav features in Meeting"),
        'fetchmail_crm': fields.boolean("Lead/Opportunity mail gateway"),
        'server' : fields.char('Server Name', size=256),
        'port' : fields.integer('Port'),
        'type': fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type'),
        'is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'user' : fields.char('Username', size=256),
        'password' : fields.char('Password', size=1024),
    }
    
    _defaults = {
        'type': 'pop',
    }
    
    def get_default_email_configurations(self, cr, uid, ids, context=None):
        ir_values_obj = self.pool.get('ir.values')
        result = {}
        installed_modules = self.get_default_installed_modules(cr, uid, ids, context=context)
        if 'fetchmail_crm' in installed_modules.keys():
            for val in ir_values_obj.get(cr, uid, 'default', False, ['fetchmail.server']):
                result.update({val[1]: val[2]})
        return result
    
    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False):
        port = 0
        values = {}
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        else:
            values['server'] = ''
        values['port'] = port
        return {'value': values}
    
    def set_email_configurations(self, cr, uid, ids, vals, context=None):
        model_obj = self.pool.get('ir.model')
        fetchmail_obj = self.pool.get('fetchmail.server')
        ir_values_obj = self.pool.get('ir.values')
        if vals.get('fetchmail_crm'):
            object_id = model_obj.search(cr, uid, [('model','=','crm.lead')])[0]
            fetchmail_vals = {
                    'name': 'Incoming Leads',
                    'object_id': object_id,
                    'server': vals.get('server'),
                    'port': vals.get('port'),
                    'is_ssl': vals.get('is_ssl'),
                    'type': vals.get('type'),
                    'user': vals.get('user'),
                    'password': vals.get('password')
            }
            if not self.get_installed_modules(cr, uid, ['fetchmail_crm'], context):
                fetchmail_obj.create(cr, uid, fetchmail_vals, context=context)
            else:
                fetchmail_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads')], context=context)
                fetchmail_obj.write(cr, uid, fetchmail_ids, fetchmail_vals, context=context)
            ir_values_obj.set(cr, uid, 'default', False, 'server', ['fetchmail.server'], fetchmail_vals.get('server'))
            ir_values_obj.set(cr, uid, 'default', False, 'port', ['fetchmail.server'], fetchmail_vals.get('port'))
            ir_values_obj.set(cr, uid, 'default', False, 'is_ssl', ['fetchmail.server'], fetchmail_vals.get('is_ssl'))
            ir_values_obj.set(cr, uid, 'default', False, 'type', ['fetchmail.server'], fetchmail_vals.get('type'))
            ir_values_obj.set(cr, uid, 'default', False, 'user', ['fetchmail.server'], fetchmail_vals.get('user'))
            ir_values_obj.set(cr, uid, 'default', False, 'password', ['fetchmail.server'], fetchmail_vals.get('password'))

crm_configuration()