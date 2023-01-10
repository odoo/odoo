# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


@tagged('work_entry_multi_contract')
class TestWorkEntryHolidaysMultiContract(TestWorkEntryHolidaysBase):

    def setUp(self):
        super().setUp()
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': 'no',
            'work_entry_type_id': self.work_entry_type_leave.id
        })

    def create_leave(self, start, end):
        work_days_data = self.jules_emp._get_work_days_data_batch(start, end)
        return self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': start,
            'date_to': end,
            'number_of_days': work_days_data[self.jules_emp.id]['days'],
        })

    def test_multi_contract_holiday(self):
        # Leave during second contract
        leave = self.create_leave(datetime(2015, 11, 17, 7, 0), datetime(2015, 11, 20, 18, 0))
        leave.action_approve()
        start = datetime.strptime('2015-11-01', '%Y-%m-%d')
        end_generate = datetime(2015, 11, 30, 23, 59, 59)
        work_entries = self.jules_emp.contract_ids._generate_work_entries(start, end_generate)
        work_entries.action_validate()
        work_entries = work_entries.filtered(lambda we: we.contract_id == self.contract_cdi)

        work = work_entries.filtered(lambda line: line.work_entry_type_id == self.env.ref('hr_work_entry.work_entry_type_attendance'))
        leave = work_entries.filtered(lambda line: line.work_entry_type_id == self.work_entry_type_leave)
        self.assertEqual(sum(work.mapped('duration')), 49, "It should be 49 hours of work this month for this contract")
        self.assertEqual(sum(leave.mapped('duration')), 28, "It should be 28 hours of leave this month for this contract")

    def test_move_contract_in_leave(self):
        # test move contract dates such that a leave is across two contracts
        start = datetime.strptime('2015-11-05 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.contract_cdi.write({'date_start': datetime.strptime('2015-12-30', '%Y-%m-%d').date()})
        # begins during contract, ends after contract
        leave = self.create_leave(start, end)
        leave.action_approve()
        # move contract in the middle of the leave
        with self.assertRaises(ValidationError):
            self.contract_cdi.date_start = datetime.strptime('2015-11-17', '%Y-%m-%d').date()

    def test_create_contract_in_leave(self):
        # test create contract such that a leave is across two contracts
        start = datetime.strptime('2015-11-05 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.contract_cdi.date_start = datetime.strptime('2015-12-30', '%Y-%m-%d').date()  # remove this contract to be able to create the leave
        # begins during contract, ends after contract
        leave = self.create_leave(start, end)
        leave.action_approve()
        # move contract in the middle of the leave
        with self.assertRaises(ValidationError):
            self.env['hr.contract'].create({
                'date_start': datetime.strptime('2015-11-30', '%Y-%m-%d').date(),
                'name': 'Contract for Richard',
                'resource_calendar_id': self.calendar_40h.id,
                'wage': 5000.0,
                'employee_id': self.jules_emp.id,
                'state': 'open',
                'date_generated_from': datetime.strptime('2015-11-30', '%Y-%m-%d'),
                'date_generated_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
            })

    def test_leave_outside_contract(self):
        # Leave outside contract => should not raise
        start = datetime.strptime('2014-10-18 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2014-10-20 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

        # begins before contract, ends during contract => should not raise
        start = datetime.strptime('2014-10-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-01-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

        # begins during contract, ends after contract => should not raise
        self.contract_cdi.date_end = datetime.strptime('2015-11-30', '%Y-%m-%d').date()
        start = datetime.strptime('2015-11-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-5 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

    def test_no_leave_overlapping_contracts(self):
        with self.assertRaises(ValidationError):
            # Overlap two contracts
            start = datetime.strptime('2015-11-12 07:00:00', '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime('2015-11-17 18:00:00', '%Y-%m-%d %H:%M:%S')
            self.create_leave(start, end)

        # Leave inside fixed term contract => should not raise
        start = datetime.strptime('2015-11-04 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-07 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

        # Leave inside contract (no end) => should not raise
        start = datetime.strptime('2015-11-18 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-20 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

    def test_leave_request_next_contracts(self):
        start = datetime.strptime('2015-11-23 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-24 18:00:00', '%Y-%m-%d %H:%M:%S')
        leave = self.create_leave(start, end)

        leave._compute_number_of_hours_display()
        self.assertEqual(leave.number_of_hours_display, 14, "It should count hours according to the future contract.")

    def test_leave_multi_contracts_same_schedule(self):
        # Allow leaves overlapping multiple contracts if same
        # resource calendar
        leave = self.create_leave(datetime(2022, 6, 1, 7, 0, 0), datetime(2022, 6, 30, 18, 0, 0))
        leave.action_approve()
        self.contract_cdi.date_end = date(2022, 6, 15)

        new_contract_cdi = self.env['hr.contract'].create({
            'date_start': date(2022, 6, 16),
            'name': 'New Contract for Jules',
            'resource_calendar_id': self.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': self.jules_emp.id,
            'state': 'draft',
            'kanban_state': 'normal',
        })
        new_contract_cdi.state = 'open'

    def test_leave_multi_contracts_split(self):
        # Check that setting a contract as running correctly
        # splits the existing time off for this employee that
        # are ovelapping with another contract with another
        # working schedule
        leave = self.create_leave(datetime(2022, 6, 1, 5, 0, 0), datetime(2022, 6, 30, 20, 0, 0))
        leave.action_approve()
        self.assertEqual(leave.number_of_days, 22)
        self.assertEqual(leave.state, 'validate')

        self.contract_cdi.date_end = date(2022, 6, 15)
        new_contract_cdi = self.env['hr.contract'].create({
            'date_start': date(2022, 6, 16),
            'name': 'New Contract for Jules',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': self.jules_emp.id,
            'state': 'draft',
            'kanban_state': 'normal',
        })
        new_contract_cdi.state = 'open'

        leaves = self.env['hr.leave'].search([('employee_id', '=', self.jules_emp.id)])
        self.assertEqual(len(leaves), 3)
        self.assertEqual(leave.state, 'refuse')
        first_leave = leaves.filtered(lambda l: l.date_from.day == 1 and l.date_to.day == 15)
        self.assertEqual(first_leave.state, 'validate')
        self.assertEqual(first_leave.number_of_days, 11)
        second_leave = leaves.filtered(lambda l: l.date_from.day == 16 and l.date_to.day == 30)
        self.assertEqual(second_leave.state, 'validate')
        self.assertEqual(second_leave.number_of_days, 11)
