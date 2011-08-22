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
    _inherit = 'mail.compose.message'

    def get_value(self, cr, uid, model, resource_id, context=None):
        '''
        To get values of the resource_id for the model
        @param model: Object
        @param resource_id: id of a record for which values to be read

        @return: Returns a dictionary
        '''
        result = super(email_compose_message, self).get_value(cr, uid,  model, resource_id, context=context)
        if model == 'project.task' and resource_id:
            task_pool = self.pool.get('project.task')
            task_data = task_pool.browse(cr, uid, resource_id, context=context)
            partner = task_data.partner_id or task_data.project_id.partner_id
            if task_data.project_id.warn_manager and (not task_data.project_id.user_id or task_data.project_id.user_id and not task_data.project_id.user_id.user_email) :
                raise osv.except_osv(_('Error'), _("Please specify the Project Manager or email address of Project Manager."))
            elif task_data.project_id.warn_customer and (not partner or not len(partner.address) or (partner and len(partner.address) and not partner.address[0].email)):
                raise osv.except_osv(_('Error'), _("Please specify the Customer or email address of Customer."))

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
            if partner and len(partner.address):
                result.update({'email_to': result.get('email_to',False) and result.get('email_to') + ',' + partner.address[0].email})
            result.update({
                       'body_text': description or False,
                       'email_to':   task_data.project_id.user_id and task_data.project_id.user_id.user_email or False,
                       'subject':  _("Task '%s' Closed") % task_data.name,
                       'model': model,
                       'res_id': resource_id,
                    })

        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
