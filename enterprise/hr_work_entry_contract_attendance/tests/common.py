#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo.fields import Date
from odoo.tests import TransactionCase

class HrWorkEntryAttendanceCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Billy Pointer',
            'tz': 'UTC',
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Billy Pointer\'s contract',
            'employee_id': cls.employee.id,
            'wage': 3500,
            'work_entry_source': 'attendance',
            'date_start': '2020-01-01',
            'state': 'open',
        })
        cls.work_entry_type_leave = cls.env['hr.work.entry.type'].create({
            'name': 'Time Off',
            'is_leave': True,
            'code': 'LEAVETEST100'
        })
        cls.richard_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'gender': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.env['hr.contract'].create({
            'date_end': Date.today() + relativedelta(years=2),
            'date_start': Date.to_date('2018-01-01'),
            'name': 'Contract for Richard',
            'wage': 5000.0,
            'employee_id': cls.richard_emp.id,
        })
