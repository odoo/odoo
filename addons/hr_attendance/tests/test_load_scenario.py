from odoo.tests.common import TransactionCase


class TestHrAttendanceScenario(TransactionCase):
    """`_load_demo_data` builds the sample dataset the Attendances app offers on
    an otherwise empty database.

    It is guarded by `has_demo_data`, and so is the `hr` scenario it chains to.
    The two guards agree in production -- neither fires unless the database
    carries no sample data at all -- so the scenario can only be exercised
    where that is true. The test used to call it unconditionally and then
    assert against employees the guard had just declined to create, so on every
    database installed with demo data it errored on `hr.employee_sj` and said
    nothing about the scenario either way.
    """

    def test_the_guard_declines_on_a_database_that_already_has_sample_data(self):
        attendance = self.env["hr.attendance"]
        if not attendance.has_demo_data():
            self.skipTest("this database carries no sample data")
        before = attendance.search_count([])
        self.assertIsNone(attendance._load_demo_data())
        self.assertEqual(
            attendance.search_count([]),
            before,
            "declining must create nothing at all, not part of the scenario",
        )

    def test_load_scenario(self):
        attendance = self.env["hr.attendance"]
        if attendance.has_demo_data():
            self.skipTest(
                "the scenario only loads on a database with no sample data; "
                "install with --without-demo=all to exercise it"
            )
        self.assertIsNotNone(attendance._load_demo_data())

        employees = self.env["hr.employee"].browse(
            [
                self.env.ref("hr.employee_sj").id,
                self.env.ref("hr.employee_mw").id,
                self.env.ref("hr.employee_eg").id,
            ]
        )
        for employee in employees:
            self.assertTrue(
                employee.attendance_ids,
                f"{employee.name} should have demo attendance records",
            )
