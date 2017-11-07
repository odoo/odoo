# -*- coding: utf-8 -*-

import time
import calendar

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.constrains('period_lock_date', 'fiscalyear_lock_date')
    def _check_dates(self):
        if not self.fiscalyear_lock_date:
            return

        fy_time = time.strptime(self.fiscalyear_lock_date, DEFAULT_SERVER_DATE_FORMAT)

        # Check the lock date for all users
        previous_month = datetime.strptime(fields.Date.today(), DEFAULT_SERVER_DATE_FORMAT) + relativedelta(months=-1)
        days_previous_month = calendar.monthrange(previous_month.year, previous_month.month)
        previous_month = previous_month.replace(day=days_previous_month[1]).timetuple()
        if fy_time <= previous_month:
            raise ValidationError(
                _('The lock date for all users must be higher than the last day of the previous month.'))

        if not self.period_lock_date:
            return

        period_time = time.strptime(self.period_lock_date, DEFAULT_SERVER_DATE_FORMAT)

        # Check the lock date for non-advisers
        if period_time > fy_time:
            raise ValidationError(
                _('The lock date for all users must be higher or equal to the lock date for non-advisers.'))
