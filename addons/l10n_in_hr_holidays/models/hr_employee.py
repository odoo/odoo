# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime, time, timedelta


class HrEmployees(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_special_days_data(self, date_start, date_end):
        res = super().get_special_days_data(date_start, date_end)
        return dict(
            res,
            optionalHolidays=self._get_optional_holidays_data(date_start, date_end),
            exceptionalDays=self._get_exceptional_days_data(date_start, date_end),
        )

    def _get_exceptional_days_data(self, date_start, date_end):
        date_from = fields.Datetime.from_string(date_start)
        date_to = fields.Datetime.from_string(date_end)

        exceptional_records = self.env['hr.leave']._get_exceptional_holidays(date_from, date_to)

        exceptional_days = []
        for rec in exceptional_records:
            if rec.date_from and rec.date_to:
                exceptional_days.append({
                    'id': rec.id,
                    'start': rec.date_from.isoformat(),
                    'end': rec.date_to.isoformat(),
                    'title': rec.name or self.env._("Exceptional Working Day"),
                })

        return exceptional_days

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

    def _get_unusual_days(self, date_from, date_to=None):
        unusual_days = super()._get_unusual_days(date_from, date_to)

        if self.company_id.country_id.code != 'IN':
            return unusual_days

        date_from_date = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S').date()
        date_to_date = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S').date() if date_to else date_from_date

        exceptional_days = self.env['hr.leave']._get_exceptional_holidays(
            datetime.combine(date_from_date, time.min),
            datetime.combine(date_to_date, time.max),
        )
        if not exceptional_days:
            return unusual_days

        working_dates = set()
        compensatory_dates = set()

        for holiday in exceptional_days:
            hstart = holiday.date_from.date()
            hend = holiday.date_to.date()
            working_dates.update(
                (hstart + timedelta(days=i)).isoformat()
                for i in range((hend - hstart).days + 1)
            )

            if holiday.working_start_date and holiday.working_end_date:
                comp_start = holiday.working_start_date.date()
                comp_end = holiday.working_end_date.date()
                comp_days = (comp_end - comp_start).days + 1
                compensatory_dates.update(
                    (comp_start + timedelta(days=i)).isoformat()
                    for i in range(comp_days)
                )

        for date_str in unusual_days:
            if date_str in working_dates:
                unusual_days[date_str] = False
            elif date_str in compensatory_dates:
                unusual_days[date_str] = True

        return unusual_days
