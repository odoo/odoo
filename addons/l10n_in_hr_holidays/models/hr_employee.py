from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, api


class HrEmployees(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_exceptional_days_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        exceptional_days = self._get_exceptional_days(date_start, date_end).sorted('start_date')
        return list(map(lambda ed: {
            'id': -ed.id,
            'colorIndex': ed.color,
            'end': datetime.combine(ed.end_date, datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.combine(ed.start_date, datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': ed.name,
        }, exceptional_days))

    def get_exceptional_days(self, start_date, end_date):
        all_days = {}

        self = self or self.env.user.employee_id

        exceptional_days = self._get_exceptional_days(start_date, end_date)
        for exceptional_day in exceptional_days:
            num_days = (exceptional_day.end_date - exceptional_day.start_date).days
            for d in range(num_days + 1):
                all_days[str(exceptional_day.start_date + relativedelta(days=d))] = exceptional_day.color

        return all_days

    def _get_exceptional_days(self, start_date, end_date):
        domain = [
            ('start_date', '<=', end_date),
            ('end_date', '>=', start_date),
            ('company_id', 'in', self.env.companies.ids),
            '|',
                ('resource_calendar_id', '=', False),
                ('resource_calendar_id', '=', self.resource_calendar_id.id),
        ]

        if self.department_id:
            domain += [
                '|',
                ('department_ids', '=', False),
                ('department_ids', 'parent_of', self.department_id.id),
            ]
        else:
            domain += [('department_ids', '=', False)]

        return self.env['l10n.in.hr.holiday.exceptional.day'].search(domain)
