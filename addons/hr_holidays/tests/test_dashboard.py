from datetime import date, datetime

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestFutureLeavesCommon, TestHrHolidaysCommon


class TestDashboard(TestHrHolidaysCommon):
    def test_dashboard_special_days(self):
        self.uid = self.user_hrmanager.id
        employee = self.env.user.employee_id
        other_calendar = self.env['resource.calendar'].sudo().create({
            'name': 'Other calendar',
        })

        mandatory_day_vals = [
            {
                'name': 'Super Event (employee schedule)',
                'company_id': employee.company_id.id,
                'start_date': datetime(2021, 6, 12),
                'end_date': datetime(2021, 6, 12),
                'resource_calendar_id': employee.resource_calendar_id.id,
            },
            {
                'name': 'Super Event (no schedule)',
                'company_id': employee.company_id.id,
                'start_date': datetime(2021, 6, 12),
                'end_date': datetime(2021, 6, 12),
            },
            {
                'name': 'Super Event (other schedule)',
                'company_id': employee.company_id.id,
                'start_date': datetime(2021, 6, 12),
                'end_date': datetime(2021, 6, 12),
                'resource_calendar_id': other_calendar.id,
            }
        ]
        self.env['hr.leave.mandatory.day'].create(mandatory_day_vals)

        public_holiday_vals = [
            {
                'name': 'Public holiday (employee schedule)',
                'date_from': "2021-06-15 06:00:00",
                'date_to': "2021-06-15 15:00:00",
                'calendar_id': employee.resource_calendar_id.id,
            },
            {
                'name': 'Public holiday (no schedule)',
                'date_from': "2021-06-16 06:00:00",
                'date_to': "2021-06-16 15:00:00",
            },
            {
                'name': 'Public holiday (other schedule)',
                'date_from': "2021-06-17 06:00:00",
                'date_to': "2021-06-17 15:00:00",
                'calendar_id': other_calendar.id,
            },
        ]
        self.env['resource.calendar.leaves'].create(public_holiday_vals)

        dashboard_data = self.env['hr.employee'].get_special_days_data("2021-06-01", "2021-07-01")

        self.assertEqual({d["title"] for d in dashboard_data["mandatoryDays"]}, {'Super Event (employee schedule)', 'Super Event (no schedule)'})
        self.assertEqual({d["title"] for d in dashboard_data["bankHolidays"]}, {'Public holiday (employee schedule)', 'Public holiday (no schedule)'})


