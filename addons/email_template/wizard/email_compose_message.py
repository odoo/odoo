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

class email_compose_message(osv.osv_memory):
    _name = 'email.compose.message'
    _inherit = 'email.compose.message'
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)
        template_pool = self.pool.get('email.template')
        model_pool = self.pool.get('ir.model')
        template_id = context.get('template_id', False)
        if template_id:
            template = template_pool.get_email_template(cr, uid, template_id=template_id, context=context)
            def _get_template_value(field):
                if not template:
                    return False
                if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets original template values for multiple email change
                    return getattr(template, field)
                else: # Simple Mail: Gets computed template values
                    return template_pool.get_template_value(cr, uid, getattr(template, field), template.model, context.get('email_res_id'), context)

            if 'template_id' in fields:
                result['template_id'] = template.id

            if 'smtp_server_id' in fields:
                result['smtp_server_id'] = template.smtp_server_id.id

            if 'attachment_ids' in fields:
                result['attachment_ids'] = template_pool.read(cr, uid, template.id, ['attachment_ids'])['attachment_ids']

            if 'model' in fields:
                result['model'] = context.get('email_model')

            if 'res_id' in fields:
                result['res_id'] = context.get('email_res_id')

            if 'email_to' in fields:
                result['email_to'] = _get_template_value('email_to')

            if 'email_cc' in fields:
                result['email_cc'] = _get_template_value('email_cc')

            if 'email_bcc' in fields:
                result['email_bcc'] = _get_template_value('email_bcc')

            if 'name' in fields:
                result['name'] = _get_template_value('subject')

            if 'description' in fields:
                result['description'] = _get_template_value('description')

            if 'reply_to' in fields:
                result['reply_to'] = _get_template_value('reply_to')

        return result

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
        elif context.get('email_model',False):
            model =  context.get('email_model')
        if model:
            record_ids = email_temp_pool.search(cr, uid, [('model','=',model)])
            return email_temp_pool.name_get(cr, uid, record_ids, context) + [(False,'')]
        return []

    _columns = {
        'template_id': fields.selection(_get_templates, 'Template'),
    }

    def on_change_template(self, cr, uid, ids, model, resource_id, template_id, context=None):
        if context is None:
            context = {}
        if context.get('mail') == 'reply':
            return {'value':{}}
        email_temp_previ_pool = self.pool.get('email_template.preview')
        result = self.on_change_referred_doc(cr, uid, [],  model, resource_id, context=context)
        vals = result.get('value',{})
        if template_id and resource_id:
            email_temp_pool = self.pool.get('email.template')
            email_temp_data = email_temp_pool.browse(cr, uid, template_id, context)
            vals.update({'smtp_server_id': email_temp_data.smtp_server_id and email_temp_data.smtp_server_id.id or False})
            context.update({'template_id': template_id})
            value = email_temp_previ_pool.on_change_ref(cr, uid, [], resource_id, context)
            vals.update(value.get('value',{}))
            vals.update({'name': value.get('value',{}).get('subject','')})
            vals.update({'attachment_ids' : email_temp_pool.read(cr, uid, template_id, ['attachment_ids'])['attachment_ids']})
        else:
            vals.update({'attachment_ids' : []})
        return {'value': vals}

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
