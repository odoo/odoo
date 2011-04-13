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

    def get_template_data(self, cr, uid, template_id, context=None):
        result = {}
        if not template_id: 
            return result
        if context is None:
            context = {}

        template_pool = self.pool.get('email.template')
        resource_id = context.get('active_id')
        template = template_pool.get_email_template(cr, uid, template_id=template_id, context=context)

        def _get_template_value(field):
            if context.get('mass_mail',False): # Multiple Mail: Gets original template values for multiple email change
                return getattr(template, field)
            else
                return self.get_template_value(cr, uid, getattr(template, field), template.model, resource_id, context=context)


        result.update({
                'template_id' : template.id,
                'smtp_server_id' : template.smtp_server_id.id,
                'body' : _get_template_value('body') or False,
                'subject' : _get_template_value('subject') or False,
                'attachment_ids' : template_pool.read(cr, uid, template.id, ['attachment_ids'])['attachment_ids'] or [],
                'res_id' : resource_id or False,
                'email_to' : _get_template_value('email_to') or False,
                'email_cc' : _get_template_value('email_cc') or False,
                'email_bcc' : _get_template_value('email_bcc') or False,
                'reply_to' : _get_template_value('reply_to') or False,
                'model' : template.model or False,
            })
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

    def get_template_value(self, cr, uid, message, model, resource_id, context=None):
        template_pool = self.pool.get('email.template')
        return template_pool.get_template_value(cr, uid, message, model, resource_id, context)

    def on_change_template(self, cr, uid, template_id, context=None):
        if context is None:
            context = {}
        
        resource_id = context.get('active_id', False)
        
        return self.get_template_data(cr, uid, resource_id, template_id, context)

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
