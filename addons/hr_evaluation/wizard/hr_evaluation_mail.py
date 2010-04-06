##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import tools

class hr_evaluation_reminder(osv.osv_memory):
    _name = "hr.evaluation.reminder"
    _description = "Sends Reminders to employess to fill the evaluations"
    _columns = {
        'evaluation_id': fields.many2one('hr_evaluation.evaluation', 'Evaluations', required=True)
    }

    def send_mail(self, cr, uid, ids, context={}):
        hr_evaluation_obj = self.pool.get('hr_evaluation.evaluation')
        evaluation_data = self.read(cr, uid, ids, context=context)[0]
        for waiting_id in hr_evaluation_obj.browse(cr, uid, evaluation_data['evaluation_id'], context=context).survey_request_ids:
            if waiting_id.state == "waiting_answer" and waiting_id.user_to_review_id.work_email :
                msg = " Hello %s, \n\n Kindly post your response for %s survey. \n\n Thanks,"  %(waiting_id.user_to_review_id.name, waiting_id.survey_id.title)
                tools.email_send(tools.config['email_from'], [waiting_id.user_to_review_id.work_email],\
                                          'Reminder to fill up Survey', msg)
        return {'type': 'ir.actions.act_window_close'}

hr_evaluation_reminder()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: