# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo.fields import Date
from odoo.tests import TransactionCase


class HrWorkEntryAttendanceCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env.company.tz = "Europe/Brussels"
        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'attendance_ids': [
                (0, 0,
                    {
                        'dayofweek': weekday,
                        'hour_from': hour,
                        'hour_to': hour + 4,
                    })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
            'name': 'Standard 40h/week',
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Billy Pointer',
            'tz': 'UTC',
            'wage': 3500,
            'attendance_based': True,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
        })

        cls.version = cls.employee.version_id

        cls.work_entry_type_leave = cls.env['hr.work.entry.type'].create({
            'name': 'Time Off',
            'count_as': 'absence',
            'code': 'LEAVETEST100'
        })

        cls.richard_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'sex': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.us').id,
            'date_version': Date.to_date('2018-01-01'),
            'contract_date_start': Date.to_date('2018-01-01'),
            'contract_date_end': Date.today() + relativedelta(years=2),
            'wage': 5000.33,
        })
