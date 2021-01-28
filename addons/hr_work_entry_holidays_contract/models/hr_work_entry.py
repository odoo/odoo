# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _get_duration(self, date_start, date_stop):
        """
        The work durations are calculated according to the contract calendar.
        """
        if not date_start or not date_stop:
            return 0
        if not self.work_entry_type_id and self.leave_id:
            calendar = self.contract_id.resource_calendar_id
            employee = self.contract_id.employee_id
            contract_data = employee._get_work_days_data_batch(
                date_start, date_stop, compute_leaves=False, calendar=calendar)[employee.id]
            return contract_data.get('hours', 0)
        return super()._get_duration(date_start, date_stop)
