# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models


class HrEmployees(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_special_days_data(self, date_start, date_end):
        res = super().get_special_days_data(date_start, date_end)
        return dict(res, optionalHolidays=self._get_optional_holidays_data(date_start, date_end))

    def _get_optional_holidays_data(self, date_start, date_end):
        employee = self._get_contextual_employee()
        optional_holidays = employee._get_optional_holidays(date_start, date_end)
        return [{
            'id': -optional_holiday.id,
            'end': datetime.combine(optional_holiday.date, datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.combine(optional_holiday.date, datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': optional_holiday.name,
        } for optional_holiday in optional_holidays]

    def _get_optional_holidays(self, start_date, end_date):
        domain = [
            ('date', '<=', end_date),
            ('date', '>=', start_date),
            ('company_id', 'in', self.env.companies.ids)
        ]
        return self.env['l10n.in.hr.leave.optional.holiday'].search(domain)