@tagged('post_install', '-at_install', 'time_off_dashboard', 'future_leaves')
class TestDashboardFutureLeaves(TestFutureLeavesCommon):
    """ The dashboard subtracts the future leaves linked to an accrual plan from the balance it displays.
    The validation of the requests, the crons and every other caller must keep their behavior.
    """

    @freeze_time('2026-09-29')
    def test_baseline_18_days_accrued_today(self):
        """ Verify the baseline accrued leave balance calculation as of today before any future requests. """
        self._create_allocation()
        info = self._get_info(from_dashboard=True)
        self.assertAlmostEqual(info['max_leaves'], 18)
        self.assertAlmostEqual(info['virtual_remaining_leaves'], 18)

    @freeze_time('2026-09-29')
    def test_future_leave_is_subtracted_on_dashboard_only(self):
        """ Test that future accrual leaves are deducted exclusively for dashboard callers while leaving backend calculations unchanged. """
        self._create_allocation()
        self._create_leave(date(2026, 11, 16), date(2026, 11, 17))

        dashboard = self._get_info(from_dashboard=True)
        other = self._get_info(from_dashboard=False)

        self.assertAlmostEqual(dashboard['virtual_remaining_leaves'], 16)
        self.assertAlmostEqual(dashboard['remaining_leaves'], 16)
        self.assertAlmostEqual(dashboard['leaves_approved'], 2)
        self.assertAlmostEqual(dashboard['leaves_requested'], 0)
        self.assertAlmostEqual(dashboard['max_leaves'], 18, msg="The allocated amount must not change")

        self.assertAlmostEqual(other['virtual_remaining_leaves'], 18)
        self.assertAlmostEqual(other['leaves_approved'], 0)
        self.assertAlmostEqual(other['future_accrual_leaves'], 2)

    @freeze_time('2026-09-29')
    def test_dashboard_entry_point(self):
        """ Verify that the dashboard RPC entry point correctly returns the deducted balance for future accrual requests. """
        self._create_allocation()
        self._create_leave(date(2026, 11, 16), date(2026, 11, 17))
        employee_model = self.env['hr.employee'].with_context(employee_id=self.employee.id, from_dashboard=True)
        allocation_data = employee_model.get_time_off_dashboard_data()['allocation_data']

        info = next(info for _name, info, _requires_allocation, type_id in allocation_data
                    if type_id == self.work_entry_type.id)
        self.assertAlmostEqual(info['virtual_remaining_leaves'], 16)

    @freeze_time('2026-09-29')
    def test_dashboard_balance_can_be_negative(self):
        """ Verify that the dashboard displays a negative balance when future accrual requests exceed today's accrued amount. """
        self._create_allocation()
        leaves = self.env['hr.leave']
        for date_from, date_to in (
            (date(2026, 11, 16), date(2026, 11, 20)),
            (date(2026, 11, 23), date(2026, 11, 27)),
            (date(2026, 12, 7), date(2026, 12, 11)),
            (date(2026, 12, 14), date(2026, 12, 18)),
        ):
            leaves |= self._create_leave(date_from, date_to)

        dashboard = self._get_info(from_dashboard=True)
        other = self._get_info(from_dashboard=False)

        self.assertEqual(set(leaves.mapped('state')), {'validate'})
        self.assertAlmostEqual(dashboard['virtual_remaining_leaves'], -2)
        self.assertAlmostEqual(other['virtual_remaining_leaves'], 18)

    @freeze_time('2026-09-29')
    def test_validation_still_blocks_when_not_enough_accrued(self):
        """ Verify that backend leave validation blocks requests when total planned leaves exceed future accrued amounts. """
        self._create_allocation()
        for date_from, date_to in (
            (date(2026, 11, 16), date(2026, 11, 20)),
            (date(2026, 11, 23), date(2026, 11, 27)),
            (date(2026, 12, 7), date(2026, 12, 11)),
            (date(2026, 12, 14), date(2026, 12, 18)),
        ):
            self._create_leave(date_from, date_to)

        with self.assertRaises(ValidationError):
            self._create_leave(date(2026, 12, 21), date(2026, 12, 25))

    @freeze_time('2026-09-29')
    def test_validation_same_result_with_dashboard_flag(self):
        """ Ensure that passing the dashboard context flag during creation does not alter backend validation restrictions. """
        self._create_allocation()
        for date_from, date_to in (
            (date(2026, 11, 16), date(2026, 11, 20)),
            (date(2026, 11, 23), date(2026, 11, 27)),
            (date(2026, 12, 7), date(2026, 12, 11)),
            (date(2026, 12, 14), date(2026, 12, 18)),
        ):
            self._create_leave(date_from, date_to)

        with self.assertRaises(ValidationError):
            self._create_leave(date(2026, 12, 21), date(2026, 12, 25), from_dashboard=True)

    @freeze_time('2026-09-29')
    def test_cancel_invalid_leaves_cron_unchanged(self):
        """ Verify that the automated cleanup cron retains valid future accrual leaves without canceling them. """
        self._create_allocation()
        leave = self._create_leave(date(2026, 10, 12), date(2026, 10, 13))
        self.env['hr.leave']._cancel_invalid_leaves()
        self.assertEqual(leave.state, 'validate')

    @freeze_time('2026-09-29')
    def test_dropdown_label(self):
        """ Test that time off selection dropdown labels correctly reflect the net balance deducting future accrual requests. """
        self._create_allocation()
        self._create_leave(date(2026, 11, 16), date(2026, 11, 17))
        work_entry_type = self.work_entry_type.with_context(
            employee_id=self.employee.id, leave_date_from=date(2026, 10, 12))

        self.assertAlmostEqual(work_entry_type.max_leaves, 20)
        self.assertAlmostEqual(work_entry_type.virtual_remaining_leaves, 20)
        self.assertAlmostEqual(work_entry_type.display_virtual_remaining_leaves, 18)
        self.assertEqual(work_entry_type.remaining_leaves_label, "18 days left")

    @freeze_time('2026-09-29')
    def test_selectable_type_takes_future_leaves_into_account(self):
        """ Verify that selection domains filter out leave types with no net remaining balance after deducting future requests. """
        self._create_allocation()
        for date_from, date_to in (
            (date(2026, 11, 16), date(2026, 11, 20)),
            (date(2026, 11, 23), date(2026, 11, 27)),
            (date(2026, 12, 7), date(2026, 12, 11)),
            (date(2026, 12, 14), date(2026, 12, 18)),
        ):
            self._create_leave(date_from, date_to)

        work_entry_types = self.env['hr.work.entry.type'].with_context(
            employee_id=self.employee.id, leave_date_from=date(2026, 10, 12))
        displayed_domain = [('id', '=', self.work_entry_type.id), ('display_virtual_remaining_leaves', '>', 0)]
        real_domain = [('id', '=', self.work_entry_type.id), ('virtual_remaining_leaves', '>', 0)]
        self.assertFalse(work_entry_types.search(displayed_domain))
        # the balance used by the validation is not changed
        self.assertTrue(work_entry_types.search(real_domain))

        work_entry_types = work_entry_types.with_context(leave_date_from=date(2026, 12, 21))
        self.assertTrue(work_entry_types.search(displayed_domain))

    def _create_leaves_in_december_on_negative_type(self):
        """ Create 19 days of December leave requests on a leave type allowing negative balances. """
        for date_from, date_to in (
            (date(2026, 12, 7), date(2026, 12, 11)),
            (date(2026, 12, 14), date(2026, 12, 18)),
            (date(2026, 12, 21), date(2026, 12, 25)),
            (date(2026, 12, 28), date(2026, 12, 31)),
        ):
            self._create_leave(date_from, date_to, work_entry_type=self.negative_work_entry_type)

    @freeze_time('2026-09-29')
    def test_negative_type_validation_without_flag(self):
        """ Ensure leave validation for negative-allowed types considers accruals at request date independently of future leaves. """
        self._create_allocation(self.negative_work_entry_type, self.negative_accrual_plan)
        self._create_leaves_in_december_on_negative_type()
        leave = self._create_leave(
            date(2026, 11, 16), date(2026, 11, 20), work_entry_type=self.negative_work_entry_type)
        self.assertEqual(leave.state, 'validate')

    @freeze_time('2026-09-29')
    def test_negative_type_validation_ignores_dashboard_flag(self):
        """ Ensure the dashboard context flag does not affect backend validation logic for negative-allowed leave types. """
        self._create_allocation(self.negative_work_entry_type, self.negative_accrual_plan)
        self._create_leaves_in_december_on_negative_type()
        leave = self._create_leave(
            date(2026, 11, 16), date(2026, 11, 20),
            work_entry_type=self.negative_work_entry_type, from_dashboard=True)
        self.assertEqual(leave.state, 'validate')

    @freeze_time('2026-09-29')
    def test_hours_future_leave_is_subtracted_on_dashboard_only(self):
        """ Test that future accrual leaves for hour based types are deducted exclusively for dashboard display. """
        self._create_allocation(self.hour_work_entry_type, self.hour_accrual_plan)
        self._create_leave(date(2026, 11, 16), date(2026, 11, 17), work_entry_type=self.hour_work_entry_type)

        dashboard = self._get_info(from_dashboard=True, work_entry_type=self.hour_work_entry_type)
        other = self._get_info(from_dashboard=False, work_entry_type=self.hour_work_entry_type)

        self.assertEqual(dashboard['unit_of_measure'], 'hour')
        self.assertAlmostEqual(dashboard['virtual_remaining_leaves'], 128)
        self.assertAlmostEqual(dashboard['remaining_leaves'], 128)
        self.assertAlmostEqual(dashboard['leaves_approved'], 16)
        self.assertAlmostEqual(dashboard['leaves_requested'], 0)
        self.assertAlmostEqual(dashboard['max_leaves'], 144, msg="The allocated amount must not change")

        self.assertAlmostEqual(other['virtual_remaining_leaves'], 144)
        self.assertAlmostEqual(other['leaves_approved'], 0)
        self.assertAlmostEqual(other['future_accrual_leaves'], 16)

    @freeze_time('2026-09-29')
    def test_hours_dashboard_balance_can_be_negative(self):
        """ Verify that the dashboard allows displaying a negative balance for hour based time types. """
        self._create_allocation(self.hour_work_entry_type, self.hour_accrual_plan)
        self._create_planned_leaves(self.hour_work_entry_type)

        dashboard = self._get_info(from_dashboard=True, work_entry_type=self.hour_work_entry_type)
        other = self._get_info(from_dashboard=False, work_entry_type=self.hour_work_entry_type)

        self.assertAlmostEqual(dashboard['virtual_remaining_leaves'], -16)
        self.assertAlmostEqual(other['virtual_remaining_leaves'], 144)

    @freeze_time('2026-09-29')
    def test_hours_custom_hours_leave(self):
        """ Test that custom-hour future leaves are properly deducted from the dashboard balance. """
        self._create_allocation(self.custom_hours_work_entry_type, self.custom_hours_accrual_plan)
        leave = self._create_leave(
            date(2026, 11, 16), date(2026, 11, 16), work_entry_type=self.custom_hours_work_entry_type,
            request_hour_from=9.0, request_hour_to=12.0)
        self.assertAlmostEqual(leave.number_of_hours, 3)

        dashboard = self._get_info(
            from_dashboard=True, work_entry_type=self.custom_hours_work_entry_type)
        other = self._get_info(
            from_dashboard=False, work_entry_type=self.custom_hours_work_entry_type)

        self.assertAlmostEqual(dashboard['virtual_remaining_leaves'], 141)
        self.assertAlmostEqual(other['virtual_remaining_leaves'], 144)
        self.assertAlmostEqual(other['future_accrual_leaves'], 3)

    @freeze_time('2026-09-29')
    def test_hours_validation_still_blocks_when_not_enough_accrued(self):
        """ Verify that backend validation still blocks hour based requests exceeding future accrual limits. """
        self._create_allocation(self.hour_work_entry_type, self.hour_accrual_plan)
        self._create_planned_leaves(self.hour_work_entry_type)
        with self.assertRaises(ValidationError):
            self._create_leave(date(2026, 12, 21), date(2026, 12, 25), work_entry_type=self.hour_work_entry_type)

    @freeze_time('2026-09-29')
    def test_hours_dropdown_label(self):
        """ Test that dropdown selection labels correctly reflect the net remaining balance for hour based types. """
        self._create_allocation(self.hour_work_entry_type, self.hour_accrual_plan)
        self._create_leave(date(2026, 11, 16), date(2026, 11, 17), work_entry_type=self.hour_work_entry_type)
        work_entry_type = self.hour_work_entry_type.with_context(
            employee_id=self.employee.id, leave_date_from=date(2026, 10, 12))

        self.assertAlmostEqual(work_entry_type.max_leaves, 160)
        self.assertAlmostEqual(work_entry_type.virtual_remaining_leaves, 160)
        self.assertAlmostEqual(work_entry_type.display_virtual_remaining_leaves, 144)
        self.assertEqual(work_entry_type.remaining_leaves_label, "144 hours left")

    @freeze_time('2026-09-29')
    def test_hours_selectable_type_takes_future_leaves_into_account(self):
        """ Verify that selection domains filter out hour based leave types with no net remaining balance. """
        self._create_allocation(self.hour_work_entry_type, self.hour_accrual_plan)
        self._create_planned_leaves(self.hour_work_entry_type)

        work_entry_types = self.env['hr.work.entry.type'].with_context(
            employee_id=self.employee.id, leave_date_from=date(2026, 10, 12))
        displayed_domain = [('id', '=', self.hour_work_entry_type.id), ('display_virtual_remaining_leaves', '>', 0)]
        real_domain = [('id', '=', self.hour_work_entry_type.id), ('virtual_remaining_leaves', '>', 0)]
        self.assertFalse(work_entry_types.search(displayed_domain))
        self.assertTrue(work_entry_types.search(real_domain))

        work_entry_types = work_entry_types.with_context(leave_date_from=date(2026, 12, 21))
        self.assertTrue(work_entry_types.search(displayed_domain))


