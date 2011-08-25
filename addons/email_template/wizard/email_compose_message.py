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
from tools.translate import _
import base64

class mail_compose_message(osv.osv_memory):
    _inherit = 'mail.compose.message'

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
            mail_message = self.pool.get('mail.message')
            message_data = mail_message.browse(cr, uid, int(context.get('message_id')), context)
            model = message_data.model
        elif context.get('active_model', False):
            model = context.get('active_model')
        if model:
            record_ids = email_temp_pool.search(cr, uid, [('model', '=', model)])
            return email_temp_pool.name_get(cr, uid, record_ids, context) + [(False,'')]
        return []

    _columns = {
        'template_id': fields.selection(_get_templates, 'Template'),
    }

    def on_change_template(self, cr, uid, ids, template_id, context=None):
        if context is None:
            context = {}
        att_ids = []
        values = {}
        if template_id:
            res_id = context.get('active_id', False)
            values = self.pool.get('email.template').generate_email(cr, uid, template_id, res_id, context=context)
            if values['attachments']:
                attachment = values.pop('attachments')
                attachment_obj = self.pool.get('ir.attachment')
                for fname, fcontent in attachment.iteritems():
                    data_attach = {
                        'name': fname,
                        'datas': base64.b64_encode(fcontent),
                        'datas_fname': fname,
                        'description': fname,
                        'res_model' : self._name,
                        'res_id' : ids[0] if ids else False
                    }
                    att_ids.append(attachment_obj.create(cr, uid, data_attach))
                values['attachment_ids'] = att_ids
        return {'value': values}

    def save_as_template(self, cr, uid, ids, context=None):
        '''
        create a new template record
        '''
        if context is None:
            context = {}
        template_pool = self.pool.get('email.template')
        model_pool = self.pool.get('ir.model')
        for record in self.browse(cr, uid, ids, context=context):
            model = context.get('active_model', record.model or False)
            model = model_pool.search(cr, uid, [('model', '=', model)])[0]
            model_name = model_pool.browse(cr, uid, model, context=context).name
            values = {
                'name': model_name,
                'email_from': record.email_from or False,
                'subject': record.subject or False,
                'body': record.body or False,
                'email_to': record.email_to or False,
                'email_cc': record.email_cc or False,
                'email_bcc': record.email_bcc or False,
                'reply_to': record.reply_to or False,
                'auto_delete': record.auto_delete,
                'model_id': model or False,
                'smtp_server_id': record.smtp_server_id.id or False,
                'attachment_ids': [(6, 0, [att.id for att in record.attachment_ids])]
            }
            template_pool.create(cr, uid, values, context=context)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
