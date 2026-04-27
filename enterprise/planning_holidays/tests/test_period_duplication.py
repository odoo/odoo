# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.planning.tests.test_period_duplication import TestPeriodDuplication


class TestPeriodDuplicationHolidays(TestPeriodDuplication):
    def test_duplication_should_create_open_shift_when_time_off(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2023, 7, 24, 0, 0)
        slot = PlanningSlot.create({
            'resource_id': self.resource_joseph.id,
            'start_datetime': dt + relativedelta(hours=9),
            'end_datetime': dt + relativedelta(hours=15),
        })
        self.env.user.tz = 'UTC'
        self.env['hr.leave'].create({
            'name': 'Time Off',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_sl').id,
            'request_date_from': dt + relativedelta(weeks=1),
            'request_date_to': dt + relativedelta(weeks=1, days=1),
            'employee_id': self.employee_joseph.id,
        }).action_validate()
        copied, _dummy = PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', self.resource_joseph.id],
            ]
        )
        self.assertEqual(len(copied), 1, "2 slots should be generated")
        copied_slot = PlanningSlot.browse(copied)
        self.assertFalse(copied_slot.resource_id, "The shifts should be copied as open, as the employees are on time off")
        self.assertEqual(slot.allocated_hours, copied_slot.allocated_hours, "The allocated hours should stay unchanged")

    def test_duplication_should_not_create_shift_when_holiday(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2023, 7, 24, 0, 0)
        PlanningSlot.create({
            'resource_id': self.resource_joseph.id,
            'start_datetime': dt + relativedelta(hours=9),
            'end_datetime': dt + relativedelta(hours=15),
        })
        self.env.user.tz = 'UTC'
        self.env['resource.calendar.leaves'].create({
            'date_from': dt + relativedelta(weeks=1),
            'date_to': dt + relativedelta(weeks=1, days=1),
        })
        self.assertFalse(PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', self.resource_joseph.id],
            ]
        ), "The shift should be copied as open, as the company is on time off")
