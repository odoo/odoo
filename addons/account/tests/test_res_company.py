from types import SimpleNamespace

from odoo import Command
from odoo.tests import common, new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class _FakeAccount:
    def __init__(self, id_, currency_id=False):
        self.id = id_
        self.currency_id = currency_id


@tagged("post_install", "-at_install")
class TestFiscalCountryGroupCodes(common.TransactionCase):
    def test_a_company_without_a_fiscal_country_still_yields_a_list(self):
        company = self.env["res.company"].create({"name": "No Fiscal Country Co"})
        self.assertFalse(company.account_config_id.account_fiscal_country_id)
        codes = company.account_config_id.account_fiscal_country_group_codes
        self.assertIsInstance(
            codes,
            list,
            "an empty list would read back as False and break every consumer",
        )
        self.assertNotIn("EU", codes)

    def test_a_partner_scoped_to_such_a_company_computes_its_group_codes(self):
        company = self.env["res.company"].create({"name": "No Fiscal Country Co 2"})
        partner = self.env["res.partner"].create({"name": "Scoped"})
        scoped = partner.with_context(allowed_company_ids=[company.id])
        self.assertIsInstance(scoped.fiscal_country_group_codes, list)

    def test_a_company_with_a_fiscal_country_reports_its_groups(self):
        belgium = self.env.ref("base.be")
        company = self.env["res.company"].create(
            {"name": "BE Fiscal Co", "account_fiscal_country_id": belgium.id}
        )
        self.assertEqual(
            company.account_config_id.account_fiscal_country_group_codes,
            belgium.country_group_codes,
            "a company with a fiscal country still reports that country's groups",
        )


@tagged("post_install", "-at_install")
class TestResCompanyAccountCode(AccountTestInvoicingCommon):
    def test_get_new_account_code_pure(self):
        new_code = self.env["res.company"].get_new_account_code
        cases = {
            ("101000", "1", "2"): "201000",
            ("101000", "10", "20"): "201000",
            ("511001", "511", "512"): "512001",
            ("570", "5", "512"): "51270",
            ("500", "5", "5000000"): "5000000",
            ("5", "5", "6"): "6",
        }
        for (code, old, new), expected in cases.items():
            self.assertEqual(
                new_code(code, old, new),
                expected,
                f"get_new_account_code({code!r}, {old!r}, {new!r})",
            )

    def test_get_new_account_code_length_preserved_for_same_length_prefix(self):
        new_code = self.env["res.company"].get_new_account_code
        for code in ("511001", "511999", "511000", "511100"):
            self.assertEqual(len(new_code(code, "511", "622")), len(code))

    def test_reflect_code_prefix_change(self):
        company = self.company_data["company"]
        Account = self.env["account.account"].with_company(company)
        cash_a = Account.create(
            {"name": "Cash A", "code": "511001", "account_type": "asset_cash"}
        )
        cash_b = Account.create(
            {"name": "Cash B", "code": "511050", "account_type": "asset_cash"}
        )
        other = Account.create(
            {"name": "Other 511", "code": "511900", "account_type": "expense"}
        )

        company.reflect_code_prefix_change("511", "622")

        self.assertEqual(cash_a.code, "622001")
        self.assertEqual(cash_b.code, "622050")
        self.assertEqual(other.code, "511900", "non-cash account must be untouched")

    def test_reflect_code_prefix_change_noop(self):
        company = self.company_data["company"]
        cash = (
            self.env["account.account"]
            .with_company(company)
            .create({"name": "Cash", "code": "511001", "account_type": "asset_cash"})
        )
        company.reflect_code_prefix_change("511", "511")
        company.reflect_code_prefix_change(False, "622")
        self.assertEqual(cash.code, "511001")


