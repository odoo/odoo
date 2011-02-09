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
        'evaluation_id': fields.many2one('hr.evaluation.interview', 'Interview', required=True)
    }

    def send_mail(self, cr, uid, ids, context=None):
        email_message_obj = self.pool.get('email.message')
        hr_evaluation_interview_obj = self.pool.get('hr.evaluation.interview')
        evaluation_data = self.read(cr, uid, ids, context=context)[0]
        current_interview = hr_evaluation_interview_obj.browse(cr, uid, evaluation_data.get('evaluation_id'))
        if current_interview.state == "waiting_answer" and current_interview.user_to_review_id.work_email :
            msg = " Hello %s, \n\n Kindly post your response for '%s' survey interview. \n\n Thanks,"  %(current_interview.user_to_review_id.name, current_interview.survey_id.title)
            email_message_obj.email_send(cr, uid, tools.config['email_from'], [current_interview.user_to_review_id.work_email],\
                                          'Reminder to fill up Survey', msg, model='hr.evaluation.reminder')
        return {'type': 'ir.actions.act_window_close'}

hr_evaluation_reminder()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
