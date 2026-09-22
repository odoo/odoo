from datetime import date

from lxml import etree

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("multi_wizard")
class TestLeaveGenerateMultiWizard(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.allocated_type = cls.env["hr.leave.type"].create(
            {
                "name": "Batch Time Off",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "leave_validation_type": "no_validation",
                "company_id": cls.company.id,
            }
        )
        cls.covered = cls.employee_emp
        cls.uncovered = cls.env["hr.employee"].create(
            {"name": "No Allocation Employee", "company_id": cls.company.id}
        )
        cls.env["hr.leave.allocation"].create(
            {
                "name": "Days for the covered one",
                "employee_id": cls.covered.id,
                "holiday_status_id": cls.allocated_type.id,
                "number_of_days": 20,
                "date_from": date(2026, 1, 1),
            }
        )

    def _wizard(self, **values):
        return self.env["hr.leave.generate.multi.wizard"].create(
            {
                "name": "Company shutdown",
                "holiday_status_id": self.allocated_type.id,
                "allocation_mode": "employee",
                "employee_ids": [(6, 0, (self.covered | self.uncovered).ids)],
                "date_from": date(2026, 6, 10),
                "date_to": date(2026, 6, 10),
                **values,
            }
        )

    def test_one_employee_without_allocation_does_not_sink_the_batch(self):
        """The employees who can take the time off get it; the one who cannot
        is skipped rather than aborting everyone else's request."""
        wizard = self._wizard()
        action = wizard.action_generate_time_off()

        leaves = self.env["hr.leave"].search(action["domain"])
        self.assertEqual(
            leaves.employee_id,
            self.covered,
            "the covered employee should have been given the time off",
        )
        self.assertFalse(
            self.env["hr.leave"].search(
                [
                    ("employee_id", "=", self.uncovered.id),
                    ("holiday_status_id", "=", self.allocated_type.id),
                ]
            ),
            "the employee with no allocation should not end up with a leave",
        )

    def test_allocated_types_are_selectable(self):
        """A type that requires an allocation can be picked in the wizard."""
        arch = etree.fromstring(
            self.env.ref("hr_holidays.hr_leave_generate_multi_wizard_view_form").arch
        )
        field = arch.xpath("//field[@name='holiday_status_id']")[0]
        self.assertNotIn(
            "requires_allocation",
            field.get("domain") or "",
            "types requiring an allocation must not be filtered out any more",
        )

    def test_no_employee_selected_means_everyone(self):
        """Leaving the employee list empty targets every employee in reach."""
        arch = etree.fromstring(
            self.env.ref("hr_holidays.hr_leave_generate_multi_wizard_view_form").arch
        )
        field = arch.xpath("//field[@name='employee_ids']")[0]
        self.assertFalse(
            field.get("required"),
            "the employee list must be optional for 'Everyone' to be reachable",
        )
        wizard = self._wizard(employee_ids=[(5, 0, 0)])
        action = wizard.action_generate_time_off()
        leaves = self.env["hr.leave"].search(action["domain"])
        self.assertIn(
            self.covered,
            leaves.employee_id,
            "an empty selection should have reached the whole company",
        )

    def test_a_batch_of_only_uncovered_employees_still_reports(self):
        """Nothing is created, and the failure is reported rather than raised
        as a wall of text."""
        wizard = self._wizard(employee_ids=[(6, 0, self.uncovered.ids)])
        action = wizard.action_generate_time_off()
        self.assertFalse(self.env["hr.leave"].search(action["domain"]))
