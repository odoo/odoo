# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import fields, models, _
from odoo.tools import get_lang

class ProjectTaskCreateTimesheet(models.TransientModel):
    _inherit = 'project.task.create.timesheet'

    def save_timesheet(self):
        if self.task_id.project_id.is_fsm:
            date = fields.Datetime.context_timestamp(self, datetime.now())
            self.task_id.message_post(
                body=_(
                    'Timer stopped at: %(date)s %(time)s',
                    date=date.strftime(get_lang(self.env).date_format),
                    time=date.strftime(get_lang(self.env).time_format),
                ),
            )
        super().save_timesheet()
