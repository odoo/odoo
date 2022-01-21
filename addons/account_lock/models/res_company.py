# -*- coding: utf-8 -*-

import calendar
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _autorise_lock_date_changes(self, vals):
        '''Check the lock dates for the current companies. This can't be done in a api.constrains because we need
        to perform some comparison between new/old values. This method forces the lock dates to be irreversible.
        * You cannot set stricter restrictions on advisors than on users.
        Therefore, the All Users Lock Date must be anterior (or equal) to the Invoice/Bills Lock Date.
        * You cannot lock a period that has not yet ended.
        Therefore, the All Users Lock Date must be anterior (or equal) to the last day of the previous month.
        * Any new All Users Lock Date must be posterior (or equal) to the previous one.
        * You cannot delete a tax lock date, lock a period that is not finished yet or the tax lock date must be set after
        the last day of the previous month.
        :param vals: The values passed to the write method.
        '''
        period_lock_date = vals.get('period_lock_date') and fields.Date.from_string(vals['period_lock_date'])
        fiscalyear_lock_date = vals.get('fiscalyear_lock_date') and fields.Date.from_string(vals['fiscalyear_lock_date'])
        tax_lock_date = vals.get('tax_lock_date') and fields.Date.from_string(vals['tax_lock_date'])

        previous_month = fields.Date.today() + relativedelta(months=-1)
        days_previous_month = calendar.monthrange(previous_month.year, previous_month.month)
        previous_month = previous_month.replace(day=days_previous_month[1])
        for company in self:
            old_fiscalyear_lock_date = company.fiscalyear_lock_date
            old_period_lock_date = company.period_lock_date
            old_tax_lock_date = company.tax_lock_date

            # The user attempts to remove the tax lock date
            if old_tax_lock_date and not tax_lock_date and 'tax_lock_date' in vals:
                raise UserError(_('The tax lock date is irreversible and can\'t be removed.'))

            # The user attempts to set a tax lock date prior to the previous one
            if old_tax_lock_date and tax_lock_date and tax_lock_date < old_tax_lock_date:
                raise UserError(_('The new tax lock date must be set after the previous lock date.'))

            # In case of no new tax lock date in vals, fallback to the oldest
            tax_lock_date = tax_lock_date or old_tax_lock_date
            # The user attempts to set a tax lock date prior to the last day of previous month
            if tax_lock_date and tax_lock_date > previous_month:
                raise UserError(_('You cannot lock a period that has not yet ended. Therefore, the tax lock date must be anterior (or equal) to the last day of the previous month.'))

            # The user attempts to remove the lock date for advisors
            if old_fiscalyear_lock_date and not fiscalyear_lock_date and 'fiscalyear_lock_date' in vals:
                raise UserError(_('The lock date for advisors is irreversible and can\'t be removed.'))

            # The user attempts to set a lock date for advisors prior to the previous one
            if old_fiscalyear_lock_date and fiscalyear_lock_date and fiscalyear_lock_date < old_fiscalyear_lock_date:
                raise UserError(_('Any new All Users Lock Date must be posterior (or equal) to the previous one.'))

            # In case of no new fiscal year in vals, fallback to the oldest
            fiscalyear_lock_date = fiscalyear_lock_date or old_fiscalyear_lock_date
            if not fiscalyear_lock_date:
                continue

            # The user attempts to set a lock date for advisors prior to the last day of previous month
            if fiscalyear_lock_date > previous_month:
                raise UserError(_('You cannot lock a period that has not yet ended. Therefore, the All Users Lock Date must be anterior (or equal) to the last day of the previous month.'))

            # In case of no new period lock date in vals, fallback to the one defined in the company
            period_lock_date = period_lock_date or old_period_lock_date
            if not period_lock_date:
                continue

            # The user attempts to set a lock date for advisors prior to the lock date for users
            if period_lock_date < fiscalyear_lock_date:
                raise UserError(_('You cannot set stricter restrictions on advisors than on users. Therefore, the All Users Lock Date must be anterior (or equal) to the Invoice/Bills Lock Date.'))

    def write(self, vals):
        # fiscalyear_lock_date can't be set to a prior date
        if 'fiscalyear_lock_date' in vals or 'period_lock_date' in vals or 'tax_lock_date' in vals:
            self._autorise_lock_date_changes(vals)
        return super(ResCompany, self).write(vals)
