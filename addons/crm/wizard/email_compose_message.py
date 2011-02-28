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

email_model = [
        'crm.lead',
    ]

class email_compose_message(osv.osv_memory):
    _inherit = 'email.compose.message'

    def get_value(self, cr, uid, model, resource_id, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).get_value(cr, uid,  model, resource_id, context=context)
        if model not in email_model:
            return result
        model_obj = self.pool.get(context.get('email_model'))
        data = model_obj.browse(cr, uid , resource_id, context)
        result.update({
                'name' : data.name,
                'email_to' : data.email_from,
                'email_from' : data.user_id and data.user_id.address_id and data.user_id.address_id.email or False,
                'description' : '\n' + (tools.ustr(data.user_id.signature or '')),
                'email_cc' : tools.ustr(data.email_cc or '')
            })
        if hasattr(data, 'section_id'):
            result.update({'reply_to' : data.section_id and data.section_id.reply_to or False})
        return result

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id',False) and context.get('email_model',False) and context.get('email_model') in email_model:
            vals = self.get_value(cr, uid, context.get('email_model'), context.get('active_id'), context)
            if 'name' in fields:
                result.update({'name' : vals.get('name','')})

            if 'email_to' in fields:
                result.update({'email_to' : vals.get('email_to','')})

            if 'email_from' in fields:
                result.update({'email_from' : vals.get('email_from','')})

            if 'description' in fields:
                result.update({'description' : vals.get('description','')})

            if 'model' in fields:
                result['model'] = context.get('email_model','')

            if 'email_cc' in fields:
                result.update({'email_cc' : vals.get('email_cc','')})

            if 'res_id' in fields:
                result['res_id'] = context.get('active_id',0)

            if 'reply_to' in fields:
                result['reply_to'] = vals.get('reply_to','')

        return result

    def on_change_referred_doc(self, cr, uid, ids, model, resource_id, context=None):
        if context is None:
            context = {}
        if context.get('mail') == 'reply':
            return {'value':{}}
        result = super(email_compose_message, self).on_change_referred_doc(cr, uid, ids, model, resource_id, context=context)
        value = {}
        if not result.get('value'):
            result.update({'value':{}})
        if resource_id and model in email_model:
            vals = self.get_value(cr, uid, model, resource_id, context)
            result['value'].update({
                        'email_from':  vals.get('email_from',''),
                        'email_to':  vals.get('email_to',''),
                        'name':  vals.get('name',''),
                        'description':  vals.get('description',''),
                        'email_cc':  vals.get('email_cc',''),
                        'email_bcc':  vals.get('email_bcc',''),
                        'reply_to':  vals.get('reply_to',''),
                    })
        return result

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
