# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingMailingScheduleDate(models.TransientModel):
    _name = "mailing.mailing.schedule.date"
    _description = "schedule a mailing"

    schedule_date = fields.Datetime(string='Scheduled for')
    mass_mailing_id = fields.Many2one('mailing.mailing', required=True)

    def action_schedule_date(self):
        self.mass_mailing_id.write({'schedule_type': 'scheduled', 'schedule_date': self.schedule_date})
        self.mass_mailing_id.action_put_in_queue()
