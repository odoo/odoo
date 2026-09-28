from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSifnextOrganization(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "SIFNEXT Department Test Company"})
        cls.other_company = cls.env["res.company"].create({"name": "SIFNEXT Other Test Company"})
        cls.department = cls.env["hr.department"].create({
            "name": "Test Department",
            "company_id": cls.company.id,
        })
        cls.other_department = cls.env["hr.department"].create({
            "name": "Other Department",
            "company_id": cls.other_company.id,
        })

    def test_company_exposes_its_departments(self):
        self.assertIn(self.department, self.company.department_ids)
        self.assertNotIn(self.other_department, self.company.department_ids)

    def test_user_department_must_be_in_allowed_companies(self):
        user = self.env["res.users"].create({
            "name": "SIFNEXT Department User",
            "login": "sifnext_department_user_test",
            "company_id": self.company.id,
            "company_ids": [(6, 0, [self.company.id])],
        })
        user.department_id = self.department
        self.assertEqual(user.department_id, self.department)

        with self.assertRaises(ValidationError):
            user.department_id = self.other_department
