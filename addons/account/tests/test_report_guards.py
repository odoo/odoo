import json
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.tests import tagged

from .common_report_engine import TestAccountReportsCommon


@tagged("post_install", "-at_install")
class TestReportValueFormatting(TestAccountReportsCommon):
    """A value must be called zero exactly when it is displayed as zero.

    formatLang divides by the rounding unit and drops every decimal, so at any unit
    other than "decimals" it displays as 0 long before the currency calls it zero.
    _is_value_zero has to be told the unit, or a report shown in millions renders
    -400,000 as "-0" and hide_0_lines keeps rows whose every cell reads 0.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("account.balance_sheet")
        cls.currency = cls.env.company.currency_id

    def _options(self, rounding_unit):
        return {"rounding_unit": rounding_unit, "multi_currency": False}

    def test_negative_value_below_the_unit_is_not_displayed_as_minus_zero(self):
        params = {"currency_id": self.currency.id}
        for rounding_unit, value in (
            ("thousands", -400.0),
            ("millions", -400.0),
            ("millions", -400000.0),
            ("lakhs", -400.0),
        ):
            with self.subTest(rounding_unit=rounding_unit, value=value):
                rendered = self.report._format_value(
                    self._options(rounding_unit), value, "monetary", params
                )
                self.assertNotIn(
                    "-", rendered, "a value that rounds to zero must not keep its sign"
                )

    def test_is_value_zero_agrees_with_what_is_rendered(self):
        params = {"currency_id": self.currency.id}
        for rounding_unit, value in (
            ("decimals", 400.0),
            ("decimals", 0.004),
            ("units", 0.4),
            ("thousands", 400.0),
            ("thousands", 400000.0),
            ("millions", 400000.0),
            ("millions", 4000000.0),
        ):
            with self.subTest(rounding_unit=rounding_unit, value=value):
                options = self._options(rounding_unit)
                rendered = self.report._format_value(options, value, "monetary", params)
                is_zero = self.report._is_value_zero(
                    value, "monetary", params, rounding_unit
                )
                renders_as_zero = not float(rendered.replace(",", ""))
                self.assertEqual(
                    is_zero,
                    renders_as_zero,
                    f"{value} renders as {rendered!r} but is_zero says {is_zero}",
                )

    def test_decimals_unit_still_defers_to_the_currency(self):
        params = {"currency_id": self.currency.id}
        self.assertTrue(
            self.report._is_value_zero(0.001, "monetary", params, "decimals")
        )
        self.assertFalse(
            self.report._is_value_zero(0.01, "monetary", params, "decimals")
        )

    def test_format_value_survives_options_without_a_rounding_unit(self):
        """format_value is public; a caller may hand it a partial options dict."""
        self.assertEqual(self.report.format_value({}, 12.5, "float"), "12.5")

    def test_hide_0_lines_hides_lines_that_render_as_zero(self):
        options = self._generate_options(
            self.report,
            "2025-01-01",
            "2025-12-31",
            default_options={
                "rounding_unit": "millions",
                "hide_0_lines": True,
                "export_mode": "print",
            },
        )
        for line in self.report._get_lines(options):
            rendered = [column.get("name") for column in line["columns"]]
            if rendered and all(
                isinstance(name, str) and name.strip().replace(",", "") in ("0", "0.00")
                for name in rendered
            ):
                self.fail(
                    f"line {line['name']!r} renders entirely as zero but was kept"
                )


@tagged("post_install", "-at_install")
class TestReportAggregationGuards(TestAccountReportsCommon):
    """Malformed report configuration must be reported, never crash or hang."""

    def _build_report(self, lines):
        report = self.env["report.formula"].create(
            {
                "name": "Guard probe",
                "filter_date_range": True,
                "column_ids": [
                    Command.create(
                        {
                            "name": "Balance",
                            "expression_label": "balance",
                            "sequence": 1,
                        }
                    )
                ],
            }
        )
        for sequence, (code, formula, subformula) in enumerate(lines, start=1):
            self.env["report.formula.line"].create(
                {
                    "name": code,
                    "code": code,
                    "report_id": report.id,
                    "sequence": sequence,
                    "expression_ids": [
                        Command.create(
                            {
                                "label": "balance",
                                "engine": "aggregation",
                                "formula": formula,
                                "subformula": subformula,
                            }
                        )
                    ],
                }
            )
        return report

    def test_mutually_referencing_aggregations_are_reported_not_looped(self):
        for label, subformula in (("bare", False), ("bounded", "if_above(USD(0))")):
            with self.subTest(subformula=label):
                report = self._build_report(
                    [
                        ("CYA" + label, "CYB" + label + ".balance", subformula),
                        ("CYB" + label, "CYA" + label + ".balance", subformula),
                    ]
                )
                with self.assertRaisesRegex(UserError, "Cyclic aggregation"):
                    report._get_lines(report.get_options({}))

    def test_three_node_aggregation_cycle_is_reported(self):
        report = self._build_report(
            [
                ("CY3A", "CY3B.balance", False),
                ("CY3B", "CY3C.balance", False),
                ("CY3C", "CY3A.balance", False),
            ]
        )
        with self.assertRaisesRegex(UserError, "Cyclic aggregation"):
            report._get_lines(report.get_options({}))

    def test_an_acyclic_aggregation_chain_still_computes(self):
        report = self._build_report(
            [
                ("CHX", "CHY.balance + 1.0", "if_above(USD(-1000))"),
                ("CHY", "2.0", False),
            ]
        )
        lines = report._get_lines(report.get_options({}))
        self.assertEqual(
            [line["columns"][0]["no_format"] for line in lines], [3.0, 2.0]
        )

    def test_malformed_bound_subformulas_raise_a_user_error(self):
        report = self.env.ref("account.balance_sheet")
        options = report.get_options({})
        for subformula in (
            "if_above(usd(0))",  # lower-case currency code
            "if_above(USD 0)",  # missing parentheses
            "gibberish(1)",
            "round(1,BAD)",  # unknown rounding method
            "rounding",  # starts with "round" but is not one
            "if_above(XYZ(1000))",  # well-formed, but no such currency
            "if_between(USD(1),XYZ(2))",  # only the second code is unknown
        ):
            with self.subTest(subformula=subformula), self.assertRaises(UserError):
                report._aggregation_apply_bounds(options, subformula, 12.345)

    def test_well_formed_bound_subformulas_are_applied(self):
        report = self.env.ref("account.balance_sheet")
        options = report.get_options({})
        self.assertEqual(
            report._aggregation_apply_bounds(options, "round(2)", 12.345), 12.34
        )
        self.assertEqual(
            report._aggregation_apply_bounds(options, "round( 2 )", 12.345), 12.34
        )
        self.assertEqual(
            report._aggregation_apply_bounds(options, "round(2, HALF-UP)", 12.345),
            12.35,
        )
        self.assertEqual(
            report._aggregation_apply_bounds(options, "if_above(USD(0))", 12.345),
            12.345,
        )
        self.assertIsNone(
            report._aggregation_apply_bounds(options, "if_below(USD(0))", 12.345)
        )

    def test_if_between_includes_both_bounds(self):
        """The docstring used to promise a strict interval; the comparison is <0 / >0,
        so a value sitting exactly on a bound is returned rather than dropped."""
        report = self.env.ref("account.balance_sheet")
        options = report.get_options({})
        code = self.env.company.currency_id.name
        subformula = f"if_between({code}(100),{code}(200))"
        for value in (100.0, 150.0, 200.0):
            with self.subTest(value=value):
                self.assertEqual(
                    report._aggregation_apply_bounds(options, subformula, value), value
                )
        for value in (99.99, 200.01):
            with self.subTest(value=value):
                self.assertIsNone(
                    report._aggregation_apply_bounds(options, subformula, value)
                )


@tagged("post_install", "-at_install")
class TestReportSortLinesInput(TestAccountReportsCommon):
    """sort_lines is called straight from the client, so its options are reachable input."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("account.general_ledger_report")
        cls.options = cls._generate_options(cls.report, "2025-01-01", "2025-12-31")
        cls.lines = cls.report._get_lines(cls.options)

    def test_an_order_column_that_names_nothing_leaves_the_lines_alone(self):
        for order_column in (
            None,
            {},
            {"expression_label": "no_such_column", "direction": "ASC"},
        ):
            with self.subTest(order_column=order_column):
                options = {**self.options, "order_column": order_column}
                self.assertEqual(
                    self.env["report.formula"].sort_lines(self.lines, options),
                    self.lines,
                )

    def test_result_as_index_keeps_its_contract_when_nothing_is_sorted(self):
        options = {**self.options, "order_column": None}
        self.assertEqual(
            self.env["report.formula"].sort_lines(
                self.lines, options, result_as_index=True
            ),
            list(range(len(self.lines))),
        )