@tagged("post_install", "-at_install")
class TestUnaffectedEarningsAccount(AccountTestInvoicingCommon):
    def _fresh_company(self, name):
        return self.env["res.company"].create({"name": name})

    def test_returns_existing_unaffected_account(self):
        company = self.company_data["company"]
        existing = (
            self.env["account.account"]
            .with_company(company)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(company),
                    ("account_type", "=", "equity_unaffected"),
                ],
                limit=1,
            )
        )
        self.assertTrue(existing, "the test chart is expected to ship one")
        self.assertEqual(company.get_unaffected_earnings_account(), existing)

    def test_creates_999999_when_free(self):
        company = self._fresh_company("Unaffected Fresh")
        account = company.get_unaffected_earnings_account()
        self.assertEqual(account.account_type, "equity_unaffected")
        self.assertEqual(account.with_company(company).code, "999999")

    def test_skips_taken_codes_counting_down(self):
        company = self._fresh_company("Unaffected Collision")
        Account = self.env["account.account"].with_company(company)
        for code in ("999999", "999998"):
            Account.create(
                {
                    "name": f"Occupant {code}",
                    "code": code,
                    "account_type": "expense",
                    "company_ids": [Command.link(company.id)],
                }
            )
        account = company.get_unaffected_earnings_account()
        self.assertEqual(account.account_type, "equity_unaffected")
        self.assertEqual(
            account.with_company(company).code,
            "999997",
            "must skip the taken codes",
        )
        self.assertEqual(company.get_unaffected_earnings_account(), account)


