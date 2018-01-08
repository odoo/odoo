# -*- coding: utf-8 -*-

import time
import calendar

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def write(self, vals):
        # fiscalyear_lock_date can't be set to a prior date
        if vals.get('fiscalyear_lock_date'):
            old_fiscalyear_lock_date = self and len(self) == 1 and self.fiscalyear_lock_date or None
            self = self.with_context(dict(self._context, old_fiscalyear_lock_date=old_fiscalyear_lock_date))
        return super(ResCompany, self).write(vals)

    @api.constrains('period_lock_date', 'fiscalyear_lock_date')
    def _check_lock_dates(self):
        period_lock_date = self.period_lock_date and\
            time.strptime(self.period_lock_date, DEFAULT_SERVER_DATE_FORMAT) or False
        old_fiscalyear_lock_date = self._context.get('old_fiscalyear_lock_date') and \
            time.strptime(self._context['old_fiscalyear_lock_date'], DEFAULT_SERVER_DATE_FORMAT) or False
        fiscalyear_lock_date = self.fiscalyear_lock_date and\
            time.strptime(self.fiscalyear_lock_date, DEFAULT_SERVER_DATE_FORMAT) or False

        # Check the irreversibility of the lock date for all users
        if old_fiscalyear_lock_date:
            if fiscalyear_lock_date:
                if fiscalyear_lock_date < old_fiscalyear_lock_date:
                    raise ValidationError(_('The lock date for all users is irreversible and must be strictly higher than the previous date.'))
            else:
                raise ValidationError(_('The lock date for all users is irreversible and can\'t be removed'))

        if not fiscalyear_lock_date:
            return

        # Check the lock date for all users
        previous_month = datetime.strptime(fields.Date.today(), DEFAULT_SERVER_DATE_FORMAT) + relativedelta(months=-1)
        days_previous_month = calendar.monthrange(previous_month.year, previous_month.month)
        previous_month = previous_month.replace(day=days_previous_month[1]).timetuple()
        if fiscalyear_lock_date <= previous_month:
            raise ValidationError(_('The lock date for all users must be higher than the last day of the previous month.'))

        if not period_lock_date:
            return

        # Check the lock date for non-advisers
        if period_lock_date > fiscalyear_lock_date:
            raise ValidationError(_('The lock date for all users must be higher or equal to the lock date for non-advisers.'))
