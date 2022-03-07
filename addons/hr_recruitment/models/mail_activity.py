# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def action_create_calendar_event(self):
        action = super().action_create_calendar_event()
        meeting_activity_type = self.env['mail.activity.type'].search([('category', '=', 'meeting')])

        if action['context']['default_res_model'] == 'hr.applicant' and action['context']['default_activity_type_id'] in meeting_activity_type.ids:
            action['context']['active_id'] = self.res_model_id
            action['context']['active_model'] = self.res_model
        return action