@tagged("post_install", "-at_install")
class TestAuditAccountStatusAccess(TestAccountReportsCommon):
    """account.audit.account.status is an accountant's sign-off on an audited account.

    It used to be readable, writable and creatable by every internal user, and carried
    no multi-company rule while every sibling in the same feature has one.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.return_type = cls.env["account.return.type"].search([], limit=1)
        cls.account = cls.env["account.account"].search(
            cls.env["account.account"]._check_company_domain(cls.env.company), limit=1
        )
        cls.audit = cls.env["account.return"].create(
            {
                "name": "acl probe",
                "type_id": cls.return_type.id,
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "company_id": cls.env.company.id,
            }
        )
        cls.status = cls.env["account.audit.account.status"].create(
            {
                "audit_id": cls.audit.id,
                "account_id": cls.account.id,
                "status": "todo",
            }
        )

    def test_a_plain_internal_user_cannot_reach_an_audit_status(self):
        plain = self.env["res.users"].create(
            {
                "name": "plain internal",
                "login": "audit_status_plain",
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        self.env.invalidate_all()  # a restricted env otherwise reads the superuser's cache
        with self.assertRaises(AccessError):
            self.status.with_user(plain).read(["status"])
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.status.with_user(plain).write({"status": "reviewed"})

    def test_an_accountant_can(self):
        """Control: the group the feature is actually for still works."""
        accountant = self.env["res.users"].create(
            {
                "name": "accountant",
                "login": "audit_status_accountant",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_user").id,
                        ]
                    )
                ],
            }
        )
        self.env.invalidate_all()
        self.status.with_user(accountant).write({"status": "reviewed"})
        self.assertEqual(self.status.status, "reviewed")

    def test_an_audit_status_does_not_leak_across_companies(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        accountant = self.env["res.users"].create(
            {
                "name": "accountant elsewhere",
                "login": "audit_status_other_co",
                "company_id": other_company.id,
                "company_ids": [Command.set([other_company.id])],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_user").id,
                        ]
                    )
                ],
            }
        )
        self.env.invalidate_all()
        # Control: the parent return is already hidden by its own rule.
        self.assertFalse(
            self.env["account.return"]
            .with_user(accountant)
            .search_count([("id", "=", self.audit.id)])
        )
        self.env.invalidate_all()
        self.assertFalse(
            self.env["account.audit.account.status"]
            .with_user(accountant)
            .search_count([("id", "=", self.status.id)]),
            "an audit status must be scoped to the companies of the audit that owns it",
        )


@tagged("post_install", "-at_install")
class TestMultiCompanyScoping(TestAccountReportsCommon):
    """A record with no company of its own is scoped by the record that owns it.

    Budget items and tax units carried no rule at all, so they stayed visible from
    companies that could not see the budget -- or any member of the tax unit.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Scoping B"})
        cls.company_c = cls.env["res.company"].create({"name": "Scoping C"})
        cls.env.user.company_ids = [
            Command.link(cls.company_b.id),
            Command.link(cls.company_c.id),
        ]

        cls.budget_b = cls.env["account.report.budget"].create(
            {
                "name": "budget in B",
                "company_id": cls.company_b.id,
            }
        )
        cls.budget_item_b = cls.env["account.report.budget.item"].create(
            {
                "budget_id": cls.budget_b.id,
                "account_id": cls.env["account.account"].search([], limit=1).id,
                "amount": 100.0,
                "date": "2025-06-01",
            }
        )
        cls.tax_unit_bc = cls.env["account.tax.unit"].create(
            {
                "name": "unit of B and C",
                "country_id": cls.env.ref("base.be").id,
                "vat": "BE0999999922",
                "company_ids": [Command.set((cls.company_b + cls.company_c).ids)],
                "main_company_id": cls.company_b.id,
            }
        )

    def _visible(self, model, record, companies):
        self.env.invalidate_all()  # a wider environment's cache would answer otherwise
        return bool(
            self.env[model]
            .with_context(allowed_company_ids=companies.ids)
            .search_count([("id", "=", record.id)])
        )

    def test_a_budget_item_is_hidden_wherever_its_budget_is(self):
        # Control: the budget itself is already scoped by its own rule.
        self.assertFalse(
            self._visible("account.report.budget", self.budget_b, self.company_a)
        )
        self.assertFalse(
            self._visible(
                "account.report.budget.item", self.budget_item_b, self.company_a
            ),
            "a budget item must not outlive its budget's company scope",
        )

    def test_a_budget_item_is_visible_where_its_budget_is(self):
        allowed = self.company_a + self.company_b
        self.assertTrue(self._visible("account.report.budget", self.budget_b, allowed))
        self.assertTrue(
            self._visible("account.report.budget.item", self.budget_item_b, allowed)
        )

    def test_a_tax_unit_is_visible_only_to_its_members(self):
        self.assertFalse(
            self._visible("account.tax.unit", self.tax_unit_bc, self.company_a),
            "a tax unit must not be visible to a company outside it",
        )
        for member in (self.company_b, self.company_c):
            self.assertTrue(
                self._visible("account.tax.unit", self.tax_unit_bc, member),
                f"{member.name} is in the unit and must see it",
            )


