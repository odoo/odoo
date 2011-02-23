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

    def _get_templates(self, cr, uid, context=None):
        """
        Return Email Template of particular  Model.
        """
        if context is None:
            context = {}
        record_ids = []
        email_temp_pool = self.pool.get('email.template')
        model = False
        if context.get('email_model',False):
            model =  context.get('email_model')
        elif context.get('active_model',False):
            model =  context.get('active_model')
        if model:
            record_ids = email_temp_pool.search(cr, uid, [('model','=',model)])
            return email_temp_pool.name_get(cr, uid, record_ids, context)
        return []

    _columns = {
        'template_id': fields.selection(_get_templates, 'Template'),
    }

    def on_change_template(self, cr, uid, ids, model, resource_id, template_id, context=None):
        if context is None:
            context = {}
        email_temp_previ_pool = self.pool.get('email_template.preview')
        result = self.on_change_referred_doc(cr, uid, [],  model, resource_id, context=context)
        vals = result.get('value',{})
        if template_id and resource_id:
            context.update({'template_id': template_id})
            value = email_temp_previ_pool.on_change_ref(cr, uid, [], resource_id, context)
            new_value = value.get('value',{})
            if vals.get('email_from'):
                new_value.get('email_from') and new_value.update({'email_from': new_value.get('email_from') + ',' + vals.get('email_from')}) or vals.get('email_from')

            if vals.get('email_to'):
                new_value.update({'email_to': new_value.get('email_to') + ',' + vals.get('email_to')}) or vals.get('email_to')

            if vals.get('email_cc'):
                new_value.get('email_cc') and new_value.update({'email_cc': new_value.get('email_cc') + ',' + vals.get('email_cc')}) or vals.get('email_cc')

            if vals.get('email_bcc'):
                new_value.get('email_bcc') and new_value.update({'email_bcc': new_value.get('email_bcc') + ',' + vals.get('email_bcc')}) or vals.get('email_bcc')

            if vals.get('reply_to'):
                new_value.get('reply_to') and new_value.update({'reply_to': new_value.get('reply_to') + ',' + vals.get('reply_to')}) or vals.get('reply_to')

            vals.update(new_value)
            vals.update({'name': new_value.get('subject','')})
        return {'value': vals}

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
