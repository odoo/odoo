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

class email_compose_message(osv.osv_memory):
    _inherit = 'email.compose.message'

    def get_value(self, cr, uid, model, resource_id, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).get_value(cr, uid,  model, resource_id, context=context)
        if model != 'project.task':
            return result
        task_pool = self.pool.get('project.task')
        task_data = task_pool.browse(cr, uid, resource_id, context=context)
        partner = task_data.partner_id or task_data.project_id.partner_id

        result.update({'email_from': task_data.user_id and task_data.user_id.user_email or False})
        val = {
                'name': task_data.name,
                'user_id': task_data.user_id.name,
                'task_id': "%d/%d" % (task_data.project_id.id, task_data.id),
                'date_start': task_data.date_start,
                'date': task_data.date_end,
                'state': task_data.state
        }
        header = (task_data.project_id.warn_header or '') % val
        footer = (task_data.project_id.warn_footer or '') % val
        description = u'%s\n %s\n %s\n\n \n%s' % (header, task_data.description or '', footer, task_data.user_id and task_data.user_id.signature)
        result.update({'description': description or False})
        result.update({'email_to':   task_data.project_id.user_id and task_data.project_id.user_id.user_email or False})
        if partner and len(partner.address) and 'email_to' in fields:
            result.update({'email_to': result.get('email_to',False) and result.get('email_to') + ',' + partner.address[0].email})
        result.update({'name':  _("Task '%s' Closed") % task_data.name})

        return result

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id',False) and context.get('email_model',False) and context.get('email_model') == 'project.task':
            task_pool = self.pool.get('project.task')
            task_data = task_pool.browse(cr, uid, context.get('active_id'), context=context)
            partner = task_data.partner_id or task_data.project_id.partner_id

            if task_data.project_id.warn_manager and (not task_data.project_id.user_id or task_data.project_id.user_id and not task_data.project_id.user_id.user_email) :
                raise osv.except_osv(_('Error'), _("Please specify the Project Manager or email address of Project Manager."))
            elif task_data.project_id.warn_customer and (not partner or not len(partner.address) or (partner and len(partner.address) and not partner.address[0].email)):
                raise osv.except_osv(_('Error'), _("Please specify the Customer or email address of Customer."))
            vals = self.get_value(cr, uid, context.get('email_model'), context.get('active_id'), context)
            if 'email_from' in fields:
                result.update({'email_from': vals.get('email_from','')})

            if 'description' in fields:
                result.update({'description': vals.get('description','')})

            if 'email_to' in fields:
                result.update({'description': vals.get('description','')})

            if 'name' in fields:
                result.update({'description': vals.get('name','')})

            if 'model' in fields:
                result.update({'model':context.get('email_model')})

            if 'res_id' in fields:
                result.update({'res_id':context.get('active_id')})

        return result

    def on_change_referred_doc(self, cr, uid, ids, model, resource_id, context=None):
        if context is None:
            context = {}
        if context.get('mail') == 'reply':
            return {'value':{}}
        result = super(email_compose_message, self).on_change_referred_doc(cr, uid, ids, model, resource_id, context=context)
        if not result.get('value'):
            result.update({'value':{}})
        if resource_id and model == 'project.task':
            vals = self.get_value(cr, uid, model, resource_id, context)
            result.get('value',{}).update({
                       'email_from': vals.get('email_from',''),
                       'email_to': vals.get('email_to',''),
                       'description': vals.get('description',''),
                       'name': vals.get('name',''),
                       'email_cc': vals.get('email_cc',''),
                       'email_bcc': vals.get('email_bcc',''),
                       'reply_to': vals.get('reply_to',''),
                    })
        return result

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
