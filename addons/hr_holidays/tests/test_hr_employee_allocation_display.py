from datetime import date
from freezegun import freeze_time

from odoo.addons.hr_holidays.tests.common import TestFutureLeavesCommon
from odoo.tests import tagged


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