@tagged("post_install", "-at_install")
class TestPaymentWizardBankExposure(TestAccountReportsCommon):
    """A related field is privileged by default (coding_guidelines.rst 10.5).

    bank_account_id is a plain many2one the user sets, so a privileged read of
    acc_number hands back the IBAN of any bank account in the database.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "Bank Exposure B"})
        partner_b = cls.env["res.partner"].create(
            {
                "name": "B's supplier",
                "company_id": cls.company_b.id,
            }
        )
        cls.bank_b = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "BE68539007547034",
                "partner_id": partner_b.id,
                "company_id": cls.company_b.id,
            }
        )
        partner_a = cls.env["res.partner"].create(
            {
                "name": "A's supplier",
                "company_id": cls.env.company.id,
            }
        )
        cls.bank_a = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "BE71096123456769",
                "partner_id": partner_a.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.account_return = cls.env["account.return"].create(
            {
                "name": "payment probe",
                "type_id": cls.env["account.return.type"].search([], limit=1).id,
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "company_id": cls.env.company.id,
            }
        )
        cls.accountant_a = cls.env["res.users"].create(
            {
                "name": "accountant in A",
                "login": "payment_wizard_acct_a",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set(cls.env.company.ids)],
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("account.group_account_user").id,
                        ]
                    )
                ],
            }
        )

    def _wizard_on(self, bank):
        return (
            self.env["account.return.payment.wizard"]
            .with_user(self.accountant_a)
            .create({"return_id": self.account_return.id, "bank_account_id": bank.id})
        )

    def test_the_wizard_does_not_reveal_a_bank_account_the_reader_cannot_read(self):
        self.env.invalidate_all()
        # Control: the same user is refused a direct read.
        with self.assertRaises(AccessError):
            self.bank_b.with_user(self.accountant_a).read(["acc_number"])
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self._wizard_on(self.bank_b).acc_number

    def test_the_wizard_still_shows_a_bank_account_the_reader_can_read(self):
        stored = self.bank_a.acc_number
        self.env.invalidate_all()
        self.assertEqual(self._wizard_on(self.bank_a).acc_number, stored)


@tagged("post_install", "-at_install")
class TestEveryReportRenders(TestAccountReportsCommon):
    """A crash net over the whole module.

    Every shipped report, under each filter toggle and each pair of toggles, then
    every unfoldable line of the plain render expanded. It asserts nothing about the
    figures -- the per-report suites do that -- only that no combination raises. The
    engines, the expansion path and the option initialisers have many more
    combinations than the per-report tests exercise, and this module's suite only
    started running in CI recently.
    """

    # Guards that are correct behaviour, not failures: a report that needs a second
    # currency, and the sections source that reroutes its own report_id.
    EXPECTED = ("activate more than one currency", "Inconsistent report_id")

    TOGGLES = (
        (
            "comparison",
            {"comparison": {"filter": "previous_period", "number_period": 2}},
        ),
        ("hierarchy", {"hierarchy": True}),
        ("unfold_all", {"unfold_all": True}),
        ("all_entries", {"all_entries": True}),
        ("hide_0_lines", {"hide_0_lines": True}),
        ("millions", {"rounding_unit": "millions"}),
        ("multi_currency", {"multi_currency": True}),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reports = cls.env["report.formula"].search([])
        # The net needs lines that actually have sublines: a report line is only
        # unfoldable when its groupby resolves to something, so an empty ledger
        # leaves nothing to expand and the net would silently test nothing.
        journal = cls.company_data["default_journal_misc"]
        moves = cls.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": "2025-06-15",
                    "journal_id": journal.id,
                    "partner_id": cls.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                                "partner_id": cls.partner_a.id,
                                "balance": -amount,
                            }
                        ),
                        Command.create(
                            {
                                "account_id": cls.company_data[
                                    "default_account_receivable"
                                ].id,
                                "partner_id": cls.partner_a.id,
                                "balance": amount,
                            }
                        ),
                    ],
                }
                for amount in (100.0, 250.0, 375.0)
            ]
        )
        moves.action_post()

    def _render(self, report, previous_options, label):
        try:
            options = report.get_options(previous_options)
            return options, report._get_lines(options)
        except UserError as e:
            if any(expected in str(e) for expected in self.EXPECTED):
                return None, None
            raise AssertionError(f"{report.name} [{label}]: {e}") from e
        except Exception as e:
            raise AssertionError(f"{report.name} [{label}]: {e!r}") from e

    def test_every_report_renders_under_every_pair_of_filters(self):
        import itertools

        base = self._generate_options(self.reports[0], "2025-01-01", "2025-12-31")
        dates = {"date": base["date"]}
        rendered = 0
        for report in self.reports:
            for size in (0, 1, 2):
                for combo in itertools.combinations(self.TOGGLES, size):
                    previous = dict(dates)
                    for _name, value in combo:
                        previous.update(value)
                    label = "+".join(name for name, _ in combo) or "plain"
                    with self.subTest(report=report.name, filters=label):
                        _options, lines = self._render(report, previous, label)
                        rendered += lines is not None
        self.assertGreater(rendered, 0, "the matrix rendered nothing at all")

    def test_every_unfoldable_line_expands(self):
        base = self._generate_options(self.reports[0], "2025-01-01", "2025-12-31")
        dates = {"date": base["date"]}
        expanded = 0
        for report in self.reports:
            options, lines = self._render(report, dict(dates), "plain")
            if lines is None:
                continue
            for line in lines:
                # Mirror the client: it offers the caret only on an unfoldable line,
                # and unfoldLine() then needs an expand_function.
                if not (line.get("unfoldable") and line.get("expand_function")):
                    continue
                with self.subTest(report=report.name, line=line["name"]):
                    try:
                        report.get_expanded_lines(
                            options,
                            line["id"],
                            line.get("groupby"),
                            line["expand_function"],
                            None,
                            0,
                            line.get("horizontal_split_side"),
                        )
                    except Exception as e:
                        raise AssertionError(
                            f"{report.name} / {line['name']}: {e!r}"
                        ) from e
                    expanded += 1
        self.assertGreater(
            expanded, 0, "no line was expandable; the net caught nothing"
        )


@tagged("post_install", "-at_install")
class TestExportTestFlagIsNotClientSettable(TestAccountReportsCommon):
    """`_running_export_test` reaches get_options through client-supplied options.

    Three l10n modules branch on it and two use it to skip a check -- l10n_es waives
    the BOE date validation, l10n_ar deselects the purchase book "to avoid raising".
    A user must not be able to ask for that waiver from a browser.
    """

    def test_the_flag_is_honoured_while_a_test_runs(self):
        """Control: TestAllReportsGeneration depends on this working."""
        report = self.env.ref("account.balance_sheet")
        options = report.get_options({"_running_export_test": True})
        self.assertTrue(options.get("_running_export_test"))

    def test_the_flag_is_ignored_when_no_test_is_running(self):
        report = self.env.ref("account.balance_sheet")
        with patch("odoo.modules.module.current_test", False):
            options = report.get_options({"_running_export_test": True})
        self.assertFalse(
            options.get("_running_export_test"),
            "a browser must not be able to switch the reports into export-test mode",
        )


@tagged("post_install", "-at_install")
class TestAccountsCoverageReportCodelessAccounts(TestAccountReportsCommon):
    """account.account.code is computed per company and reads False for an account
    that belongs to another one.

    The coverage report's domain-engine branch searches accounts with no company
    filter, so those Falses reach the code sets and used to make sorted() compare
    str against bool.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Build the report rather than look for one: whether any shipped report
        # offers the coverage tool depends on the installed localisation, and a
        # test that skips itself on a generic database guards nothing.
        root = cls.env.ref("account.balance_sheet")
        cls.report = cls.env["report.formula"].create(
            {
                "name": "Coverage probe",
                "root_report_id": root.id,
                "availability_condition": "always",
                "line_ids": [
                    Command.create(
                        {
                            "name": "Cash",
                            "code": "COVCASH",
                            "expression_ids": [
                                Command.create(
                                    {
                                        "label": "balance",
                                        "engine": "domain",
                                        "formula": "[('account_id.account_type', '=', 'asset_cash')]",
                                        "subformula": "sum",
                                    }
                                )
                            ],
                        }
                    )
                ],
            }
        )
        assert cls.report.is_account_coverage_report_available

    def test_an_account_of_another_company_does_not_break_the_coverage_report(self):
        other_company = self.company_data_2["company"]
        foreign_account = (
            self.env["account.account"]
            .with_company(other_company)
            .create(
                {
                    "name": "Coverage foreign cash",
                    "code": "ZZCOV9",
                    "account_type": "asset_cash",
                    "company_ids": [Command.set(other_company.ids)],
                }
            )
        )
        self.assertFalse(
            foreign_account.with_company(self.env.company).code,
            "the premise: the account has no code in the active company",
        )

        lines = self.report._generate_accounts_coverage_report_xlsx_lines()
        self.assertIsInstance(lines, list)


