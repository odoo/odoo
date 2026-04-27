from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "payroll_sickness_relapse")
class TestPayrollSicknessRelapse(TestPayrollCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sick_time_off_type = cls.env.ref("hr_holidays.holiday_status_sl")

    def test_sickness_relapse_visibility(self):
        """
        Test Case:
        Employee Test is sick for a week. The following week the employee becomes
        sick again and submits another time off request. For the second
        time off request the employee has the option to select if this sickness
        is a relapse of the sickness from the week before or a new sickness.
        """
        first_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 1),
                "request_date_to": date(2024, 7, 5),
            }
        )
        second_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 10),
                "request_date_to": date(2024, 7, 12),
            }
        )

        (first_leave + second_leave).action_validate()

        self.assertFalse(first_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(second_leave.l10n_be_sickness_can_relapse)

    def test_sickness_relapse_no_relapse(self):
        """
        Test Case:
        Employee Test is sick for 3 weeks. A week after the employee becomes
        sick again and submits another time off request for another 3 weeks.
        For the second time off request Employee test has indicated that this
        is a new sickness and not a relapse of the previous sickness.
        This results in a work entry with the code LEAVE110, Sick Time Off,
        30 Calendar days after the first sick day, indicating that
        the first sick leave has no effect on the second one.
        """
        first_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 1),
                "request_date_to": date(2024, 7, 20),
            }
        )
        second_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 29),
                "request_date_to": date(2024, 8, 16),
                "l10n_be_sickness_relapse": False,
            }
        )

        (first_leave + second_leave).action_validate()

        work_entries = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 8, 8), date(2024, 8, 8)
        )
        work_entries.action_validate()
        work_entry_names = set(work_entries.mapped("code"))

        self.assertSetEqual(work_entry_names, {"LEAVE110"})

    def test_sickness_relapse_with_relapse(self):
        """
        Test Case:
        Employee Test is sick for 3 weeks. A week after the employee becomes
        sick again and submits another time off request for another 3 weeks.
        For the second time off request Employee test has indicated that this
        a relapse of the previous sickness. This results in a work entry
        with the code LEAVE214, Sick Time Off(Without Guaranteed Salary),
        31 sick days after the first sick day, indicating that the second
        sick leave is a continuation of the first one.
        """
        first_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 1),
                "request_date_to": date(2024, 7, 20),
            }
        )
        second_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 29),
                "request_date_to": date(2024, 8, 16),
                "l10n_be_sickness_relapse": True,
            }
        )

        (first_leave + second_leave).action_validate()

        work_entry_paid = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 8, 7), date(2024, 8, 7)
        )
        work_entry_unpaid = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 8, 8), date(2024, 8, 8)
        )

        work_entry_paid.action_validate()
        work_entry_unpaid.action_validate()

        work_entry_paid_code = set(work_entry_paid.mapped("code"))
        work_entry_unpaid_code = set(work_entry_unpaid.mapped("code"))

        self.assertSetEqual(work_entry_paid_code, {"LEAVE110"})
        self.assertSetEqual(work_entry_unpaid_code, {"LEAVE214"})

    def test_sickness_multiple_sicknesses_partial_relapse(self):
        """
        Test Case:
        Employee Test is sick for 5 days every week for 4 weeks. The next week
        Employee Test is sick again, but this is a new sickness. This sickness
        relapses again every week for 2 more week. Even though Employee Test has
        taken 35 days of sick leave he should still be paid fully as the
        two sick leaves are not for the same illness. Thus all work entries
        starting from the first day in the 7th week should still have
        a work entry code of LEAVE110.
        """
        first_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 1),
                "request_date_to": date(2024, 7, 5),
            }
        )
        second_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 8),
                "request_date_to": date(2024, 7, 12),
                "l10n_be_sickness_relapse": True,
            }
        )
        third_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 15),
                "request_date_to": date(2024, 7, 19),
                "l10n_be_sickness_relapse": True,
            }
        )
        fourth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 22),
                "request_date_to": date(2024, 7, 26),
                "l10n_be_sickness_relapse": True,
            }
        )
        fifth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 29),
                "request_date_to": date(2024, 8, 2),
                "l10n_be_sickness_relapse": False,
            }
        )
        sixth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 8, 5),
                "request_date_to": date(2024, 8, 9),
                "l10n_be_sickness_relapse": True,
            }
        )
        seventh_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 8, 12),
                "request_date_to": date(2024, 8, 16),
                "l10n_be_sickness_relapse": True,
            }
        )
        (
            first_leave
            + second_leave
            + third_leave
            + fourth_leave
            + fifth_leave
            + sixth_leave
            + seventh_leave
        ).action_validate()

        work_entries = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 8, 12), date(2024, 8, 12)
        )
        work_entries.action_validate()
        work_entries_code = set(work_entries.mapped("code"))

        self.assertSetEqual(work_entries_code, {"LEAVE110"})
        self.assertFalse(first_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(second_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(third_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(fourth_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(fifth_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(sixth_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(seventh_leave.l10n_be_sickness_can_relapse)

    def test_sickness_multiple_sicknesses_only_relapse(self):
        """
        Test Case:
        Employee Test is sick for 5 days every week for 7 weeks, with every sick
        leave being a relapse of the previous one. All work entries starting
        from the first day in the 7th week should have a work entry code of LEAVE214.
        """
        first_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 1),
                "request_date_to": date(2024, 7, 5),
            }
        )
        second_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 8),
                "request_date_to": date(2024, 7, 12),
                "l10n_be_sickness_relapse": True,
            }
        )
        third_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 15),
                "request_date_to": date(2024, 7, 19),
                "l10n_be_sickness_relapse": True,
            }
        )
        fourth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 22),
                "request_date_to": date(2024, 7, 26),
                "l10n_be_sickness_relapse": True,
            }
        )
        fifth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 29),
                "request_date_to": date(2024, 8, 2),
                "l10n_be_sickness_relapse": True,
            }
        )
        sixth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 8, 5),
                "request_date_to": date(2024, 8, 9),
                "l10n_be_sickness_relapse": True,
            }
        )
        seventh_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 8, 12),
                "request_date_to": date(2024, 8, 16),
                "l10n_be_sickness_relapse": True,
            }
        )

        (
            first_leave
            + second_leave
            + third_leave
            + fourth_leave
            + fifth_leave
            + sixth_leave
            + seventh_leave
        ).action_validate()

        work_entries = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 8, 12), date(2024, 8, 12)
        )
        work_entries.action_validate()
        work_entries_code = set(work_entries.mapped("code"))

        self.assertSetEqual(work_entries_code, {"LEAVE214"})
        self.assertFalse(first_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(second_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(third_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(fourth_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(fifth_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(sixth_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(seventh_leave.l10n_be_sickness_can_relapse)

    def test_sickness_biweekly_relapse(self):
        """
        Test Case:
        A person is sick for 2 days every 14 days for almost 8 months.
        Eventually the sick leave days should culminate in over 30 days
        of leave causing the person to no longer have work entries with the
        code LEAVE110.
        """
        for i in range(16):
            start_date = date(2024, 1, 1) + relativedelta(days=(14 * i))
            end_date = start_date + relativedelta(days=1)
            short_leave = self.env["hr.leave"].create(
                {
                    "holiday_status_id": self.sick_time_off_type.id,
                    "employee_id": self.employee_test.id,
                    "request_date_from": start_date,
                    "request_date_to": end_date,
                    "l10n_be_sickness_relapse": True,
                }
            )
            short_leave.action_validate()

        work_entries = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 7, 15), date(2024, 7, 29)
        )

        work_entries.action_validate()

        paid_date = work_entries.filtered(lambda entry: entry.date_start.day == 15)
        unpaid_date = work_entries.filtered(lambda entry: entry.date_start.day == 29)

        work_entry_paid_code = set(paid_date.mapped("code"))
        work_entry_unpaid_code = set(unpaid_date.mapped("code"))

        self.assertSetEqual(work_entry_paid_code, {"LEAVE110"})
        self.assertSetEqual(work_entry_unpaid_code, {"LEAVE214"})

    def test_from_comment(self):
        """
        Example (all dates are inclusive):
        | Name | Date from   | Date to     | Relapse | Calendar Days | Work Days  |
        | ---- | ----------- | ----------- | ------- | ------------- | ---------- |
        | 1st  | 10/Jun/2024 | 12/Jun/2024 | False   | 03 (c)days    | 03 (w)days |
        | 2nd  | 01/Jul/2024 | 08/Jul/2024 | False   | 08 (c)days    | 06 (w)days |
        | 3rd  | 15/Jul/2024 | 30/Jul/2024 | True    | 16 (c)days    | 12 (w)days |
        | 4th  | 05/Aug/2024 | 15/Aug/2024 | True    | 11 (c)days    | 09 (w)days |

        Note: 1st and 2nd leave will have a relapse value of True in practice because
        that is the default value for the field. In this example, the value is set to
        False to hopefully make the example clearer.

        The first leave is shorter than 30 (calendar) days.
        All (work) days within this leave have a guaranteed salary.

        The second leave is shorter than 30 (c) days.
        The gap between it and the first leave is greater than 14 days.
        All (w) days within this leave have a guaranteed salary.

        The third leave is shorter than 30 (c) days.
        The gap between it and the second leave is less than 14 days.
        It is a relapse, sum the duration of this and previous related leaves.
        The sum is 8 + 16 = 24 (c) days, which is less than 30 days.
        All (w) days within this leave have a guaranteed salary.

        The fourth leave is shorter than 30 (c) days.
        The gap between it and the third leave is less than 14 days.
        It is a relapse, sum the duration of this and previous related leaves.
        That sum is 8 + 16 + 11 = 35 (c) days, which is greater than 30 days.
        The first 6 (c) days have a guaranteed salary.
        (w) days 12/08 - 15/08 do not have a guaranteed salary.
        """
        first_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 6, 10),
                "request_date_to": date(2024, 6, 12),
            }
        )
        second_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 1),
                "request_date_to": date(2024, 7, 8),
            }
        )
        third_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 7, 15),
                "request_date_to": date(2024, 7, 30),
            }
        )
        fourth_leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.sick_time_off_type.id,
                "employee_id": self.employee_test.id,
                "request_date_from": date(2024, 8, 5),
                "request_date_to": date(2024, 8, 15),
            }
        )
        (first_leave + second_leave + third_leave + fourth_leave).action_validate()

        work_entries = self.employee_test.contract_ids.generate_work_entries(
            date(2024, 8, 9), date(2024, 8, 12)
        )

        work_entries.action_validate()

        paid_date = work_entries.filtered(lambda entry: entry.date_start.day == 9)
        unpaid_date = work_entries.filtered(lambda entry: entry.date_start.day == 12)
        work_entry_paid_code = set(paid_date.mapped("code"))
        work_entry_unpaid_code = set(unpaid_date.mapped("code"))

        self.assertSetEqual(work_entry_paid_code, {"LEAVE110"})
        self.assertSetEqual(work_entry_unpaid_code, {"LEAVE214"})
        self.assertFalse(first_leave.l10n_be_sickness_can_relapse)
        self.assertFalse(second_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(third_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(fourth_leave.l10n_be_sickness_can_relapse)

    def test_sickness_relapse_starting_from_2026(self):
        """
        Example (all dates are inclusive):
        | Leave | Date from   | Date to     | Relapse | Calendar Days | Work Days  |
        | ----- | ----------- | ----------- | ------- | ------------- | ---------- |
        | 1st   | 10/Jan/26   | 30/Jan/26   | False   | 21 (c)days    | 15 (w)days |
        | 2nd   | 01/Apr/26   | 15/Apr/26   | False   | 15 (c)days    | 11 (w)days |
        | 3rd   | 11/May/26   | 30/May/26   | True    | 20 (c)days    | 15 (w)days |
        | 4th   | 10/Aug/26   | 20/Aug/26   | False   | 11 (c)days    | 8 (w)days  |
        The first leave is shorter than 30 (calendar) days.
        All (work) days within this leave have a guaranteed salary.
        The second leave is shorter than 30 (c) days.
        The gap between it and the first leave is greater than 56 days.
        It is not considered as a relapse.
        All (w) days within this leave have a guaranteed salary.
        The third leave is shorter than 30 (c) days.
        The gap between it and the second leave is less than 56 days.
        It is a relapse, sum the duration of this and previous related leaves.
        The sum is 15 + 20 = 35 (c) days, which is greater than 30 days.
        The first 30 (c) days have a guaranteed salary.
        (w) days 26/05 - 30/05 do not have a guaranteed salary.
        The fourth leave is shorter than 30 (c) days.
        The gap between it and the third leave is greater than 56 days.
        It is not considered as a relapse.
        """

        first_leave = self.env["hr.leave"].create({
            "holiday_status_id": self.sick_time_off_type.id,
            "employee_id": self.employee_test.id,
            "request_date_from": date(2026, 1, 10),
            "request_date_to": date(2026, 1, 30),
        })

        second_leave = self.env["hr.leave"].create({
            "holiday_status_id": self.sick_time_off_type.id,
            "employee_id": self.employee_test.id,
            "request_date_from": date(2026, 4, 1),
            "request_date_to": date(2026, 4, 15),
        })

        third_leave = self.env["hr.leave"].create({
            "holiday_status_id": self.sick_time_off_type.id,
            "employee_id": self.employee_test.id,
            "request_date_from": date(2026, 5, 11),
            "request_date_to": date(2026, 5, 30),
        })

        fourth_leave = self.env["hr.leave"].create({
            "holiday_status_id": self.sick_time_off_type.id,
            "employee_id": self.employee_test.id,
            "request_date_from": date(2026, 8, 10),
            "request_date_to": date(2026, 8, 20),
        })
        (first_leave + second_leave + third_leave + fourth_leave).action_approve()

        self.assertFalse(first_leave.l10n_be_sickness_can_relapse)
        self.assertFalse(second_leave.l10n_be_sickness_can_relapse)
        self.assertTrue(third_leave.l10n_be_sickness_can_relapse)
        self.assertFalse(fourth_leave.l10n_be_sickness_can_relapse)
