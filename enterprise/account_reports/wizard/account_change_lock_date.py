# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChangeLockDate(models.TransientModel):
    """
    This wizard is used to change the lock date
    """
    _inherit = 'account.change.lock.date'

    def _create_default_report_external_values(self, lock_date_field):
        """
        Calls the _generate_default_external_values in account_report
        to create default external values for either all reports except the tax reports,
        or only the tax reports, depending on the lock date type:
            - max(fiscalyear_lock_date, hard_lock_date) is used to create default values in all reports except the tax reports for that date
            - tax_lock_date is used to create default values only in tax reports for that date
        """
        # extends account.accountant
        date_from, date_to = self._get_current_period_dates(lock_date_field)
        self.env['account.report']._generate_default_external_values(date_from, date_to, lock_date_field == 'tax_lock_date')
