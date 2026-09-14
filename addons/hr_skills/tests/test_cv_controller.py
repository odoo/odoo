from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import TransactionCase

from odoo.addons.hr_skills.controllers.main import EMPLOYEE_IDS_RE, HrEmployeeCV


@tagged("post_install", "-at_install")
class TestEmployeeIdsPattern(TransactionCase):
    def test_a_plain_id_list_is_accepted(self):
        for accepted in ("1", "1,2", "10,20,30"):
            self.assertTrue(EMPLOYEE_IDS_RE.match(accepted), accepted)

    def test_anything_int_would_choke_on_is_rejected(self):
        for rejected in ("1|2", "1,,2", "", ",", "1,", "1 2", "-1", "1;2", "a"):
            self.assertFalse(EMPLOYEE_IDS_RE.match(rejected), repr(rejected))

    def test_a_repeated_query_parameter_is_not_a_string(self):
        with self.assertRaises(TypeError):
            EMPLOYEE_IDS_RE.match(["1", "2"])

    def test_only_a_hex_color_reaches_the_report_styles(self):
        self.assertEqual(HrEmployeeCV._css_color("#1a2B3c"), "#1a2B3c")
        for rejected in (
            "red",
            "#fff",
            "#123456;background:url(/web/session/logout)",
            ["#123456"],
            None,
        ):
            self.assertEqual(HrEmployeeCV._css_color(rejected), "#666666", rejected)

    def test_the_rejected_shapes_are_the_ones_that_used_to_reach_int(self):
        for crashing in ("1|2", "1,,2", "", ",", "1,", "1 2", "1;2", "a"):
            with self.assertRaises(ValueError, msg=crashing):
                [int(part) for part in crashing.split(",")]


@tagged("post_install", "-at_install")
class TestPrintedCvAccess(HttpCase):
    """The controller renders as superuser, so the check it does beforehand is
    the only access control the printed CV has."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_company = cls.env["res.company"].create({"name": "Elsewhere Ltd"})
        cls.elsewhere = cls.env["hr.employee"].create(
            {"name": "Employee elsewhere", "company_id": cls.other_company.id},
        )
        cls.hr_user = new_test_user(
            cls.env,
            login="cv.hr",
            groups="hr.group_hr_user",
            company_id=cls.env.company.id,
            company_ids=[(6, 0, cls.env.company.ids)],
        )
        cls.hr_employee = cls.env["hr.employee"].create(
            {"name": "The HR user", "user_id": cls.hr_user.id},
        )
        cls.plain_user = new_test_user(
            cls.env, login="cv.plain", groups="base.group_user"
        )
        cls.plain_employee = cls.env["hr.employee"].create(
            {"name": "The plain user", "user_id": cls.plain_user.id},
        )

    def _print(self, login, employee_ids):
        self.authenticate(login, login)
        return self.url_open(f"/print/cv?employee_ids={employee_ids}&show_contact=1")

    def test_an_hr_user_cannot_print_an_employee_they_cannot_read(self):
        self.assertFalse(
            self.elsewhere.with_user(self.hr_user).has_access("read"),
            "the fixture only means something if the record rule hides them",
        )
        self.assertEqual(self._print("cv.hr", self.elsewhere.id).status_code, 404)

    def test_an_hr_user_prints_an_employee_they_can_read(self):
        response = self._print("cv.hr", self.plain_employee.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")

    def test_a_list_with_one_unreadable_employee_is_refused_whole(self):
        response = self._print("cv.hr", f"{self.plain_employee.id},{self.elsewhere.id}")
        self.assertEqual(response.status_code, 404)

    def test_an_id_that_exists_nowhere_is_not_found_rather_than_a_crash(self):
        missing = self.env["hr.employee"].search([], order="id desc", limit=1).id + 1000
        self.assertEqual(self._print("cv.hr", missing).status_code, 404)

    def test_a_plain_user_prints_only_themself(self):
        self.assertEqual(
            self._print("cv.plain", self.plain_employee.id).status_code, 200
        )
        self.assertEqual(self._print("cv.plain", self.hr_employee.id).status_code, 404)