@tagged("post_install", "-at_install")
class TestSortLinesKeepsEveryLine(TestAccountReportsCommon):
    """sort_lines walks a tree rooted on the lines whose parent is not in the list.

    It used to root the walk on the None sentinel alone, so a list whose lines all
    carry a parent -- what the hierarchy produces, since its root is referenced but
    never emitted -- walked an empty branch and came back empty.
    """

    def test_a_hierarchy_keeps_every_line_through_the_sort(self):
        report = self.env.ref("account.trial_balance_report")
        options = self._generate_options(
            report, "2025-01-01", "2025-12-31", default_options={"hierarchy": True}
        )
        lines = report._get_lines(options)
        self.assertTrue(lines, "no lines to sort; nothing tested")
        self.assertFalse(
            any(line.get("parent_id") is None for line in lines),
            "the premise: the hierarchy roots every line on a parent it never emits",
        )

        for column in options["columns"]:
            for direction in ("ASC", "DESC"):
                with self.subTest(
                    column=column["expression_label"], direction=direction
                ):
                    sorted_lines = report.sort_lines(
                        lines,
                        {
                            **options,
                            "order_column": {
                                "expression_label": column["expression_label"],
                                "direction": direction,
                            },
                        },
                    )
                    self.assertEqual(
                        len(sorted_lines),
                        len(lines),
                        "sorting must not add or drop a line",
                    )
                    self.assertEqual(
                        {line["id"] for line in sorted_lines},
                        {line["id"] for line in lines},
                    )


