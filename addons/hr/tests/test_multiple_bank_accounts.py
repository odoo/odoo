from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestEmployeeMultipleBanksUi(HttpCase):
    def test_employee_profile_tour(self):
        employee = self.env["hr.employee"].create(
            {
                "name": "Johnny H.",
            }
        )
        self.start_tour(
            "/odoo",
            "hr_employee_multiple_bank_accounts_tour",
            login="admin",
            timeout=200,
        )
        total = 0
        for allocation in employee.salary_allocation_ids:
            ba_percentage = allocation.amount
            self.assertEqual(allocation.amount_is_percentage, True)
            self.assertAlmostEqual(ba_percentage, 33.33, delta=0.011)
            total += ba_percentage
        self.assertAlmostEqual(total, 100.0, "Total must amount to 100.")
