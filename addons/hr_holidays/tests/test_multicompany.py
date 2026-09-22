from datetime import date, datetime

from odoo import tests

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tests.tagged("post_install", "-at_install")
class TestHrHolidaysMultiCompanyCommon(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2 = cls.env["res.company"].create({"name": "Test company 2"})

    def test_unrelated_public_leave(self):
        public_leave = self.env["resource.schedule.exception"].create(
            {
                "name": "Global Time Off for Company 2",
                "resource_id": False,
                "date_from": datetime(2024, 1, 3, 6, 0, 0),
                "date_to": datetime(2024, 1, 3, 19, 0, 0),
            }
        )
        public_leave.company_id = self.company_2
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type",
                "requires_allocation": False,
                "request_unit": "day",
                "company_id": False,
            }
        )
        leave = self.env["hr.leave"].create(
            {
                "name": "3 days leave",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date(2024, 1, 2),
                "request_date_to": datetime(2024, 1, 4),
            }
        )
        self.assertNotEqual(public_leave.company_id, self.employee_emp.company_id)
        self.assertEqual(
            leave.number_of_days,
            3,
            "The leave should not depend on other companies public leaves.",
        )

    def test_the_columns_the_company_rules_filter_are_indexed(self):
        """The global company rules must not make every read a sequential scan.

        `hr_leave_rule_multicompany` puts `company_id` in the domain of every
        read of a time off, and `hr_leave_allocation_rule_multicompany` reaches
        `holiday_status_id.company_id`, which the ORM resolves by joining
        through that Many2one (`_traverse_related_sql`). Both columns carry the
        weight of the security layer on every query, so neither may be left
        without an index.
        """
        expected = {
            ("hr_leave", "company_id"),
            ("hr_leave", "holiday_status_id"),
            ("hr_leave_allocation", "holiday_status_id"),
        }
        missing = set()
        for table, column in sorted(expected):
            self.env.cr.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = %s AND indexdef LIKE %s",
                (table, f"%({column})%"),
            )
            if not self.env.cr.fetchall():
                missing.add(f"{table}.{column}")
        self.assertFalse(
            missing,
            "no index covers %s, so the multi-company record rules scan the "
            "whole table on every read" % ", ".join(sorted(missing)),
        )
