from contextlib import closing
from datetime import timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.models.account_config import SOFT_LOCK_DATE_FIELDS
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountLockException(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.fakenow = cls.env.cr.now()
        cls.startClassPatcher(freeze_time(cls.fakenow))

        cls.other_user = new_test_user(
            cls.env,
            name="Other User",
            login="other_user",
            password="password",
            email="other_user@example.com",
            group_ids=cls.get_default_groups().ids,
            company_id=cls.env.company.id,
        )

        cls.company_data_2 = cls.setup_other_company()

        cls.soft_lock_date_info = [
            ("fiscalyear_lock_date", "out_invoice"),
            ("tax_lock_date", "out_invoice"),
            ("sale_lock_date", "out_invoice"),
            ("purchase_lock_date", "in_invoice"),
        ]

    def test_user_exception_move_edit_multi_user(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_move_edit_multi_user",
                    }
                )
                move.action_draft()
                move.action_post()

                with self.assertRaises(UserError):
                    move.with_user(self.other_user).action_draft()

    def test_global_exception_move_edit_multi_user(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": False,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_global_exception_move_edit_multi_user",
                    }
                )

                move.action_draft()
                move.action_post()

                move.with_user(self.other_user).action_draft()

    def test_user_exception_branch(self):
        root_company = self.company_data["company"]
        root_company.write({"child_ids": [Command.create({"name": "branch"})]})
        self.cr.precommit.run()
        branch = root_company.child_ids

        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                branch_move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                    company=branch,
                )

                root_move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                    company=root_company,
                )

                branch.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )

                with self.assertRaises(UserError):
                    branch_move.action_draft()
                root_move.action_draft()
                root_move.action_post()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": branch.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_branch branch exception",
                    }
                )
                branch_move.action_draft()
                branch_move.action_post()

                root_company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )

                for move in [branch_move, root_move]:
                    with self.assertRaises(UserError):
                        move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": root_company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_branch root_company exception",
                    }
                )
                for move in [branch_move, root_move]:
                    move.action_draft()
                    move.action_post()

    def test_user_exception_wrong_company(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )
                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company_data_2["company"].id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_move_edit_multi_user",
                    }
                )

                with self.assertRaises(UserError):
                    move.action_draft()

    def test_user_exception_insufficient(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2016-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_move_edit_multi_user",
                    }
                )

                with self.assertRaises(UserError):
                    move.action_draft()

    def test_expired_exception(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "create_date": self.fakenow - timedelta(hours=24),
                        "end_datetime": self.fakenow - timedelta(seconds=1),
                        "reason": "test_expired_exception",
                    }
                )
                with self.assertRaises(UserError):
                    move.action_draft()

    def test_revoked_exception(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                exception = self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_move_edit_multi_user",
                    }
                )
                move.action_draft()
                move.action_post()

                exception.action_revoke()

                with self.assertRaises(UserError):
                    move.action_draft()

    def test_user_exception_wrong_field(self):
        for lock_date_field, move_type, exception_lock_date_field in [
            ("fiscalyear_lock_date", "out_invoice", "tax_lock_date"),
            ("tax_lock_date", "out_invoice", "fiscalyear_lock_date"),
            ("sale_lock_date", "out_invoice", "purchase_lock_date"),
            ("purchase_lock_date", "in_invoice", "sale_lock_date"),
        ]:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )
                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company_data_2["company"].id,
                        "user_id": self.env.user.id,
                        exception_lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_wrong_field",
                    }
                )

                with self.assertRaises(UserError):
                    move.action_draft()

    def test_hard_lock_date(self):
        in_move = self.init_invoice(
            "in_invoice",
            invoice_date="2016-01-01",
            post=True,
            amounts=[1000.0],
            taxes=self.tax_sale_a,
        )
        out_move = self.init_invoice(
            "out_invoice",
            invoice_date="2016-01-01",
            post=True,
            amounts=[1000.0],
            taxes=self.tax_sale_a,
        )

        self.company.account_config_id.hard_lock_date = fields.Date.to_date(
            "2020-01-01"
        )

        with self.assertRaises(UserError):
            self.company.account_config_id.hard_lock_date = False

        with self.assertRaises(UserError):
            self.company.account_config_id.hard_lock_date = fields.Date.to_date(
                "2019-01-01"
            )

        self.env["account.lock_exception"].create(
            [
                {
                    "company_id": self.company_data_2["company"].id,
                    "user_id": self.env.user.id,
                    lock_date_field: fields.Date.to_date("2010-01-01"),
                    "end_datetime": self.fakenow + timedelta(hours=24),
                    "reason": f"test_hard_lock_ignores_exceptions {lock_date_field}",
                }
                for lock_date_field in SOFT_LOCK_DATE_FIELDS
            ]
        )

        for move in [in_move, out_move]:
            with self.assertRaises(UserError):
                move.action_draft()

    def test_company_lock_date(self):
        self.env["account.lock_exception"].search([]).sudo().unlink()
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )

                revoked_exception = self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_exception_recreated_on_lock_date_change revoked",
                    }
                )
                revoked_exception.action_revoke()
                active_exception = self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: fields.Date.to_date("2010-01-01"),
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_exception_recreated_on_lock_date_change active",
                    }
                )

                self.assertEqual(
                    revoked_exception.company_lock_date,
                    fields.Date.to_date("2020-01-01"),
                )
                self.assertEqual(
                    active_exception.company_lock_date,
                    fields.Date.to_date("2020-01-01"),
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2021-01-01"
                )

                self.assertEqual(
                    revoked_exception.company_lock_date,
                    fields.Date.to_date("2020-01-01"),
                )

                self.assertEqual(active_exception.state, "revoked")

                exceptions = (
                    self.env["account.lock_exception"]
                    .with_context(active_test=False)
                    .search([])
                )
                self.assertEqual(len(exceptions), 3)
                new_exception = exceptions - revoked_exception - active_exception
                self.assertRecordValues(
                    new_exception,
                    [
                        {
                            "company_id": self.company.id,
                            "user_id": self.env.user.id,
                            lock_date_field: fields.Date.to_date("2010-01-01"),
                            "company_lock_date": fields.Date.to_date("2021-01-01"),
                            "end_datetime": self.env.cr.now() + timedelta(hours=24),
                            "reason": "test_exception_recreated_on_lock_date_change active",
                        }
                    ],
                )

    def test_user_exception_remove_lock_date(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with (
                self.subTest(lock_date_field=lock_date_field, move_type=move_type),
                closing(self.cr.savepoint()),
            ):
                move = self.init_invoice(
                    move_type,
                    invoice_date="2016-01-01",
                    post=True,
                    amounts=[1000.0],
                    taxes=self.tax_sale_a,
                )

                self.company.account_config_id[lock_date_field] = fields.Date.to_date(
                    "2020-01-01"
                )
                with self.assertRaises(UserError):
                    move.action_draft()

                self.env["account.lock_exception"].create(
                    {
                        "company_id": self.company.id,
                        "user_id": self.env.user.id,
                        lock_date_field: False,
                        "end_datetime": self.fakenow + timedelta(hours=24),
                        "reason": "test_user_exception_move_edit_multi_user",
                    }
                )
                move.action_draft()

    def test_lock_exception_is_company_scoped(self):
        exception_company_1 = self.env["account.lock_exception"].create(
            {
                "company_id": self.company.id,
                "user_id": self.env.user.id,
                "fiscalyear_lock_date": fields.Date.to_date("2020-01-01"),
                "end_datetime": self.fakenow + timedelta(hours=24),
                "reason": "test_lock_exception_is_company_scoped",
            }
        )
        other_company_user = new_test_user(
            self.env,
            name="Other Company User",
            login="other_company_user",
            password="password",
            email="other_company_user@example.com",
            group_ids=self.get_default_groups().ids,
            company_id=self.company_data_2["company"].id,
        )
        visible_ids = (
            self.env["account.lock_exception"]
            .with_user(other_company_user)
            .search([])
            .ids
        )
        self.assertNotIn(exception_company_1.id, visible_ids)

    def test_lock_exception_visible_from_a_branch_company(self):
        root_company = self.company_data["company"]
        root_company.write({"child_ids": [Command.create({"name": "branch"})]})
        self.cr.precommit.run()
        branch = root_company.child_ids

        exception_on_root = self.env["account.lock_exception"].create(
            {
                "company_id": root_company.id,
                "user_id": self.env.user.id,
                "fiscalyear_lock_date": fields.Date.to_date("2020-01-01"),
                "end_datetime": self.fakenow + timedelta(hours=24),
                "reason": "test_lock_exception_visible_from_a_branch_company",
            }
        )
        visible_ids = (
            self.env["account.lock_exception"].with_company(branch).search([]).ids
        )
        self.assertIn(exception_on_root.id, visible_ids)
