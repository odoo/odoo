# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import pytz
from dateutil.relativedelta import relativedelta
from odoo import exceptions
from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


@tagged('benefit')
class TestBenefit(TestPayslipBase):

    def setUp(self):
        super(TestBenefit, self).setUp()
        self.tz = pytz.timezone(self.richard_emp.tz)
        self.start = datetime.strptime('2015-11-01 01:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        self.end = datetime.strptime('2015-11-30 23:59:59', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        self.resource_calendar_id = self.env['resource.calendar'].create({'name': 'Zboub'})
        self.env['hr.contract'].create({
            'date_start': self.start - relativedelta(days=5),
            'name': 'dodo',
            'resource_calendar_id': self.resource_calendar_id.id,
            'wage': 1000,
            'employee_id': self.richard_emp.id,
            'state': 'open',
        })
        self.richard_emp.resource_calendar_id = self.resource_calendar_id

        self.benefit_type_leave = self.env['hr.benefit.type'].create({
            'name': 'Leave',
            'is_leave': True,
            'code': 'LEAVE100'
        })
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'allocation_type': 'no',
            'benefit_type_id': self.benefit_type_leave.id
        })
        self.benefit_type = self.env['hr.benefit.type'].create({
            'name': 'attendance',
            'is_leave': False,
            'code': 'LEAVE100'
        })

    def test_no_duplicate(self):
        self.richard_emp.generate_benefit(self.start, self.end)
        pou1 = self.env['hr.benefit'].search_count([])
        self.richard_emp.generate_benefit(self.start, self.end)
        pou2 = self.env['hr.benefit'].search_count([])
        self.assertEqual(pou1, pou2, "Benefits should not be duplicated")

    def test_benefit(self):

        self.richard_emp.generate_benefit(self.start, self.end)

        attendance_nb = len(self.resource_calendar_id._attendance_intervals(self.start, self.end))
        benefit_nb = self.env['hr.benefit'].search_count([('employee_id', '=', self.richard_emp.id)])
        self.assertEqual(attendance_nb, benefit_nb, "One benefit should be generated for each calendar attendance")

    def test_split_benefit_by_day(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-03 18:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)

        # Benefit of type attendance should be split in three
        benefit = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'date_start': start,
            'date_stop': end,
        })

        benefits = benefit.split_by_day()
        self.assertEqual(len(benefits), 3, "Benefit should be split in three")
        self.assertEqual(pytz.utc.localize(benefits[0].date_start), self.tz.localize(datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S')))
        self.assertEqual(pytz.utc.localize(benefits[0].date_stop), self.tz.localize(datetime.strptime('2015-11-01 23:59:59', '%Y-%m-%d %H:%M:%S')))

        self.assertEqual(pytz.utc.localize(benefits[1].date_start), self.tz.localize(datetime.strptime('2015-11-02 00:00:00', '%Y-%m-%d %H:%M:%S')))
        self.assertEqual(pytz.utc.localize(benefits[1].date_stop), self.tz.localize(datetime.strptime('2015-11-02 23:59:59', '%Y-%m-%d %H:%M:%S')))

        self.assertEqual(pytz.utc.localize(benefits[2].date_start), self.tz.localize(datetime.strptime('2015-11-03 00:00:00', '%Y-%m-%d %H:%M:%S')))
        self.assertEqual(pytz.utc.localize(benefits[2].date_stop), self.tz.localize(datetime.strptime('2015-11-03 18:00:00', '%Y-%m-%d %H:%M:%S')))

        # Test with end at mid-night -> should not create benefit starting and ending at the same time (at 00:00)
        start = datetime.strptime('2013-11-01 00:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2013-11-04 00:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)

        benefit = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'date_start': start,
            'date_stop': end,
        })
        benefits = benefit.split_by_day()
        self.assertEqual(len(benefits), 3, "Benefit should be split in three")
        self.assertEqual(pytz.utc.localize(benefits[0].date_start), self.tz.localize(datetime.strptime('2013-11-01 00:00:00', '%Y-%m-%d %H:%M:%S')))
        self.assertEqual(pytz.utc.localize(benefits[0].date_stop), self.tz.localize(datetime.strptime('2013-11-01 23:59:59', '%Y-%m-%d %H:%M:%S')))

        self.assertEqual(pytz.utc.localize(benefits[1].date_start), self.tz.localize(datetime.strptime('2013-11-02 00:00:00', '%Y-%m-%d %H:%M:%S')))
        self.assertEqual(pytz.utc.localize(benefits[1].date_stop), self.tz.localize(datetime.strptime('2013-11-02 23:59:59', '%Y-%m-%d %H:%M:%S')))

        self.assertEqual(pytz.utc.localize(benefits[2].date_start), self.tz.localize(datetime.strptime('2013-11-03 00:00:00', '%Y-%m-%d %H:%M:%S')))
        self.assertEqual(pytz.utc.localize(benefits[2].date_stop), self.tz.localize(datetime.strptime('2013-11-03 23:59:59', '%Y-%m-%d %H:%M:%S')))


    def test_duplicate_global_benefit_to_attendance(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-03 18:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)

        benef = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.env.ref('hr_payroll.benefit_type_attendance').id,
            'date_start': start,
            'date_stop': end,
        })
        benef._duplicate_to_calendar()
        attendance_nb = self.env['resource.calendar.attendance'].search_count([
            ('date_from', '>=', start.date()),
            ('date_to', '<=', end.date())
        ])
        self.assertEqual(attendance_nb, 0, "It should not duplicate the 'normal/global' benefit type")

    def test_duplicate_benefit_to_attendance(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-03 18:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)

        # Benefit (not leave) should be split in three attendance
        benef = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type.id,
            'date_start': start,
            'date_stop': end,
        })
        benef._duplicate_to_calendar()
        attendance_nb = self.env['resource.calendar.attendance'].search_count([
            ('date_from', '>=', start.date()),
            ('date_to', '<=', end.date())
        ])
        self.assertEqual(attendance_nb, 3, "It should create one calendar attendance per day")
        self.assertTrue(self.env['resource.calendar.attendance'].search([
            ('date_from', '=', datetime.strptime('2015-11-01', '%Y-%m-%d').date()),
            ('date_to', '=', datetime.strptime('2015-11-01', '%Y-%m-%d').date()),
            ('hour_from', '=', 9.0),
            ('hour_to', '>=', 23.9)
        ]))
        self.assertTrue(self.env['resource.calendar.attendance'].search([
            ('date_from', '=', datetime.strptime('2015-11-02', '%Y-%m-%d').date()),
            ('date_to', '=', datetime.strptime('2015-11-02', '%Y-%m-%d').date()),
            ('hour_from', '=', 0.0),
            ('hour_to', '>=', 23.9)
        ]))
        self.assertTrue(self.env['resource.calendar.attendance'].search([
            ('date_from', '=', datetime.strptime('2015-11-03', '%Y-%m-%d').date()),
            ('date_to', '=', datetime.strptime('2015-11-03', '%Y-%m-%d').date()),
            ('hour_from', '=', 0.0),
            ('hour_to', '=', 18.0)
        ]))

    def test_create_benefit_leave(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-03 18:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)

        benef = self.env['hr.benefit'].create({
            'name': 'Richard leave from benef',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type_leave.id,
            'date_start': start,
            'date_stop': end,
        })
        benef.action_validate(benef.ids)
        calendar_leave = self.env['resource.calendar.leaves'].search([('name', '=', 'Richard leave from benef')])
        self.assertTrue(calendar_leave, "It should have created a leave in the calendar")
        self.assertEqual(calendar_leave.benefit_type_id, benef.benefit_type_id, "It should have the same benefit type")

    def test_validate_conflict_benefit(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-01 13:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        benef1 = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.env.ref('hr_payroll.benefit_type_attendance').id,
            'date_start': start,
            'date_stop': end + relativedelta(hours=5),
        })
        benef2 = self.env['hr.benefit'].create({
            'name': '2',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.env.ref('hr_payroll.benefit_type_attendance').id,
            'date_start': start + relativedelta(hours=3),
            'date_stop': end,
        })
        self.assertFalse(benef1.action_validate(benef1.ids), "It should not validate benefits conflicting with others")
        self.assertTrue(benef1.display_warning)
        self.assertNotEqual(benef1.state, 'validated')

    def test_validate_non_approved_leave_benefit(self):
        benef1 = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type_leave.id,
            'date_start': self.start,
            'date_stop': self.end,
        })
        leave_1 = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': self.start - relativedelta(days=1),
            'date_to': self.start + relativedelta(days=1),
            'number_of_days': 2,
        })
        self.assertFalse(benef1.action_validate(benef1.ids),"It should not validate benefits conflicting with non approved leaves")
        self.assertTrue(benef1.display_warning)

    def test_validate_undefined_benefit(self):
        benef1 = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'date_start': self.start,
            'date_stop': self.end,
        })
        self.assertFalse(benef1.action_validate(benef1.ids),"It should not validate benefits without a type")

    def test_approve_leave_benefit(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-03 13:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        leave = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': start,
            'date_to': start + relativedelta(days=1),
            'number_of_days': 2,
        })
        benef = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type.id,
            'date_start': start,
            'date_stop': end,
            'leave_id': leave.id
        })
        leave.action_approve()

        new_leave_benef = self.env['hr.benefit'].search([
            ('date_start', '=', datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S')),
            ('date_stop', '=', datetime.strptime('2015-11-02 09:00:00', '%Y-%m-%d %H:%M:%S')),
            ('benefit_type_id.is_leave', '=', True)
        ])

        new_benef = self.env['hr.benefit'].search([
            ('date_start', '=', datetime.strptime('2015-11-02 09:00:01', '%Y-%m-%d %H:%M:%S')),
            ('date_stop', '=', end),
            ('benefit_type_id.is_leave', '=', False)
        ])

        self.assertTrue(new_benef, "It should have created a benefit for the last two days")
        self.assertTrue(new_leave_benef, "It should have created a leave benefit for the first day")

        self.assertTrue(benef.action_validate((new_benef|new_leave_benef).ids), "It should be able to validate the benefits")

    def test_refuse_leave_benefit(self):
        start = datetime.strptime('2015-11-01 09:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-03 13:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        leave = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': start,
            'date_to': start + relativedelta(days=1),
            'number_of_days': 2,
        })
        benef = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type.id,
            'date_start': start,
            'date_stop': end,
            'leave_id': leave.id
        })
        benef.action_validate(benef.ids)
        self.assertTrue(benef.display_warning, "It should have an error (conflicting leave to approve")
        leave.action_refuse()
        self.assertFalse(benef.display_warning, "It should not have an error")

    def test_time_normal_benefit(self):
        # Normal attendances (global to all employees)
        data = self.richard_emp.get_benefit_days_data(self.env.ref('hr_payroll.benefit_type_attendance'), self.start, self.end)
        self.assertEqual(data['hours'], 168.0)

    def test_time_extra_benefit(self):
        start = datetime.strptime('2015-11-01 10:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        end = datetime.strptime('2015-11-01 17:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.tz)
        benef = self.env['hr.benefit'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type.id,
            'date_start': start,
            'date_stop': end,
        })
        benef.action_validate(benef.ids)
        data = self.richard_emp.get_benefit_days_data(self.benefit_type, self.start, self.end)
        self.assertEqual(data['hours'], 7.0)

    def test_time_week_leave_benefit(self):
        # /!\ this is a week day => it exists an calendar attendance at this time
        start = datetime.strptime('2015-11-02 10:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc) # UTC
        end = datetime.strptime('2015-11-02 17:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
        leave_benef = self.env['hr.benefit'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type_leave.id,
            'date_start': start,
            'date_stop': end,
        })
        leave_benef.action_validate(leave_benef.ids)
        data = self.richard_emp.get_benefit_days_data(self.benefit_type_leave, self.start, self.end)
        self.assertEqual(data['hours'], 5.0, "It should equal the number of hours richard should have worked")

    def test_time_weekend_leave_benefit(self):
        # /!\ this is in the weekend => no calendar attendance at this time
        start = datetime.strptime('2015-11-01 10:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc) # UTC
        end = datetime.strptime('2015-11-01 17:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
        leave_benef = self.env['hr.benefit'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'benefit_type_id': self.benefit_type_leave.id,
            'date_start': start,
            'date_stop': end,
        })
        leave_benef.action_validate(leave_benef.ids)
        data = self.richard_emp.get_benefit_days_data(self.benefit_type_leave, self.start, self.end)
        self.assertEqual(data['hours'], 0.0, "It should equal the number of hours richard should have worked")
