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

class email_compose_message(osv.osv_memory):
    _name = 'email.compose.message'
    _inherit = 'email.compose.message'

    def get_template_data(self, cr, uid, res_id, template_id, context=None):
        if context is None:
            context = {}
        result = {}
        template_pool = self.pool.get('email.template')
        if template_id:
            template = template_pool.get_email_template(cr, uid, template_id=template_id, context=context)
            def _get_template_value(field):
                if not template:
                    return False
                if len(context.get('src_rec_ids',[])) > 1: # Multiple Mail: Gets original template values for multiple email change
                    return getattr(template, field)
                else: # Simple Mail: Gets computed template values
                    return template_pool.get_template_value(cr, uid, getattr(template, field), template.model, context.get('active_id'), context)
            result.update({
                    'template_id' : template.id,
                    'smtp_server_id' : template.smtp_server_id.id,
                    'body' : _get_template_value('body') or False,
                    'subject' : _get_template_value('subject') or False,
                    'attachment_ids' : template_pool.read(cr, uid, template.id, ['attachment_ids'])['attachment_ids'] or [],
                    'res_id' : res_id or False,
                    'email_to' : _get_template_value('email_to') or False,
                    'email_cc' : _get_template_value('email_cc') or False,
                    'email_bcc' : _get_template_value('email_bcc') or False,
                    'reply_to' : _get_template_value('reply_to') or False,
                    'model' : template.model or False,
                })
        return result

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)
        template_id = context.get('template_id', False)
        vals = {}
        if template_id and context.get('active_model') and context.get('active_id'):
            vals = self.get_template_data(cr, uid, context.get('active_id'), template_id, context)

        if not vals:
            return result

        if 'template_id' in fields:
            result.update({'template_id' : vals.get('template_id', False)})

        if 'smtp_server_id' in fields:
            result.update({'smtp_server_id' : vals.get('smtp_server_id', False)})

        if 'attachment_ids' in fields:
            result.update({'attachment_ids' : vals.get('attachment_ids', False)})

        if 'model' in fields:
            result.update({'model' : vals.get('model', False)})

        if 'res_id' in fields:
            result.update({'res_id' : vals.get('res_id', False)})

        if 'email_to' in fields:
            result.update({'email_to' : vals.get('email_to', False)})

        if 'email_cc' in fields:
            result.update({'email_cc' : vals.get('email_cc', False)})

        if 'email_bcc' in fields:
            result.update({'email_bcc' : vals.get('email_bcc', False)})

        if 'subject' in fields:
            result.update({'subject' : vals.get('name', False)})

        if 'body' in fields:
            result.update({'body' : vals.get('body', False)})

        if 'reply_to' in fields:
            result.update({'reply_to' : vals.get('reply_to', False)})

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
        elif context.get('active_model',False):
            model =  context.get('active_model')
        if model:
            record_ids = email_temp_pool.search(cr, uid, [('model','=',model)])
            return email_temp_pool.name_get(cr, uid, record_ids, context) + [(False,'')]
        return []

    _columns = {
        'template_id': fields.selection(_get_templates, 'Template'),
    }

    def on_change_template(self, cr, uid, ids, model, template_id, context=None):
        if context is None:
            context = {}
        if context.get('mail') == 'reply':
            return {'value':{}}
        vals = {}
        resource_id = context.get('active_id', False)
        if template_id and resource_id:
            vals.update(self.get_template_data(cr, uid, resource_id, template_id, context))
        else:
            vals.update({'attachment_ids' : []})

        email_temp_pool = self.pool.get('email.template')
        template_data = email_temp_pool.browse(cr, uid, template_id, context=context)
        vals.update({'auto_delete': template_data.auto_delete})
        if context.get('active_model') and context.get('active_id') and template_data.user_signature:
            model_pool = self.pool.get(context['active_model'])
            user = model_pool.browse(cr, uid, context['active_id'], context=context).user_id
            signature = user and user.signature or ''
            vals['body'] = vals['body'] + '\n' + signature
        return {'value': vals}

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
