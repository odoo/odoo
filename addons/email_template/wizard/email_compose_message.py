# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv
from osv import fields
import tools
from tools.translate import _
import binascii

class email_compose_message(osv.osv_memory):
    _name = 'email.compose.message'
    _inherit = 'email.compose.message'

    def _get_templates(self, cr, uid, context=None):
        """
        Return Email Template of particular  Model.
        """
        if context is None:
            context = {}
        record_ids = []
        email_temp_pool = self.pool.get('email.template')
        model = False
        if context.get('message_id'):
            message_pool = self.pool.get('email.message')
            message_data = message_pool.browse(cr, uid, int(context.get('message_id')), context)
            model = message_data.model
        elif context.get('active_model',False):
            model =  context.get('active_model')
        if model:
            record_ids = email_temp_pool.search(cr, uid, [('model','=',model)])
            return email_temp_pool.name_get(cr, uid, record_ids, context) + [(False,'')]
        return []

    _columns = {
        'template_id': fields.selection(_get_templates, 'Template'),
    }

    def get_template_value(self, cr, uid, message, model, resource_id, context=None):
        template_pool = self.pool.get('email.template')
        return template_pool.get_template_value(cr, uid, message, model, resource_id, context)

    def on_change_template(self, cr, uid, ids, template_id, context=None):
        if context is None:
            context = {}
        att_ids = []
        res_id = context.get('active_id', False)
        values = self.pool.get('email.template').generate_email(cr, uid, template_id, res_id, context=context)
        if values['attachment']:
            attachment = values['attachment']
            attachment_obj = self.pool.get('ir.attachment')
            for fname, fcontent in attachment.items():
                data_attach = {
                    'name': fname,
                    'datas': binascii.b2a_base64(str(fcontent)),
                    'datas_fname': fname,
                    'description': _('Mail attachment'),
                    'res_model' : self._name,
                    'res_id' : ids and ids[0] or False
                }
                att_ids.append(attachment_obj.create(cr, uid, data_attach))
            values['attachment_ids'] = att_ids
        return {'value': values}

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
