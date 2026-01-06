# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from dateutil.relativedelta import relativedelta


class HrEmployees(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_special_days_data(self, date_start, date_end):
        res = super().get_special_days_data(date_start, date_end)
        return dict(res, optionalHolidays=self._get_optional_holidays_data(date_start, date_end))

    @api.model
    def get_optional_days(self, date_start, date_end):
        optional_holidays = self._get_optional_holidays(date_start, date_end)
        all_days = []
        for optional_holiday in optional_holidays:
            num_days = (optional_holiday.end_date - optional_holiday.start_date).days
            for d in range(num_days + 1):
                all_days.append(optional_holiday.start_date + relativedelta(days=d))
        return all_days

    def _get_optional_holidays_data(self, date_start, date_end):
        optional_holidays = self._get_optional_holidays(date_start, date_end)
        return [{
            'id': -optional_holiday.id,
            'colorIndex': 0,
            'title': optional_holiday.name,
            'isAllDay': True,
            'start': optional_holiday.start_date.isoformat(),
            'startType': "start_date",
            'end': optional_holiday.end_date.isoformat(),
            'endType': "end_date",
        } for optional_holiday in optional_holidays]

    def _get_optional_holidays(self, date_start, date_end):
        optional_holidays = self.env['l10n.in.hr.leave.optional.holiday'].search([
            ('end_date', '<=', date_end),
            ('start_date', '>=', date_start),
            ('company_id', 'in', self.env.companies.ids)
        ])
        return optional_holidays
