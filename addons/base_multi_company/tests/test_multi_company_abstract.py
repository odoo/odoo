# Copyright 2017 LasLabs Inc.
# Copyright 2021 ACSONE SA/NV
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo_test_helper import FakeModelLoader

from odoo.tests import common


class TestMultiCompanyAbstract(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()

        # The fake class is imported here !! After the backup_registry
        from .multi_company_abstract_tester import MultiCompanyAbstractTester

        cls.loader.update_registry((MultiCompanyAbstractTester,))

        cls.test_model = cls.env["multi.company.abstract.tester"]

        cls.tester_model = cls.env["ir.model"].search(
            [("model", "=", "multi.company.abstract.tester")]
        )

        # Access record:
        cls.env["ir.model.access"].create(
            {
                "name": "access.tester",
                "model_id": cls.tester_model.id,
                "perm_read": 1,
                "perm_write": 1,
                "perm_create": 1,
                "perm_unlink": 1,
            }
        )

        cls.record_1 = cls.test_model.create({"name": "test"})
        cls.company_1 = cls.env.company
        cls.company_2 = cls.env["res.company"].create(
            {"name": "Test Co 2", "email": "base_multi_company@test.com"}
        )

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def add_company(self, company):
        """Add company to the test record."""
        self.record_1.company_ids = [(4, company.id)]

    def switch_user_company(self, user, company):
        """Add a company to the user's allowed & set to current."""
        user.write(
            {
                "company_ids": [(6, 0, (company + user.company_ids).ids)],
                "company_id": company.id,
            }
        )

    def test_compute_company_id(self):
        """It should set company_id to the top of the company_ids stack."""
        self.add_company(self.company_2)
        self.env.user.company_ids = [(4, self.company_2.id)]
        self.env.user.company_id = self.company_2.id
        self.assertEqual(
            self.record_1.company_id.id,
            self.company_2.id,
        )

    def test_search_company_id(self):
        """It should return correct record by searching company_id."""
        self.add_company(self.company_2)
        record = self.test_model.search(
            [
                ("company_id.email", "=", self.company_2.email),
                ("id", "=", self.record_1.id),
            ]
        )
        self.assertEqual(record, self.record_1)
        record = self.test_model.search(
            [("company_id", "=", self.company_2.id), ("id", "=", self.record_1.id)]
        )
        self.assertEqual(record, self.record_1)
        record = self.test_model.search(
            [
                ("company_ids", "child_of", self.company_2.id),
                ("id", "=", self.record_1.id),
            ]
        )
        self.assertEqual(record, self.record_1)
        record = self.test_model.search(
            [
                ("company_ids", "parent_of", self.company_2.id),
                ("id", "=", self.record_1.id),
            ]
        )
        self.assertEqual(record, self.record_1)

        name_result = self.test_model.name_search(
            "test", [["company_id", "in", [self.company_2.id]]]
        )
        # Result is [(<id>, "test")]
        self.assertEqual(name_result[0][0], self.record_1.id)

        result = self.test_model.search_read(
            [("company_id", "in", [False, self.company_2.id])], ["name"]
        )
        self.assertEqual([{"id": self.record_1.id, "name": self.record_1.name}], result)

    def test_search_in_false_company(self):
        """Records with no company are shared across companies but we need to convert
        those queries with an or operator"""
        self.record_1.company_ids = False
        result = self.test_model.search([("company_id", "in", [1, False])])
        self.assertEqual(result, self.record_1)

    def test_patch_company_domain(self):
        new_domain = self.test_model._patch_company_domain(
            [["company_id", "in", [False, self.company_2.id]]]
        )
        self.assertEqual(
            ["|", ["company_id", "=", False], ["company_id", "=", self.company_2.id]],
            new_domain,
        )

    def test_compute_company_id2(self):
        """
        Test the computation of company_id for a multi_company_abstract.
        We have to ensure that the priority of the computed company_id field
        is given on the current company of the current user.
        And not a random company into allowed companies (company_ids of the
        target model).
        Because most of access rights are based on the current company of the
        current user and not on allowed companies (company_ids).
        :return: bool
        """

        user_obj = self.env["res.users"]
        company_obj = self.env["res.company"]
        company1 = self.env.ref("base.main_company")
        # Create companies
        company2 = company_obj.create({"name": "High salaries"})
        company3 = company_obj.create({"name": "High salaries, twice more!"})
        company4 = company_obj.create({"name": "No salaries"})
        companies = company1 + company2 + company3
        # Create a "normal" user (not the admin)
        user = user_obj.create(
            {
                "name": "Best employee",
                "login": "best-emplyee@example.com",
                "company_id": company1.id,
                "company_ids": [(6, False, companies.ids)],
            }
        )
        tester_obj = self.test_model.with_user(user)
        tester = tester_obj.create(
            {"name": "My tester", "company_ids": [(6, False, companies.ids)]}
        )
        # Current company_id should be updated with current company of the user
        for company in user.company_ids:
            user.write({"company_id": company.id})
            # Force recompute
            tester.invalidate_model()
            # Ensure that the current user is on the right company
            self.assertEqual(user.company_id, company)
            self.assertEqual(tester.company_id, company)
            # So can read company fields without Access error
            self.assertTrue(bool(tester.company_id.name))
        # Switch to a company not in tester.company_ids
        self.switch_user_company(user, company4)
        # Force recompute
        tester.invalidate_model()
        self.assertNotEqual(user.company_id.id, tester.company_ids.ids)
        self.assertTrue(bool(tester.company_id.id))
        self.assertTrue(bool(tester.company_id.name))
        self.assertNotIn(user.company_id.id, tester.company_ids.ids)

    def test_company_id_create(self):
        """
        Test object creation with both company_ids and company_id
        :return: bool
        """

        user_obj = self.env["res.users"]
        company_obj = self.env["res.company"]
        company1 = self.env.ref("base.main_company")
        # Create companies
        company2 = company_obj.create({"name": "High salaries"})
        company3 = company_obj.create({"name": "High salaries, twice more!"})
        companies = company1 + company2 + company3
        # Create a "normal" user (not the admin)
        user = user_obj.create(
            {
                "name": "Best employee",
                "login": "best-emplyee@example.com",
                "company_id": company1.id,
                "company_ids": [(6, False, companies.ids)],
            }
        )
        tester_obj = self.test_model.with_user(user)
        # We add both values
        tester = tester_obj.create(
            {
                "name": "My tester",
                "company_id": company1.id,
                "company_ids": [(6, False, companies.ids)],
            }
        )
        # Check if all companies have been added
        self.assertEqual(tester.sudo().company_ids, companies)

    def test_company_id_create_false(self):
        """
        Test a creation with only company_id == False
        """

        user_obj = self.env["res.users"]
        company_obj = self.env["res.company"]
        company1 = self.env.ref("base.main_company")
        # Create companies
        company2 = company_obj.create({"name": "High salaries"})
        company3 = company_obj.create({"name": "High salaries, twice more!"})
        companies = company1 + company2 + company3
        # Create a "normal" user (not the admin)
        user = user_obj.create(
            {
                "name": "Best employee",
                "login": "best-emplyee@example.com",
                "company_id": company1.id,
                "company_ids": [(6, False, companies.ids)],
            }
        )
        tester_obj = self.test_model.with_user(user)
        # We add both values
        tester = tester_obj.create(
            {
                "name": "My tester",
                "company_id": False,
            }
        )
        # Check company_ids is False too
        self.assertFalse(tester.sudo().company_ids)

        # Check company_id is False also when changing current one
        self.assertFalse(tester.with_company(company2).company_id)

    def test_set_company_id(self):
        """
        Test object creation with both company_ids and company_id
        :return: bool
        """

        user_obj = self.env["res.users"]
        company_obj = self.env["res.company"]
        company1 = self.env.ref("base.main_company")
        # Create companies
        company2 = company_obj.create({"name": "High salaries"})
        company3 = company_obj.create({"name": "High salaries, twice more!"})
        companies = company1 + company2 + company3
        # Create a "normal" user (not the admin)
        user = user_obj.create(
            {
                "name": "Best employee",
                "login": "best-emplyee@example.com",
                "company_id": company1.id,
                "company_ids": [(6, False, companies.ids)],
            }
        )
        tester_obj = self.test_model.with_user(user)
        # We add both values
        tester = tester_obj.create(
            {"name": "My tester", "company_ids": [(6, False, companies.ids)]}
        )
        # Check if all companies have been added
        self.assertEqual(tester.sudo().company_ids, companies)

        # Check set company_id
        tester.company_id = company1

        self.assertEqual(tester.sudo().company_ids, company1)

        # Check remove company_id
        tester.company_id = False

        self.assertFalse(tester.sudo().company_ids)