@tagged("post_install", "-at_install")
class TestSortLinesShortLines(TestAccountReportsCommon):
    """A report line may carry fewer cells than options["columns"] declares.

    The journal report's tax summary section headings carry none at all, and
    sort_lines indexed straight into the list, so any client-supplied order_column
    raised IndexError instead of sorting.
    """

    def test_a_line_with_no_columns_does_not_break_the_sort(self):
        invoice = self.init_invoice(
            "out_invoice",
            invoice_date="2025-03-01",
            amounts=[1000.0],
            taxes=self.company_data["default_tax_sale"],
        )
        invoice.action_post()

        report = self.env.ref("account.journal_report")
        options = self._generate_options(report, "2025-01-01", "2025-12-31")
        lines = report._get_lines(options)
        self.assertTrue(
            any(len(line["columns"]) < len(options["columns"]) for line in lines),
            "the premise: this report emits a line shorter than its own options",
        )

        for column in options["columns"]:
            for direction in ("ASC", "DESC"):
                with self.subTest(
                    column=column["expression_label"], direction=direction
                ):
                    sorted_lines = report.sort_lines(
                        lines,
                        {
                            **options,
                            "order_column": {
                                "expression_label": column["expression_label"],
                                "direction": direction,
                            },
                        },
                    )
                    self.assertEqual(len(sorted_lines), len(lines))


@tagged("post_install", "-at_install")
class TestNewCompanyGetsDeadlineDefaults(TestAccountReportsCommon):
    """res.company.create used to pre-filter the return types needing defaults with
    a domain on deadline_periodicity / deadline_start_date.

    Both are company_dependent, so the domain resolved against the creating user's
    company. Once a type was configured there -- the steady state -- it was excluded
    and the new company got no deadline configuration at all.
    """

    def test_a_new_company_picks_up_every_deadline_default(self):
        return_type = self.env["account.return.type"].search([], limit=1)
        self.assertTrue(return_type, "no return type to configure; nothing tested")

        return_type.with_company(self.env.company).write(
            {
                "deadline_periodicity": "monthly",
                "deadline_start_date": "2025-01-01",
            }
        )
        return_type.write(
            {
                "default_deadline_periodicity": "trimester",
                "default_deadline_start_date": "2024-06-01",
                "default_deadline_days_delay": 17,
            }
        )

        new_company = self.env["res.company"].create({"name": "Deadline defaults co"})

        configured = return_type.with_company(new_company)
        self.assertEqual(configured.deadline_periodicity, "trimester")
        self.assertEqual(
            configured.deadline_start_date, fields.Date.to_date("2024-06-01")
        )
        self.assertEqual(configured.deadline_days_delay, 17)


