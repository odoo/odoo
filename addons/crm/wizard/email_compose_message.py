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
    _inherit = 'email.compose.message'

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        model = ['crm.lead', 'crm.claim', 'crm.fundraising', 'crm.helpdesk', 'event.registration', 'hr.applicant', 'project.issue']
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)
        if context.get('record_id',False) and context.get('model',False) and context.get('model') in model:
            model_obj = self.pool.get(context.get('model'))
            data = model_obj.browse(cr, uid ,context.get('record_id'), context)
            if 'name' in fields:
                result['name'] = data.name

            if 'email_to' in fields:
                result['email_to'] = data.email_from

            if 'email_from' in fields:
                result['email_from'] = data.user_id and data.user_id.address_id and data.user_id.address_id.email

            if 'description' in fields:
                result['description'] = '\n' + (tools.ustr(data.user_id.signature or ''))

            if 'model' in fields:
                result['model'] = context.get('model','')

            if 'email_cc' in fields:
                result['email_cc'] = tools.ustr(data.email_cc or '')

            if 'res_id' in fields:
                result['res_id'] = context.get('record_id',0)

            if 'reply_to' in fields and hasattr(data, 'section_id'):
                result['reply_to'] = data.section_id and data.section_id.reply_to or False

        return result

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
