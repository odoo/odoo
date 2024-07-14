#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
