# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from datetime import datetime, UTC
from zoneinfo import ZoneInfo


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    external_code = fields.Char("External Code", copy=False, help="Use this code to export your data to a third party", groups="hr.group_hr_user")

    # YTI TODO: Rename private method into _get_work_entries_vals()
    # Public method probably to drop
    def generate_work_entries(self, date_start, date_stop):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            versions = self._get_versions_with_contract_overlap_with_period(date_start, date_stop)
        else:
            versions = self._get_all_versions_with_contract_overlap_with_period(date_start, date_stop)
        return versions.generate_work_entries(date_start, date_stop)

    def _get_date_in_employee_tz_or_utc(self, value):
        """Returns the date of `value` in the employee's timezone (naive datetimes treated as UTC)"""
        self.ensure_one()
        if not isinstance(value, datetime):
            return value
        if not value.tzinfo:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(ZoneInfo(self._get_tz())).date()