@tagged("post_install", "-at_install")
class TestAuditReturnPreviousPeriodScoping(TestAccountReportsCommon):
    """Creating an audit return carries the previous period's account statuses
    forward.

    The lookup used to compute its boundaries from self.env.company -- the active
    company, not the return's -- and then search for the previous return with no
    company and no tax-unit scoping at all.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.audit_type = cls.env["account.return.type"].search(
            [("category", "=", "audit")], limit=1
        )
        cls.company_a = cls.env.company
        cls.company_b = cls.company_data_2["company"]

    def _create_audit(self, company, date_from, date_to, name):
        return self.env["account.return"].create(
            {
                "name": name,
                "type_id": self.audit_type.id,
                "company_id": company.id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )

    def _shared_account(self):
        """An account both companies can see, so a status can actually leak."""
        account = (
            self.env["account.account"]
            .with_company(self.company_a)
            .create(
                {
                    "name": "Audit scoping shared",
                    "code": "ZZAUD1",
                    "account_type": "asset_current",
                }
            )
        )
        account.with_company(self.company_b).write(
            {"company_ids": [Command.link(self.company_b.id)], "code": "ZZAUD1"}
        )
        return account

    def test_the_previous_period_is_read_off_the_returns_own_company(self):
        self.assertTrue(self.audit_type, "no audit return type; nothing tested")
        self.company_a.account_config_id.write(
            {"fiscalyear_last_day": 31, "fiscalyear_last_month": "12"}
        )
        self.company_b.account_config_id.write(
            {"fiscalyear_last_day": 31, "fiscalyear_last_month": "3"}
        )

        current_from, current_to = self.audit_type._get_period_boundaries(
            self.company_b, fields.Date.to_date("2026-06-30")
        )
        previous_from, previous_to = self.audit_type._get_period_boundaries(
            self.company_b, current_from - relativedelta(days=1)
        )
        self.assertNotEqual(
            (previous_from, previous_to),
            self.audit_type._get_period_boundaries(
                self.company_a, current_from - relativedelta(days=1)
            ),
            "the premise: the two companies disagree on where the period starts",
        )

        account = self._shared_account()
        previous = self._create_audit(
            self.company_b, previous_from, previous_to, "audit B previous"
        )
        previous_status = self.env["account.audit.account.status"].search(
            [("audit_id", "=", previous.id), ("account_id", "=", account.id)]
        )
        self.assertTrue(previous_status, "the previous audit did not cover the account")
        previous_status.status = "todo"

        current = self._create_audit(
            self.company_b, current_from, current_to, "audit B current"
        )
        carried = self.env["account.audit.account.status"].search(
            [("audit_id", "=", current.id), ("account_id", "=", account.id)]
        )
        self.assertEqual(
            carried.status,
            "todo",
            "the status of the previous period must be carried forward",
        )

    def test_the_previous_period_is_not_taken_from_another_company(self):
        self.assertTrue(self.audit_type, "no audit return type; nothing tested")
        for company in (self.company_a, self.company_b):
            company.account_config_id.write(
                {"fiscalyear_last_day": 31, "fiscalyear_last_month": "12"}
            )

        current_from, current_to = self.audit_type._get_period_boundaries(
            self.company_b, fields.Date.to_date("2026-06-30")
        )
        previous_from, previous_to = self.audit_type._get_period_boundaries(
            self.company_b, current_from - relativedelta(days=1)
        )

        account = self._shared_account()
        foreign = self._create_audit(
            self.company_a, previous_from, previous_to, "audit A previous"
        )
        foreign_status = self.env["account.audit.account.status"].search(
            [("audit_id", "=", foreign.id), ("account_id", "=", account.id)]
        )
        self.assertTrue(foreign_status, "the foreign audit did not cover the account")
        foreign_status.status = "todo"

        current = self._create_audit(
            self.company_b, current_from, current_to, "audit B current"
        )
        carried = self.env["account.audit.account.status"].search(
            [("audit_id", "=", current.id), ("account_id", "=", account.id)]
        )
        self.assertFalse(
            carried.status,
            "another company's audit must not decide what this one reviews",
        )


@tagged("post_install", "-at_install")
class TestBudgetItemAccess(TestAccountReportsCommon):
    """A Basic accounting user could read a budget but not its items.

    group_account_basic implies only group_account_invoice, so this gap does not
    close when accountant is installed.
    """

    def test_a_basic_user_reads_a_budget_and_its_items_alike(self):
        basic = self.env["res.users"].create(
            {
                "name": "basic accountant",
                "login": "budget_item_acl_basic",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_basic").id,
                        ]
                    )
                ],
            }
        )
        for model in ("account.report.budget", "account.report.budget.item"):
            with self.subTest(model=model):
                self.env[model].with_user(basic).check_access("read")


@tagged("post_install", "-at_install")
class TestManagerReachesTheModulesAcls(TestAccountReportsCommon):
    """group_account_manager does not imply group_account_user.

    That implication is added by accountant, which depends on account_reports, so
    in any install that pulls this module without it -- around 25 l10n_*_reports
    do -- an Accounting Administrator was denied everything the module grants only
    to group_account_user.
    """

    def test_a_manager_reaches_what_the_module_grants(self):
        manager = self.env["res.users"].create(
            {
                "name": "accounting administrator",
                "login": "module_acl_manager",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_manager").id,
                        ]
                    )
                ],
            }
        )
        for model, operation in (
            ("account.return", "create"),
            ("account.return.check", "write"),
            ("account.return.check.template", "create"),
            ("account.report.annotation", "create"),
            ("account_reports.export.wizard", "create"),
            ("account.multicurrency.revaluation.wizard", "create"),
            ("account.return.creation.wizard", "create"),
            ("account.return.submission.wizard", "create"),
            ("account.return.payment.wizard", "create"),
            ("qr.code.payment.wizard", "create"),
            ("account.audit.account.status", "write"),
        ):
            with self.subTest(model=model, operation=operation):
                self.env[model].with_user(manager).check_access(operation)


@tagged("post_install", "-at_install")
class TestBudgetFilterIsMultiCompany(TestAccountReportsCommon):
    """The budget filter listed the active company's budgets only, while the
    entries it builds carry a company_id -- a key that only means something if
    budgets from several companies can appear.
    """

    def test_the_filter_lists_every_selected_companys_budgets(self):
        report = self.env["report.formula"].search(
            [("filter_budgets", "=", True)], limit=1
        )
        self.assertTrue(report, "no report offers the budget filter; nothing tested")

        other_company = self.company_data_2["company"]
        here = self.env["account.report.budget"].create(
            {"name": "budget here", "company_id": self.env.company.id}
        )
        there = self.env["account.report.budget"].create(
            {"name": "budget there", "company_id": other_company.id}
        )

        options = report.with_context(
            allowed_company_ids=[self.env.company.id, other_company.id]
        ).get_options({})
        listed = {budget["id"] for budget in options["budgets"]}
        self.assertIn(here.id, listed)
        self.assertIn(
            there.id,
            listed,
            "a budget of another selected company must be offered too",
        )


@tagged("post_install", "-at_install")
class TestLineIdIsClientInput(TestAccountReportsCommon):
    """Line ids arrive from the client on every caret, audit, unfold and sort
    action, and the parser used to let a malformed one out as a bare ValueError,
    i.e. a 500 rather than a message.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("account.balance_sheet")

    def test_a_malformed_line_id_raises_a_user_error(self):
        for line_id in (
            "garbage",  # no separator at all
            "x~account.account~abc",  # value is not an id
            "a~b~1||c~d~2",  # empty segment between two delimiters
            "~account.account~",  # model without a value is fine, but paired here
        ):
            with self.subTest(line_id=line_id):
                try:
                    self.report._parse_line_id(line_id)
                except UserError:
                    pass
                except ValueError as e:
                    raise AssertionError(
                        f"{line_id!r} surfaced as a server error: {e!r}"
                    ) from e

    def test_the_sort_path_reports_a_bad_line_id_as_a_user_error(self):
        with self.assertRaises(UserError):
            self.report._get_model_info_from_id("x~account.account~abc")

    def test_a_well_formed_line_id_still_parses(self):
        self.assertEqual(
            self.report._parse_line_id("markup~account.account~5"),
            [("markup", "account.account", 5)],
        )
        self.assertEqual(self.report._parse_line_id(""), [])
        # An empty markup stays the empty string, as it always has.
        self.assertEqual(
            self.report._parse_line_id("~~Acme"),
            [("", None, "Acme")],
        )


