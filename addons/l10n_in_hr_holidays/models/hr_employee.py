# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrEmployees(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_special_days_data(self, date_start, date_end):
        res = super().get_special_days_data(date_start, date_end)
        return dict(res, optionalHolidays=self._get_optional_holidays_data(date_start, date_end))

    def _get_optional_holidays_data(self, date_start, date_end):
        optional_holidays = self.env['l10n.in.hr.leave.optional.holiday'].search([
            ('date', '<=', date_end),
            ('date', '>=', date_start),
            ('company_id', 'in', self.env.companies.ids)
        ])
        return [{
            'id': -optional_holiday.id,
            'title': optional_holiday.name,
            'isAllDay': True,
            'start': optional_holiday.date.isoformat(),
            'startType': "date",
            'end': optional_holiday.date.isoformat(),
            'endType': "date",
        } for optional_holiday in optional_holidays]
