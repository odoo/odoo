# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MailingMailingScheduleDate(models.TransientModel):
    _name = 'mailing.mailing.schedule.date'
    _description = 'Mass Mailing Scheduling'

    schedule_date = fields.Datetime(string='Scheduled for')
    mass_mailing_id = fields.Many2one('mailing.mailing', required=True, ondelete='cascade')

    @api.constrains('schedule_date')
    def _check_schedule_date(self):
        for scheduler in self:
            if scheduler.schedule_date < fields.Datetime.now():
                raise ValidationError(_('Please select a date equal/or greater than the current date.'))

    def set_schedule_date(self):
        self.mass_mailing_id.write({'schedule_date': self.schedule_date, 'state': 'in_queue'})