@tagged("post_install", "-at_install")
class TestLineIdDelimitersAreRejected(TestAccountReportsCommon):
    """The generic line id joins markup~model~value and escapes nothing.

    A segment carrying either delimiter used to build an id that could not be
    parsed back, and the failure only surfaced later, wherever something tried.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("account.balance_sheet")

    def test_a_segment_carrying_a_delimiter_is_refused_at_build_time(self):
        for markup, value in (
            ("m", "Ac~me"),
            ("m", "Ac|me"),
            ("a|b", "x"),
            ("a~b", "x"),
        ):
            with self.subTest(markup=markup, value=value), self.assertRaises(UserError):
                self.report._get_generic_line_id(None, value, markup=markup)

    def test_a_clean_segment_still_round_trips(self):
        line_id = self.report._get_generic_line_id(None, "Acme", markup="m")
        self.assertEqual(self.report._parse_line_id(line_id)[-1], ("m", None, "Acme"))


@tagged("post_install", "-at_install")
class TestDispatchOnSectionsSource(TestAccountReportsCommon):
    """on_sections_source and sections_source_id both come from the client.

    The sections branch browsed the source with no relationship check and assigned
    report_id into the caller's own options, which made the compatibility guard
    below it unreachable on that path.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = cls.env["report.formula"].search(
            [("section_report_ids", "!=", False)], limit=1
        )

    def test_a_report_that_is_not_a_section_of_the_source_is_refused(self):
        self.assertTrue(self.source, "no report has sections; nothing tested")
        section = self.source.section_report_ids[0]
        stranger = self.env["report.formula"].search(
            [("id", "not in", (self.source | self.source.section_report_ids).ids)],
            limit=1,
        )
        self.assertTrue(stranger, "no unrelated report to point at")

        options = {
            **self.source.get_options({}),
            "sections_source_id": stranger.id,
        }
        with self.assertRaises(UserError):
            section.dispatch_report_action(
                options,
                "get_default_report_filename",
                action_param="pdf",
                on_sections_source=True,
            )

    def test_a_report_dispatching_on_its_own_options_is_allowed(self):
        """_init_options_sections points sections_source_id at the report itself,
        or at its selected variant. Both are legitimate and must not be refused."""
        for report in self.env["report.formula"].search([], limit=12):
            options = report.get_options({})
            source = self.env["report.formula"].browse(options["sections_source_id"])
            with self.subTest(report=report.name, source=source.name):
                report.dispatch_report_action(
                    options,
                    "get_default_report_filename",
                    action_param="pdf",
                    on_sections_source=True,
                )

    def test_the_caller_s_options_are_not_mutated(self):
        self.assertTrue(self.source, "no report has sections; nothing tested")
        section = self.source.section_report_ids[0]
        options = {
            **self.source.get_options({}),
            "sections_source_id": self.source.id,
            "report_id": section.id,
        }
        section.dispatch_report_action(
            options,
            "get_default_report_filename",
            action_param="pdf",
            on_sections_source=True,
        )
        self.assertEqual(
            options["report_id"],
            section.id,
            "dispatching must not rewrite the dict the caller still holds",
        )


