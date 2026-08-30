from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install", "accruals")
class TestAccrualYearlyGain(TestHrHolidaysCommon):
    """How much a level actually grants over a year.

    The form asks for an amount and a frequency, but the number the HR officer
    is actually deciding -- days per year -- was left for them to work out in
    their head, differently for each of the seven frequencies.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env.company.resource_calendar_id
        cls.plan = cls.env["hr.leave.accrual.plan"].create(
            {"name": "Yearly gain plan", "accrued_gain_time": "start"}
        )

    def _level(self, **values):
        return self.env["hr.leave.accrual.level"].create(
            {"accrual_plan_id": self.plan.id, "added_value": 1, **values}
        )

    def test_yearly_gain_per_frequency(self):
        expected = {
            "weekly": 52,
            "bimonthly": 24,
            "monthly": 12,
            "biyearly": 2,
            "yearly": 1,
        }
        for frequency, days in expected.items():
            with self.subTest(frequency=frequency):
                level = self._level(frequency=frequency)
                self.assertEqual(level.yearly_gain, days)

    def test_yearly_gain_hourly_follows_the_company_week(self):
        level = self._level(frequency="hourly")
        self.assertEqual(level.yearly_gain, 52 * self.calendar.hours_per_week)

    def test_yearly_gain_daily_counts_calendar_days(self):
        # Not based on worked time: every day of the year accrues.
        level = self._level(frequency="daily")
        self.assertFalse(level.is_based_on_worked_time)
        self.assertEqual(level.yearly_gain, 365)

    def test_yearly_gain_daily_on_worked_time_counts_working_days(self):
        level = self._level(frequency="daily")
        level.accrual_plan_id.is_based_on_worked_time = True
        self.assertEqual(level.yearly_gain, 52 * self.calendar._get_days_per_week())

    def test_yearly_gain_scales_with_the_amount(self):
        level = self._level(frequency="monthly", added_value=2.5)
        self.assertEqual(level.yearly_gain, 30)
