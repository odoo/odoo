# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: odoo@cybrosys.com
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

import datetime
from datetime import datetime
from odoo import api, fields, models, _


class DeadLineReminder(models.Model):
    _inherit = "project.task"

    task_reminder = fields.Boolean("Reminder")

    @api.model
    def _cron_deadline_reminder(self):
        for task in self.env['project.task'].search(
                [('date_deadline', '!=', None),
                 ('task_reminder', '=', True), ('user_ids', '!=', None)]):
            reminder_date = task.date_deadline
            today = datetime.now().date()

            if reminder_date == today and task:
                template_id = self.env['ir.model.data']._xmlid_lookup(
                    'task_deadline_reminder.email_template_edi_deadline_reminder')[2]
                if template_id:
                    email_template_obj = self.env['mail.template'].browse(
                        template_id)
                    for usr in task.user_ids:
                        data = {'email_to': usr.email}
                        values = email_template_obj.with_context(data).generate_email(task.id,
                           ['subject', 'body_html', 'email_from', 'email_to',
                            'partner_to', 'email_cc', 'reply_to','scheduled_date'])
                        msg_id = self.env['mail.mail'].create(values)
                        if msg_id:
                            msg_id._send()
        return True