@tagged('post_install', '-at_install', 'future_leaves', 'time_off_display')
class TestHrEmployeeAllocationDisplay(TestFutureLeavesCommon):
    """ The time off smart button has to subtracts the future leaves linked to an accrual plan. """

    def _get_smart_button_values(self):
        self.employee.invalidate_recordset(['allocation_remaining_display', 'allocation_display'])
        return self.employee.allocation_remaining_display, self.employee.allocation_display

    @freeze_time('2026-09-29')
    def test_employee_smart_button_subtracts_future_leaves(self):
        """ Test that the employee smart button deducts future accrual leave requests from the remaining balance. """
        self._create_allocation()
        self.assertEqual(self._get_smart_button_values(), ('18', '18'))

        self._create_leave(date(2026, 11, 16), date(2026, 11, 17))
        self.assertEqual(self._get_smart_button_values(), ('16', '18'))

    @freeze_time('2026-09-29')
    def test_employee_smart_button_can_be_negative(self):
        """ Verify that the employee smart button displays a negative balance when future requests exceed current accruals. """
        self._create_allocation()
        self._create_planned_leaves(self.work_entry_type)
        self.assertEqual(self._get_smart_button_values(), ('-2', '18'))

    @freeze_time('2026-09-29')
    def test_employee_smart_button_hours(self):
        """ Test that future leave requests for hour-based types are converted to days for the smart button display. """
        self._create_allocation(self.hour_work_entry_type, self.hour_accrual_plan)
        self._create_leave(date(2026, 11, 16), date(2026, 11, 17), work_entry_type=self.hour_work_entry_type)
        self.assertEqual(self._get_smart_button_values(), ('16', '18'))
