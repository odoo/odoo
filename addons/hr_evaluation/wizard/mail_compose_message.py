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

class mail_compose_message(osv.osv_memory):
    _inherit = 'mail.compose.message'

    def get_value(self, cr, uid, model, resource_id, context=None):
        '''
        To get values of the resource_id for the model
        @param model: Object
        @param resource_id: id of a record for which values to be read

        @return: Returns a dictionary
        '''
        if context is None:
            context = {}
        result = super(mail_compose_message, self).get_value(cr, uid,  model, resource_id, context=context)
        if model == 'hr.evaluation.interview' and resource_id:
            model_pool = self.pool.get(model)
            record_data = model_pool.browse(cr, uid, resource_id, context)
            if record_data.state == "waiting_answer":
                msg = _("Hello %s, \n\n Kindly post your response for '%s' survey interview. \n\n Thanks,")  %(record_data.user_to_review_id.name, record_data.survey_id.title)
                result.update({
                        'email_to': record_data.user_to_review_id.work_email or False,
                        'subject': _("Reminder to fill up Survey"),
                        'body_text': msg,
                    })
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
