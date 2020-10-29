# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone, UTC


class MailingMailingScheduleDate(models.TransientModel):
    _name = 'mailing.mailing.schedule.date'
    _description = 'Mass Mailing Scheduling'

    schedule_date = fields.Datetime(string='Scheduled for')
    mass_mailing_id = fields.Many2one('mailing.mailing', required=True, ondelete='cascade')

    @api.onchange('schedule_date')
    def _onchange_schedule_date(self):
        user_tz = timezone(self.env.user.tz)
        today = datetime.now().astimezone(user_tz)
        for mailing_schedule_date in self:
            if mailing_schedule_date.schedule_date:
                schedule_date_user_tz = mailing_schedule_date.schedule_date.astimezone(user_tz)
                if schedule_date_user_tz <= today:
                    temp_schedule_date = schedule_date_user_tz + timedelta(hours=1)
                    if temp_schedule_date.day > mailing_schedule_date.schedule_date.day or temp_schedule_date.day == 1:
                        mailing_schedule_date.schedule_date = schedule_date_user_tz.replace(minute=59, second=59).astimezone(UTC).replace(tzinfo=None)
                    else:
                        mailing_schedule_date.schedule_date = temp_schedule_date.astimezone(UTC).replace(tzinfo=None)

    @api.constrains('schedule_date')
    def _check_schedule_date(self):
        for scheduler in self:
            if scheduler.schedule_date < fields.Datetime.now():
                raise ValidationError(_('Please select a date equal/or greater than the current date.'))

    def set_schedule_date(self):
        self.mass_mailing_id.write({'schedule_date': self.schedule_date, 'state': 'in_queue'})
