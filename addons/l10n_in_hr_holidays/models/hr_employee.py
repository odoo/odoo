# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models


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

        start = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S').date()
        end = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S').date() if date_to else start

        holidays = self.env['hr.leave']._get_exceptional_holidays(
            datetime.combine(start, time.min),
            datetime.combine(end, time.max),
        )
        if not holidays:
            return unusual_days

        def date_range(start_date, end_date):
            return {
                (start_date + timedelta(days=i)).isoformat()
                for i in range((end_date - start_date).days + 1)
            }

        working_dates = set()
        compensatory_dates = set()
        timezone = ZoneInfo(self.company_id.tz or self.env.user.tz or "UTC")

        for holiday in holidays:
            working_dates |= date_range(
                holiday.date_from.replace(tzinfo=UTC).astimezone(timezone).date(),
                holiday.date_to.replace(tzinfo=UTC).astimezone(timezone).date(),
            )

            if holiday.working_start_date and holiday.working_end_date:
                compensatory_dates |= date_range(
                    holiday.working_start_date.replace(tzinfo=UTC).astimezone(timezone).date(),
                    holiday.working_end_date.replace(tzinfo=UTC).astimezone(timezone).date(),
                )

        for date in unusual_days:
            if date in working_dates:
                unusual_days[date] = False
            elif date in compensatory_dates:
                unusual_days[date] = True

        return unusual_days
