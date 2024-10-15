# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.addons import mail


class MailActivitySchedule(mail.MailActivitySchedule):

    def action_create_calendar_event(self):
        self.ensure_one()
        if self.is_batch_mode:
            raise UserError(_("Scheduling an activity using the calendar is not possible on more than one record."))
        return self.with_context({
            'default_res_model': self.res_model,
            'default_res_id': self._evaluate_res_ids()[0],
        })._action_schedule_activities().action_create_calendar_event()
