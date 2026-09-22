from odoo.exceptions import AccessError

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestMultiCompanyReport(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_1 = cls.env["res.company"].create({"name": "Opoo"})
        cls.company_2 = cls.env["res.company"].create({"name": "Otoo"})
        cls.employees = cls.env["hr.employee"].create(
            [
                {"name": "Bidule", "company_id": cls.company_1.id},
                {"name": "Machin", "company_id": cls.company_2.id},
            ]
        )
        cls.res_users_hr_officer.company_ids = [
            (4, cls.company_1.id),
            (4, cls.company_2.id),
        ]
        cls.res_users_hr_officer.company_id = cls.company_1.id
        cls.env.flush_all()
        cls.env.invalidate_all()

    def test_multi_company_report(self):
        content, _ = (
            self.env["ir.actions.report"]
            .with_user(self.res_users_hr_officer)
            .with_context(allowed_company_ids=[self.company_1.id, self.company_2.id])
            ._render_qweb_pdf("hr.hr_employee_print_badge", res_ids=self.employees.ids)
        )
        self.assertIn(b"Bidule", content)
        self.assertIn(b"Machin", content)

    def test_single_company_report(self):
        with self.assertRaises(AccessError):
            self.env["ir.actions.report"].with_user(
                self.res_users_hr_officer
            ).with_company(self.company_1)._render_qweb_pdf(
                "hr.hr_employee_print_badge", res_ids=self.employees.ids
            )


class TestMultiCompany(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env["res.company"].create({"name": "Company A"})
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})

        cls.user_a = mail_new_test_user(
            cls.env,
            login="user_a",
            company_id=cls.company_a.id,
            company_ids=(cls.company_a | cls.company_b).ids,
        )
        cls.user_b = mail_new_test_user(
            cls.env, login="user_b", company_id=cls.company_b.id
        )

        cls.employee_a = cls.env["hr.employee"].create(
            {
                "name": "Employee A",
                "company_id": cls.company_a.id,
                "user_id": cls.user_a.id,
            }
        )

        cls.employee_other_a = cls.env["hr.employee"].create(
            {
                "name": "Employee Other A",
                "company_id": cls.company_a.id,
            }
        )

        cls.employee_b = cls.env["hr.employee"].create(
            {
                "name": "Employee B",
                "company_id": cls.company_b.id,
                "user_id": cls.user_b.id,
                "parent_id": cls.employee_a.id,
            }
        )

        cls.employee_other_b = cls.env["hr.employee"].create(
            {
                "name": "Employee Other B",
                "company_id": cls.company_b.id,
            }
        )

        cls.env.flush_all()
        cls.env.invalidate_all()

    def test_read_manager_employee(self):
        self.assertEqual(
            self.employee_a.with_user(self.user_b).with_company(self.company_b).name,
            "Employee A",
        )

        self.assertEqual(
            self.employee_b.with_user(self.user_a).with_company(self.company_a).name,
            "Employee B",
        )

        with self.assertRaises(AccessError):
            self.employee_other_a.with_user(self.user_b).with_company(
                self.company_b
            ).name

    def test_read_no_manager_company(self):
        self.employee_b.parent_id = False

        with self.assertRaises(AccessError):
            self.employee_a.with_user(self.user_b).name

    def test_compute_hr_presence_state(self):
        self.user_a.company_ids = self.company_a
        self.assertEqual(
            self.employee_b.with_user(self.user_a).with_company(self.company_a).name,
            "Employee B",
        )

        presence_state = (
            self.employee_b.with_user(self.user_a)
            .with_company(self.company_a)
            .hr_presence_state
        )
        self.assertIn(
            presence_state,
            {"present", "absent", "out_of_working_hour", "archive"},
        )

    def test_an_employee_is_read_under_its_version_rule(self):
        # hr.employee delegates to hr.version through the computed version_id:
        # a version held by a company the reader cannot reach is not read
        # through the employee either
        hr_manager_a = mail_new_test_user(
            self.env,
            login="hr_manager_a",
            company_id=self.company_a.id,
            company_ids=self.company_a.ids,
            groups="base.group_user,hr.group_hr_manager",
        )
        other = self.employee_other_a
        other.version_id.write({"wage": 4321.0, "company_id": self.company_b.id})
        Employee = (
            self.env["hr.employee"].with_user(hr_manager_a).with_company(self.company_a)
        )
        self.assertFalse(Employee.search([("id", "=", other.id)]))
        self.assertFalse(Employee.search([("wage", "=", 4321.0)]))
        with self.assertRaises(AccessError):
            Employee.browse(other.id).read(["wage"])
        self.assertEqual(
            Employee.search([("id", "=", self.employee_a.id)]), self.employee_a
        )

    def test_a_relationship_reads_the_version_through_both_doors(self):
        # user_b reports to employee_a, of company A: what lets user_b read its
        # manager's employee record lets it read the manager's version
        Version = (
            self.env["hr.version"].with_user(self.user_b).with_company(self.company_b)
        )
        self.assertEqual(
            Version.search([("employee_id", "=", self.employee_a.id)]),
            self.employee_a.version_ids,
        )
        with self.assertRaises(AccessError):
            Version.browse(self.employee_other_a.version_id.id).read(["name"])
