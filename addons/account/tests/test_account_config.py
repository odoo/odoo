from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestAccountConfig(TransactionCase):
    def test_every_company_has_one_configuration(self):
        company = self.env["res.company"].create({"name": "configured co"})
        config = company.account_config_id
        self.assertEqual(config.company_id, company)
        self.assertEqual(
            self.env["account.config"].search_count([("company_id", "=", company.id)]),
            1,
        )
        self.assertEqual(config.fiscalyear_last_day, 31)
        self.assertEqual(config.fiscalyear_last_month, "12")

    def test_a_company_is_created_and_written_with_its_configuration(self):
        company = self.env["res.company"].create(
            {
                "name": "routed co",
                "fiscalyear_last_day": 30,
                "fiscalyear_last_month": "6",
            }
        )
        self.assertEqual(company.account_config_id.fiscalyear_last_day, 30)
        self.assertEqual(company.account_config_id.fiscalyear_last_month, "6")
        company.write({"anglo_saxon_accounting": True, "name": "routed co 2"})
        self.assertTrue(company.account_config_id.anglo_saxon_accounting)
        self.assertEqual(company.name, "routed co 2")
        self.assertNotIn("anglo_saxon_accounting", company._fields)

    def test_a_company_is_searched_through_its_configuration(self):
        company = self.env["res.company"].create(
            {"name": "searched co", "tax_calculation_rounding_method": "round_per_line"}
        )
        found = self.env["res.company"].search(
            [
                (
                    "account_config_id.tax_calculation_rounding_method",
                    "=",
                    "round_per_line",
                ),
                ("id", "=", company.id),
            ]
        )
        self.assertEqual(found, company)
        self.assertFalse(
            self.env["res.company"].search(
                [
                    (
                        "account_config_id.tax_calculation_rounding_method",
                        "=",
                        "round_globally",
                    ),
                    ("id", "=", company.id),
                ]
            )
        )

    def test_a_branch_takes_the_delegated_fields_from_its_root(self):
        root = self.env["res.company"].create(
            {"name": "root co", "fiscalyear_last_day": 30, "fiscalyear_last_month": "6"}
        )
        branch = self.env["res.company"].create(
            {"name": "branch co", "parent_id": root.id}
        )
        self.assertEqual(branch.account_config_id.fiscalyear_last_day, 30)
        self.assertEqual(branch.account_config_id.fiscalyear_last_month, "6")
        with self.assertRaises(ValidationError):
            branch.account_config_id.fiscalyear_last_month = "12"

    def test_the_lock_dates_are_kept_on_the_configuration(self):
        config = self.env.company.account_config_id
        config.fiscalyear_lock_date = "2020-01-31"
        self.assertEqual(str(config.user_fiscalyear_lock_date), "2020-01-31")
        self.assertEqual(
            self.env.company._get_user_lock_date("fiscalyear_lock_date"),
            config.fiscalyear_lock_date,
        )

    def test_a_configuration_is_read_under_the_readers_access(self):
        mine = self.env["res.company"].create({"name": "reader co"})
        theirs = self.env["res.company"].create({"name": "other reader co"})
        mine.account_config_id.write({"invoice_terms": "mine terms"})
        theirs.account_config_id.write(
            {"invoice_terms": "their terms", "fiscalyear_lock_date": "2024-06-30"}
        )
        portal = new_test_user(
            self.env,
            login="ac_portal",
            groups="base.group_portal",
            company_id=mine.id,
            company_ids=[Command.set([mine.id])],
        )
        employee = new_test_user(
            self.env,
            login="ac_employee",
            groups="base.group_user",
            company_id=mine.id,
            company_ids=[Command.set([mine.id])],
        )
        for user in (portal, employee):
            with self.subTest(user=user.login):
                Company = self.env["res.company"].with_user(user)
                Company = Company.with_context(allowed_company_ids=mine.ids)
                self.assertIn(
                    "mine terms",
                    Company.browse(mine.id).account_config_id.invoice_terms,
                )
                self.assertEqual(
                    Company.search(
                        [("account_config_id.invoice_terms", "ilike", "terms")]
                    ),
                    mine,
                    "a search through the link is bounded by the reader's rules",
                )
                Config = self.env["account.config"].with_user(user)
                Config = Config.with_context(allowed_company_ids=mine.ids)
                self.assertEqual(Config.search([]).company_id, mine)
                with self.assertRaises(AccessError):
                    Config._for(theirs).fiscalyear_lock_date
