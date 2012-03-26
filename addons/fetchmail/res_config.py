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

from osv import fields, osv

class project_configuration(osv.osv_memory):
    _inherit = 'project.config.settings'

    def get_default_email_configurations(self, cr, uid, ids, context=None):
        fetchmail_obj = self.pool.get('fetchmail.server')
        result = {}
        if not context:
            context = {}
        type = context.get('type')
        if type:
            server_ids = fetchmail_obj.search(cr, uid, [('name','=',type),('state','=','done')])
            if server_ids:
                result.update({'project_'+type: True})
                server_id = fetchmail_obj.browse(cr, uid, server_ids[0])
                result.update({type+'_server': server_id.server})
                result.update({type+'_port': server_id.port})
                result.update({type+'_is_ssl': server_id.is_ssl})
                result.update({type+'_type': server_id.type})
                result.update({type+'_user': server_id.user})
                result.update({type+'_password': server_id.password})

        return result

    def set_email_configurations(self, cr, uid, ids, context=None):
        model_obj = self.pool.get('ir.model')
        fetchmail_obj = self.pool.get('fetchmail.server')
        ir_values_obj = self.pool.get('ir.values')
        if not context:
            context = {}
        type = context.get('type')
        model = context.get('obj')
        if type and model:
            object_id = model_obj.search(cr, uid, [('model','=',model)])
            vals = self.read(cr, uid, ids[0], [], context=context)
            if vals.get('project_'+type) and object_id:
                server_vals = {
                        'name': type,
                        'object_id': object_id[0],
                        'server': vals.get(type+'_server'),
                        'port': vals.get(type+'_port'),
                        'is_ssl': vals.get(type+'_is_ssl'),
                        'type': vals.get(type+'_type'),
                        'user': vals.get(type+'_user'),
                        'password': vals.get(type+'_password')
                }
                server_ids = fetchmail_obj.search(cr, uid, [('name','=',type),('state','!=','done')])
                if not server_ids:
                    server_ids = [fetchmail_obj.create(cr, uid, server_vals, context=context)]
                else:
                    server_ids = fetchmail_obj.search(cr, uid, [('name','=',type)], context=context)
                    fetchmail_obj.write(cr, uid, server_ids, server_vals, context=context)
                fetchmail_obj.button_confirm_login(cr, uid, server_ids, context=None)

            else:
                server_ids = fetchmail_obj.search(cr, uid, [('name','=',type),('state','=','done')])
                fetchmail_obj.set_draft(cr, uid, server_ids, context=None)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
