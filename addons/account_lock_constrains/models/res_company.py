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
        if 'fiscalyear_lock_date' in vals or 'period_lock_date' in vals:
            self._check_lock_dates(vals)
        return super(ResCompany, self).write(vals)

    @api.multi
    def _check_lock_dates(self, vals):
        '''Check the lock dates for the current companies. This can't be done in a api.constrains because we need
        to perform some comparison between new/old values. This method forces the lock dates to be irreversible.

        * The lock date for advisers can't be unset.
        * The lock date for advisers must be higher than the lock date for non-advisers.
        * The lock date for advisers must be higher than the last day of the previous month.
        * The lock date for advisers must be higher than the previous lock date set if exists.

        :param vals: The values passed to the write method.
        '''
        period_lock_date = vals.get('period_lock_date') and\
            time.strptime(vals['period_lock_date'], DEFAULT_SERVER_DATE_FORMAT)
        fiscalyear_lock_date = vals.get('fiscalyear_lock_date') and\
            time.strptime(vals['fiscalyear_lock_date'], DEFAULT_SERVER_DATE_FORMAT)

        previous_month = datetime.strptime(fields.Date.today(), DEFAULT_SERVER_DATE_FORMAT) + relativedelta(months=-1)
        days_previous_month = calendar.monthrange(previous_month.year, previous_month.month)
        previous_month = previous_month.replace(day=days_previous_month[1]).timetuple()
        for company in self:
            old_fiscalyear_lock_date = company.fiscalyear_lock_date and\
                time.strptime(company.fiscalyear_lock_date, DEFAULT_SERVER_DATE_FORMAT)

            # The user attempts to remove the existing fiscal year lock date
            if old_fiscalyear_lock_date and not fiscalyear_lock_date and 'fiscalyear_lock_date' in vals:
                raise ValidationError(_('The lock date for all users is irreversible and can\'t be removed'))

            # The user attempts to set a fiscal year lock date prior to the previous one
            if old_fiscalyear_lock_date and fiscalyear_lock_date and fiscalyear_lock_date < old_fiscalyear_lock_date:
                raise ValidationError(_('The lock date for all users is irreversible and must be strictly higher than the previous date.'))

            # In case of no new fiscal year in vals, fallback to the oldest
            if not fiscalyear_lock_date:
                if old_fiscalyear_lock_date:
                    fiscalyear_lock_date = old_fiscalyear_lock_date
                else:
                    continue

            # The user attempts to set a fiscal year lock date prior to the last day of previous month
            if fiscalyear_lock_date <= previous_month:
                raise ValidationError(_('The lock date for all users must be higher than the last day of the previous month.'))

            # In case of no new period lock date in vals, fallback to the one defined in the company
            if not period_lock_date:
                if company.period_lock_date:
                    period_lock_date = time.strptime(company.period_lock_date, DEFAULT_SERVER_DATE_FORMAT)
                else:
                    continue

            # The user attempts to set a fiscal year lock date prior to the period lock date
            if period_lock_date > fiscalyear_lock_date:
                raise ValidationError(_('The lock date for all users must be higher or equal to the lock date for non-advisers.'))