@tagged("post_install", "-at_install")
class TestCoverageReportDomainRewrite(TestAccountReportsCommon):
    """The coverage report rewrites a domain-engine formula from account.move.line
    terms to account.account ones.

    It used to do it by list surgery, popping the operator only when the skipped
    term followed it directly, which left a dangling operator with one operand.
    """

    def _rewrite(self, domain):
        """Run the report's rewrite over a domain and return the account domain."""
        report = self.env.ref("account.balance_sheet")
        rewritten = []
        real_search = type(self.env["account.account"]).search

        def spy(records, args, **kwargs):
            rewritten.append(args)
            return real_search(records, args, **kwargs)

        expression = report.line_ids.expression_ids.filtered(
            lambda e: e.engine == "domain"
        )[:1]
        self.assertTrue(expression, "the balance sheet has no domain expression")
        expression.formula = repr(domain)
        with patch.object(type(self.env["account.account"]), "search", spy):
            report._generate_accounts_coverage_report_xlsx_lines()
        return rewritten

    def test_an_operator_whose_second_operand_is_stripped_stays_well_formed(self):
        date = "2020-01-01"
        for domain in (
            [("account_id.code", "=like", "4%")],
            [("date", ">", date), ("account_id.code", "=like", "4%")],
            ["&", ("date", ">", date), ("account_id.code", "=like", "4%")],
            ["&", ("account_id.code", "=like", "4%"), ("date", ">", date)],
            ["|", ("account_id.code", "=like", "4%"), ("date", ">", date)],
            [("date", ">", date)],
        ):
            with self.subTest(domain=domain):
                # Raising at all is the failure: the old rewriter produced
                # ['&', ['code', '=like', '4%']] for the fourth case.
                self._rewrite(domain)

    def test_an_or_between_two_account_terms_is_preserved(self):
        """Flattening the tree would turn this union into an intersection."""
        Account = self.env["account.account"].with_context(active_test=False)
        four = Account.search_count([("code", "=like", "4%")])
        five = Account.search_count([("code", "=like", "5%")])
        self.assertTrue(four and five, "no accounts to tell union from intersection")

        both = Account.search_count(
            Domain(
                [
                    "|",
                    ("code", "=like", "4%"),
                    ("code", "=like", "5%"),
                ]
            )
        )
        self.assertEqual(both, four + five)


@tagged("post_install", "-at_install")
class TestAnnotationChatterLoad(TestAccountReportsCommon):
    """The chatter map behind annotations needs one number per line: the move id of
    each annotatable move line. Reading `move_id` the ordinary way makes the ORM
    resolve every one of those moves to a display name as well, and nothing ever
    displays them -- the map is consumed as `{"model": "account.move", "id": <id>}`.
    """

    def _annotatable_line(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2020-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "balance": 500.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "balance": -500.0,
                        }
                    ),
                ],
            }
        )
        return move.line_ids[0]

    def _spy_on_display_name(self):
        """Returns (context manager, list that collects every resolved move id)."""
        resolved = []
        move_cls = type(self.env["account.move"])
        original = move_cls._compute_display_name

        def _spy(records):
            resolved.append(records.ids)
            return original(records)

        return patch.object(move_cls, "_compute_display_name", _spy), resolved

    def test_chatter_map_does_not_resolve_move_display_names(self):
        aml = self._annotatable_line()
        report = self.env.ref("account.general_ledger_report")
        lines = [{"id": report._get_generic_line_id("account.move.line", aml.id)}]

        spy, resolved = self._spy_on_display_name()
        with spy:
            report._postprocess_chatter_for_annotations(lines)

        self.assertEqual(
            lines[0]["chatter"],
            {"model": "account.move", "id": aml.move_id.id},
            "the chatter must still point at the line's move",
        )
        self.assertFalse(
            resolved,
            "building the chatter map must not resolve any account.move display"
            f" name; it resolved {resolved}",
        )

    def test_general_ledger_postprocessor_does_not_resolve_display_names(self):
        """The general ledger keeps its own copy of the same map."""
        aml = self._annotatable_line()
        report = self.env.ref("account.general_ledger_report")
        handler = self.env["account.general.ledger.report.handler"]
        # The general ledger only attaches a chatter to its own accumulated-balance
        # rows: no model, that markup, and a JSON res_id whose second element is
        # the move line id (models/account_general_ledger.py:605-612).
        lines = [
            {
                "id": report._get_generic_line_id(
                    None,
                    json.dumps(["account.move.line", aml.id]),
                    markup={"groupby": "id_with_accumulated_balance"},
                ),
                "columns": [],
            }
        ]

        spy, resolved = self._spy_on_display_name()
        with spy:
            handler._custom_line_postprocessor(report, {}, lines)

        self.assertEqual(
            lines[0]["chatter"],
            {"model": "account.move", "id": aml.move_id.id},
            "the general ledger rewrites the chatter onto the move",
        )
        self.assertFalse(
            resolved,
            "the general ledger must not resolve display names either;"
            f" it resolved {resolved}",
        )