@tagged("post_install", "-at_install")
class TestResCompanyDomesticFP(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.be = self.env.ref("base.be")
        self.europe = self.env.ref("base.europe")
        self.company = self.env["res.company"].create(
            {"name": "CC Domestic", "country_id": self.be.id}
        )
        self.FP = self.env["account.fiscal.position"].with_company(self.company)

    def _fp(self, name, sequence, specific):
        return self.FP.create(
            {
                "name": name,
                "company_id": self.company.id,
                "sequence": sequence,
                "country_id": self.be.id if specific else False,
                "country_group_id": False if specific else self.europe.id,
            }
        )

    def test_lowest_sequence_wins_over_specificity(self):
        self._fp("spec-seq5", 5, specific=True)
        group_low = self._fp("group-seq1", 1, specific=False)
        self.company.account_config_id.invalidate_recordset(
            ["domestic_fiscal_position_id"]
        )
        self.assertEqual(
            self.company.account_config_id.domestic_fiscal_position_id, group_low
        )

    def test_specific_beats_group_on_sequence_tie(self):
        self._fp("group-seq5", 5, specific=False)
        spec = self._fp("spec-seq5", 5, specific=True)
        self.company.account_config_id.invalidate_recordset(
            ["domestic_fiscal_position_id"]
        )
        self.assertEqual(
            self.company.account_config_id.domestic_fiscal_position_id, spec
        )

    def test_no_candidate(self):
        self.assertFalse(self.company.account_config_id.domestic_fiscal_position_id)


@tagged("post_install", "-at_install")
class TestResCompanyMultiVat(common.TransactionCase):
    def test_multi_vat_follows_country_id(self):
        be = self.env.ref("base.be")
        fr = self.env.ref("base.fr")
        us = self.env.ref("base.us")
        company = self.env["res.company"].create(
            {"name": "CC MultiVat", "country_id": us.id}
        )
        company.account_config_id.account_fiscal_country_id = us
        fp = self.env["account.fiscal.position"].create(
            {
                "name": "BE foreign VAT",
                "company_id": company.id,
                "country_id": be.id,
                "foreign_vat": "BE0477472701",
            }
        )
        self.assertEqual(company.account_config_id.multi_vat_foreign_country_ids, be)

        fp.write({"country_id": fr.id})
        self.assertEqual(company.account_config_id.multi_vat_foreign_country_ids, fr)


@tagged("post_install", "-at_install")
class TestOpeningMovePlanner(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.a1 = _FakeAccount(1)
        cls.a2 = _FakeAccount(2)
        cls.bal = _FakeAccount(9)

    def _plan(self, to_update, existing=None, initial=0.0):
        return self.env["res.company"]._plan_opening_move_lines(
            to_update=to_update,
            balancing_account=self.bal,
            existing_lines=existing or {},
            initial_balance=initial,
            is_zero=lambda balance: abs(balance) < 1e-9,
            amount_currency_of=lambda account, balance: balance,
            currency_id_of=lambda account: 42,
            opening_name="OPEN",
            balancing_name="BAL",
        )

    @staticmethod
    def _line(id_, balance):
        return SimpleNamespace(id=id_, balance=balance)

    def test_fresh_single_debit_balances_to_zero(self):
        cmds = self._plan({self.a1: (100.0, None)})
        self.assertEqual(len(cmds), 2, "one opening line + one balancing line")
        creates = {c[2]["account_id"]: c[2] for c in cmds if c[0] == 0}
        self.assertEqual(sum(v["balance"] for v in creates.values()), 0.0)
        self.assertEqual(creates[1]["balance"], 100.0)
        self.assertEqual(creates[1]["name"], "OPEN")
        self.assertEqual(creates[9]["balance"], -100.0)
        self.assertEqual(creates[9]["name"], "BAL")
        self.assertEqual(creates[9]["currency_id"], 42)

    def test_fresh_debit_and_credit(self):
        cmds = self._plan({self.a1: (100.0, 30.0)})
        creates = [c[2] for c in cmds if c[0] == 0]
        self.assertEqual(sum(v["balance"] for v in creates), 0.0)
        a1_balances = sorted(v["balance"] for v in creates if v["account_id"] == 1)
        self.assertEqual(a1_balances, [-30.0, 100.0], "credit stored as negative")

    def test_update_replaces_existing_and_rebalances(self):
        existing = {
            (self.a1, "debit"): [self._line(7, 40.0)],
            (self.bal, "credit"): [self._line(8, -40.0)],
        }
        cmds = self._plan({self.a1: (100.0, None)}, existing=existing, initial=40.0)
        self.assertTrue(all(c[0] == 1 for c in cmds), "only updates, no create/delete")
        updates = {c[1]: c[2] for c in cmds if c[0] == 1}
        self.assertEqual(updates[7]["balance"], 100.0)
        self.assertEqual(updates[8]["balance"], -100.0)
        self.assertEqual(updates[7]["balance"] + updates[8]["balance"], 0.0)

    def test_zero_side_deletes_existing_lines(self):
        existing = {
            (self.a1, "debit"): [self._line(7, 100.0)],
            (self.bal, "credit"): [self._line(8, -100.0)],
        }
        cmds = self._plan({self.a1: (0.0, None)}, existing=existing, initial=100.0)
        self.assertEqual({c[1] for c in cmds if c[0] == 2}, {7, 8})
        self.assertFalse([c for c in cmds if c[0] == 0], "nothing created")


@tagged("post_install", "-at_install")
class TestUpdateOpeningMove(AccountTestInvoicingCommon):
    def test_create_then_update_stays_balanced(self):
        company = self.company_data["company"]
        revenue = self.company_data["default_account_revenue"]
        expense = self.company_data["default_account_expense"]

        company._update_opening_move({revenue: (1000.0, 0.0), expense: (0.0, 400.0)})
        move = company.account_config_id.account_opening_move_id
        self.assertTrue(move, "opening move created")
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0, "balanced")
        self.assertEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )
        self.assertEqual(
            move.line_ids.filtered(lambda ln: ln.account_id == revenue).balance, 1000.0
        )

        company._update_opening_move({revenue: (500.0, 0.0)})
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)
        self.assertEqual(
            move.line_ids.filtered(lambda ln: ln.account_id == revenue).balance, 500.0
        )


@tagged("post_install", "-at_install")
class TestResCompanyCategoryDefaults(common.TransactionCase):
    def test_create_by_erp_manager_without_group_system(self):
        user = new_test_user(
            self.env,
            login="erp_manager_no_settings",
            groups="base.group_user,base.group_erp_manager,base.group_partner_manager",
        )
        company = (
            self.env["res.company"]
            .with_user(user)
            .create({"name": "Category Defaults Co"})
        )

        category_defaults = (
            self.env["ir.default"]
            .sudo()
            .search(
                [
                    ("company_id", "=", company.id),
                    ("field_id.model", "=", "product.category"),
                    (
                        "field_id.name",
                        "in",
                        [
                            "property_account_expense_categ_id",
                            "property_account_income_categ_id",
                        ],
                    ),
                ]
            )
        )
        self.assertEqual(
            sorted(category_defaults.field_id.mapped("name")),
            [
                "property_account_expense_categ_id",
                "property_account_income_categ_id",
            ],
            "creating a company must set both product.category account defaults",
        )
        self.assertFalse(
            any(category_defaults.mapped("user_id")),
            "the defaults are company-wide, which is what needs more rights than "
            "creating the company does",
        )
