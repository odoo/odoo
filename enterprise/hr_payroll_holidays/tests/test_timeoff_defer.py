# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.exceptions import ValidationError, UserError
from odoo.fields import Datetime
from odoo.tests.common import tagged
from odoo.addons.hr_payroll_holidays.tests.common import TestPayrollHolidaysBase

from dateutil.relativedelta import relativedelta


@tagged('post_install', '-at_install')
class TestTimeoffDefer(TestPayrollHolidaysBase):

    def test_no_defer(self):
        #create payslip -> waiting or draft
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': (date.today() + relativedelta(day=13)),
            'request_date_to': (date.today() + relativedelta(day=16)),
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_to_defer(self):
        #create payslip
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()
        payslip.action_payslip_done()

        #create a time off for our employee, validating it now should put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': (date.today() + relativedelta(day=13)),
            'request_date_to': (date.today() + relativedelta(day=16)),
        })
        leave.action_approve()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

    def test_multi_payslip_defer(self):
        #A leave should only be set to defer if ALL colliding with the time period of the time off are in a done state
        # it should not happen if a payslip for that time period is still in a waiting state

        #create payslip -> waiting
        waiting_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip draft',
            'employee_id': self.emp.id,
        })
        #payslip -> done
        done_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip done',
            'employee_id': self.emp.id,
        })

        # Puts the waiting payslip to draft/waiting
        waiting_payslip.compute_sheet()
        # Puts the done payslip to the done state
        done_payslip.compute_sheet()
        done_payslip.action_payslip_done()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': (date.today() + relativedelta(day=13)),
            'request_date_to': (date.today() + relativedelta(day=16)),
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_payslip_paid_past(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })

        payslip.compute_sheet()
        self.assertEqual(payslip.state, 'verify')

        leave_1 = self.env['hr.leave'].with_user(self.vlad).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': '2022-01-12',
            'request_date_to': '2022-01-12',
        })
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave_1.sudo().action_validate()
        self.assertEqual(leave_1.payslip_state, 'blocked', 'Leave should be to defer')

        # A Simple User can request a leave if a payslip is paid
        leave_2 = self.env['hr.leave'].with_user(self.vlad).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': '2022-01-19',
            'request_date_to': '2022-01-19',
        })
        leave_2.sudo().action_validate()
        self.assertEqual(leave_2.payslip_state, 'blocked', 'Leave should be to defer')

        # Check overlapping periods with no payslip
        leave_3 = self.env['hr.leave'].with_user(self.vlad).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': '2022-01-31',
            'request_date_to': '2022-02-01',
        })
        leave_3.sudo().action_validate()
        self.assertEqual(leave_3.payslip_state, 'blocked', 'Leave should be to defer')

        leave_4 = self.env['hr.leave'].with_user(self.vlad).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': '2021-01-31',
            'request_date_to': '2022-01-03',
        })
        leave_4.sudo().action_validate()
        self.assertEqual(leave_4.payslip_state, 'blocked', 'Leave should be to defer')

    def test_report_to_next_month(self):
        self.emp.contract_ids.generate_work_entries(date(2022, 1, 1), date(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 31),
            'request_date_to': date(2022, 1, 31),
            'request_hour_from': 7,
            'request_hour_to': 18,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        leave.action_report_to_next_month()
        reported_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2022-02-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2022-02-28'), datetime.max.time()))
        ])
        self.assertEqual(reported_work_entries[0].date_start, datetime(2022, 2, 1, 7, 0))
        self.assertEqual(reported_work_entries[0].date_stop, datetime(2022, 2, 1, 11, 0))
        self.assertEqual(reported_work_entries[1].date_start, datetime(2022, 2, 1, 12, 0))
        self.assertEqual(reported_work_entries[1].date_stop, datetime(2022, 2, 1, 16, 0))

    def test_report_to_next_month_overlap(self):
        """
        If the time off overlap over 2 months, only report the exceeding part from january
        In case leaves go over two months, only the leaves that are in the first month should be defered
        """
        self.emp.contract_ids.generate_work_entries(date(2022, 1, 1), date(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 31),
            'request_date_to': date(2022, 2, 2),
            'request_hour_from': 7,
            'request_hour_to': 18,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        leave.action_report_to_next_month()
        reported_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2022-02-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2022-02-28'), datetime.max.time()))
        ])
        self.assertEqual(len(reported_work_entries), 6)
        self.assertEqual(list({we.date_start.day for we in reported_work_entries}), [1, 2, 3])
        self.assertEqual(reported_work_entries[0].date_start, datetime(2022, 2, 1, 7, 0))
        self.assertEqual(reported_work_entries[0].date_stop, datetime(2022, 2, 1, 11, 0))
        self.assertEqual(reported_work_entries[1].date_start, datetime(2022, 2, 1, 12, 0))
        self.assertEqual(reported_work_entries[1].date_stop, datetime(2022, 2, 1, 16, 0))

    def test_report_to_next_month_not_enough_days(self):
        # If the time off contains too many days to be reported to next months, raise
        self.emp.contract_ids.generate_work_entries(date(2022, 1, 1), date(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 1),
            'request_date_to': date(2022, 1, 31),
            'request_hour_from': 7,
            'request_hour_to': 18,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        with self.assertRaises(UserError):
            leave.action_report_to_next_month()

    def test_report_to_next_month_long_time_off(self):
        # If the time off overlap over more than 2 months, raise
        self.emp.contract_ids.generate_work_entries(date(2022, 1, 1), date(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 1),
            'request_date_to': date(2022, 3, 10),
            'request_hour_from': 7,
            'request_hour_to': 18,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        with self.assertRaises(UserError):
            leave.action_report_to_next_month()

    def test_report_to_next_month_half_days(self):
        self.leave_type.request_unit = 'half_day'
        self.emp.contract_ids.generate_work_entries(date(2022, 1, 1), date(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': date(2022, 1, 31),
            'request_date_to': date(2022, 1, 31),
            'request_unit_half': True,
            'request_date_from_period': 'am',
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))

        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        leave.action_report_to_next_month()
        reported_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2022-02-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2022-02-28'), datetime.max.time()))
        ])
        self.assertEqual(len(reported_work_entries), 1)
        self.assertEqual(reported_work_entries[0].date_start, datetime(2022, 2, 1, 7, 0))
        self.assertEqual(reported_work_entries[0].date_stop, datetime(2022, 2, 1, 11, 0))

    def test_defer_next_month_double_time_off(self):
        """
         If you have a time off 5 days on Jun and 3 days on july, when you "defer it to next month"
         it's only the 5 days of Jun that should be postponed to july.
         """
        self.emp.contract_ids._generate_work_entries(datetime(2023, 6, 1), datetime(2023, 7, 31))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2023-06-01',
            'date_to': '2023-06-30',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave_data = [{
            'name': 'Paid Time Off',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2023-06-26 00:00:00',
            'request_date_to': '2023-06-30 23:59:59',
            }, {
            'name': 'Paid Time Off',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2023-07-03 00:00:00',
            'request_date_to': '2023-07-05 23:59:59',
            }]
        leaves = self.env['hr.leave'].create(leave_data)
        leaves.action_validate()
        leaves[0].action_report_to_next_month()
        # reported work entries between the 1st of july 2023 to the 31st of july 2023
        july_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2023-07-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2023-07-31'), datetime.max.time()))
        ])
        # The length of reported work entries is 16 because we are generating records for 8 days of leave.
        # Each day is divided into two parts, morning and afternoon, resulting in a total of 16 work entries.
        # These leaves cover the period from July 3rd to July 12th, excluding July 1st and 2nd as they are designated holidays.
        self.assertEqual(len(july_work_entries), 16)
        self.assertEqual(list({we.date_start.day for we in july_work_entries}), [3, 4, 5, 6, 7, 10, 11, 12])
        self.assertEqual(july_work_entries[0].date_start, datetime(2023, 7, 3, 6, 0))
        self.assertEqual(july_work_entries[0].date_stop, datetime(2023, 7, 3, 10, 0))
        self.assertEqual(july_work_entries[1].date_start, datetime(2023, 7, 3, 11, 0))
        self.assertEqual(july_work_entries[1].date_stop, datetime(2023, 7, 3, 15, 0))

    def test_leave_overlaping_over_2_month(self):
        """
        The part of the leave in the first month closed by a payslip should be deferred on the next month.

        - A leave for the 2 whole weeks (2025-05-26 -> 2025-06-06) overlapping over 2 months
        - May payslip computed and validated
        - Compute the payslip of June

        5 leave day from May should be deferred and added to the leave of june on work entries and payslip of june.
        This should results in 10 leave day on June.
        """
        # Generate the work entries
        may_work_entries = self.emp.contract_ids._generate_work_entries(
            datetime.fromisoformat('2025-05-01'),
            datetime.fromisoformat('2025-05-31')
        )
        june_work_entries = self.emp.contract_ids._generate_work_entries(
            datetime.fromisoformat('2025-06-01'),
            datetime.fromisoformat('2025-06-30')
        )
        self.assertRecordValues((may_work_entries + june_work_entries).work_entry_type_id, [{'code': 'WORK100'}])
        self.assertEqual(set(may_work_entries.mapped('state')), {'draft'})

        # Create and validate payslips like an HR user would do:
        # create a payslip batch, gets the payslips created through the wizard call and validate the batch
        may_payslip_batch = self.env['hr.payslip.run'].create({
            'name': 'May 2025 payslip batch',
            'date_start': '2025-05-01',
            'date_end': '2025-05-31',
            'company_id': self.emp.company_id.id,
        })
        self.env['hr.payslip.employees'].with_context(active_id=may_payslip_batch.id).create({
            'employee_ids': self.emp.ids,  # We only do it for one employee to avoid side effects from the setup
        }).compute_sheet()
        may_payslip_batch.action_validate()
        self.assertEqual(set(may_work_entries.mapped('state')), {'validated'})

        # Create a time off overlaping over 2 months
        overlapping_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Annoying overlaping work entry type',
            'is_leave': True,
            'code': 'OVERLAPING101',
        })
        overlapping_leave_type = self.env['hr.leave.type'].create({
            'name': 'Annoying overlaping leave type',
            'work_entry_type_id': overlapping_work_entry_type.id,
            'time_type': 'leave',
            'requires_allocation': 'no',
        })
        overlapping_leave = self.env['hr.leave'].create({
            'name': 'Annoying overlaping leave',
            'holiday_status_id': overlapping_leave_type.id,
            'employee_id': self.emp.id,
            'date_from': '2025-05-26 00:00:01',
            'date_to': '2025-06-06 23:59:59',
            'request_date_from': '2025-05-26 00:00:01',
            'request_date_to': '2025-06-06 23:59:59',
        })
        overlapping_leave.action_approve()
        self.assertEqual(overlapping_leave.payslip_state, 'blocked', 'Leave should be to defer')

        # Defer the blocked time off
        overlapping_leave.action_report_to_next_month()

        # Ensure the timeoff work entries have been deferred on June and that May stays untouched
        self.assertEqual(len(june_work_entries.filtered(lambda we: we.work_entry_type_id.code == 'OVERLAPING101')),
                         20, "There should only have 20 OVERLAPING101 work entry deferred (2 Work entry per leave day)")

        # Ensure the worked days lines gets computed correctly on June payslip
        june_payslip_batch = self.env['hr.payslip.run'].create({
            'name': 'June 2025 payslip batch',
            'date_start': '2025-06-01',
            'date_end': '2025-06-30',
        })
        self.env['hr.payslip.employees'].with_context(active_id=june_payslip_batch.id).create({
            'employee_ids': self.emp.ids,  # We only do it for one employee to avoid side effects from the setup
        }).compute_sheet()
        june_payslip_batch.action_validate()
        payslip = june_payslip_batch.slip_ids
        self.assertEqual(
            set(payslip.worked_days_line_ids.mapped('number_of_days')),
            {10, 11},
            "There should be 10 timeoff (5 from may and 5 from june) and 11 Attendances (21 - 10) on the payslip"
        )

    def test_timeoff_overlaping_with_a_public_holiday_shouldnt_be_deferred(self):
        """
        A leave overlaping on a public holiday shouldn't be deferred as the public holiday was already a leave.

        - Public holiday on Thursday 2025-05-29 with code LEAVECANTMISS3000
        - May payslip already computed and validated
        - A leave for the 2 whole weeks (2025-05-26 -> 2025-06-06) overlapping with the Public holiday
        - Compute the payslip of June

        Only 4 leave day from May should be deferred on work entries and payslip of june.
        """
        # Register a public holiday with a specific work entry type
        self.env['resource.calendar.leaves'].create({
            'name': "Supreme leader party you can't miss",
            'date_from': Datetime.from_string('2025-05-29 00:00:00'),
            'date_to': Datetime.from_string('2025-05-29 23:59:59'),
            'work_entry_type_id': self.env['hr.work.entry.type'].create({
                'name': "Public holiday leaves that can't be missed",
                'code': 'LEAVECANTMISS3000',
                'is_leave': True,
            }).id,
        })

        # Generate the work entries
        may_work_entries = self.emp.contract_ids._generate_work_entries(
            datetime.fromisoformat('2025-05-01'),
            datetime.fromisoformat('2025-05-31')
        )
        june_work_entries = self.emp.contract_ids._generate_work_entries(
            datetime.fromisoformat('2025-06-01'),
            datetime.fromisoformat('2025-06-30')
        )

        # Ensure the public holiday was taken into account
        self.assertRecordValues(may_work_entries.work_entry_type_id, [{'code': 'WORK100'}, {'code': 'LEAVECANTMISS3000'}])
        self.assertRecordValues(june_work_entries.work_entry_type_id, [{'code': 'WORK100'}])

        # Create and validate payslips like an HR user would do:
        # create a payslip batch, gets the payslips created through the wizard call and validate the batch
        may_payslip_batch = self.env['hr.payslip.run'].create({
            'name': 'May 2025 payslip batch',
            'date_start': '2025-05-01',
            'date_end': '2025-05-31',
            'company_id': self.emp.company_id.id,
        })
        self.env['hr.payslip.employees'].with_context(active_id=may_payslip_batch.id).create({
            'employee_ids': self.emp.ids,  # We only do it for one employee to avoid side effects from the setup
        }).compute_sheet()
        may_payslip_batch.action_validate()

        # Create a time off overlaping with the public holiday
        overlapping_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Annoying overlaping work entry type',
            'is_leave': True,
            'code': 'OVERLAPING101',
        })
        overlapping_leave_type = self.env['hr.leave.type'].create({
            'name': 'Annoying overlaping leave type',
            'work_entry_type_id': overlapping_work_entry_type.id,
            'time_type': 'leave',
            'requires_allocation': 'no',
        })
        overlapping_leave = self.env['hr.leave'].create({
            'name': 'Annoying overlaping leave',
            'holiday_status_id': overlapping_leave_type.id,
            'employee_id': self.emp.id,
            'date_from': '2025-05-26 00:00:01',
            'date_to': '2025-06-06 23:59:59',
            'request_date_from': '2025-05-26 00:00:01',
            'request_date_to': '2025-06-06 23:59:59',
        })
        overlapping_leave.action_approve()
        self.assertEqual(overlapping_leave.payslip_state, 'blocked', 'Leave should be to defer')

        # Defer the blocked time off
        overlapping_leave.action_report_to_next_month()

        # Ensure the timeoff work entries have been deferred on June and that May stays untouched
        self.assertEqual(set(may_work_entries.work_entry_type_id.mapped('code')),
                         {'WORK100', 'LEAVECANTMISS3000'}, "Nothing should have changed regarding May work entries")
        self.assertEqual(set(june_work_entries.work_entry_type_id.mapped('code')),
                         {'WORK100', 'OVERLAPING101'}, "June work entries should contain the deferred work entries from May")
        self.assertEqual(len(june_work_entries.filtered(lambda we: we.work_entry_type_id.code == 'OVERLAPING101')),
                         18, "There should only have 18 OVERLAPING101 work entry deferred (2 Work entry per leave day)")

        # Ensure the worked days lines gets computed correctly on June payslip
        june_payslip_batch = self.env['hr.payslip.run'].create({
            'name': 'June 2025 payslip batch',
            'date_start': '2025-06-01',
            'date_end': '2025-06-30',
        })
        self.env['hr.payslip.employees'].with_context(active_id=june_payslip_batch.id).create({
            'employee_ids': self.emp.ids,  # We only do it for one employee to avoid side effects from the setup
        }).compute_sheet()
        june_payslip_batch.action_validate()
        payslip = june_payslip_batch.slip_ids
        self.assertEqual(set(payslip.worked_days_line_ids.mapped('number_of_days')),
                         {9, 12}, "There should be 9 timeoff and 12 Attendances on the payslip")
