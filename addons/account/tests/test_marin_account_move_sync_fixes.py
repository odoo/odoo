import ast
import collections
import inspect
import textwrap

from odoo import Command
from odoo.tests import tagged
from odoo.tools import frozendict

from odoo.addons.account.models.account_move_sync import AccountMove
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMarinAccountMoveSyncFixes(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.rounding_profit = cls.company_data["default_account_revenue"].copy()
        cls.rounding_loss = cls.company_data["default_account_expense"].copy()

    def _cash_rounding(self, strategy, rounding=0.05, with_accounts=True):
        vals = {
            "name": "R %s %s" % (strategy, rounding),
            "rounding": rounding,
            "strategy": strategy,
            "rounding_method": "HALF-UP",
        }
        if with_accounts:
            vals["profit_account_id"] = self.rounding_profit.id
            vals["loss_account_id"] = self.rounding_loss.id
        return self.env["account.cash.rounding"].create(vals)

    def _rounded_invoice(self, cash_rounding, price_unit, taxes):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_cash_rounding_id": cash_rounding.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "p",
                            "quantity": 1,
                            "price_unit": price_unit,
                            "tax_ids": [Command.set(taxes.ids)],
                        }
                    )
                ],
            }
        )

    def _unbalanced_entry(self, env, first_line_name):
        expense = self.company_data["default_account_expense"]
        revenue = self.company_data["default_account_revenue"]
        return env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "name": first_line_name,
                            "account_id": expense.id,
                            "balance": 60.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "taxed",
                            "account_id": expense.id,
                            "balance": 40.0,
                            "tax_ids": [
                                Command.set(
                                    self.company_data["default_tax_purchase"].ids
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "counterpart",
                            "account_id": revenue.id,
                            "balance": -100.0,
                        }
                    ),
                ],
            }
        )

    def test_balancing_line_never_hijacks_a_line_by_name(self):
        marker_by_lang = {
            lang: self.env["account.move"]
            .with_context(lang=lang)
            .env._("Automatic Balancing Line")
            for lang in ("en_US", "fr_FR")
        }
        self.assertNotEqual(
            marker_by_lang["en_US"],
            marker_by_lang["fr_FR"],
            "this test is only meaningful while the marker is translated",
        )

        for lang in ("en_US", "fr_FR"):
            env = self.env(context=dict(self.env.context, lang=lang))
            for name in marker_by_lang.values():
                with self.subTest(acting_lang=lang, line_named=name):
                    move = self._unbalanced_entry(env, name)
                    entered = move.line_ids.filtered(
                        lambda line, name=name: (
                            line.display_type != "balancing" and line.name == name
                        )
                    )
                    self.assertEqual(
                        entered.balance,
                        60.0,
                        "a line the user named after the marker must keep its amount",
                    )
                    balancing = move.line_ids.filtered(
                        lambda line: line.display_type == "balancing"
                    )
                    self.assertEqual(len(balancing), 1)
                    tax_total = sum(
                        move.line_ids.filtered("tax_repartition_line_id").mapped(
                            "balance"
                        )
                    )
                    self.assertTrue(tax_total)
                    self.assertEqual(balancing.balance, -tax_total)
                    self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def test_cash_rounding_line_is_written_in_place_for_both_strategies(self):
        tax = self.env["account.tax"].create(
            {
                "name": "sync 10%",
                "amount_type": "percent",
                "amount": 10.0,
                "type_tax_use": "sale",
                "company_ids": [Command.set(self.env.company.ids)],
            }
        )
        for strategy in ("biggest_tax", "add_invoice_line"):
            with self.subTest(strategy=strategy):
                invoice = self._rounded_invoice(
                    self._cash_rounding(strategy), 11.11, tax
                )
                product_line = invoice.line_ids.filtered(
                    lambda line: line.display_type == "product"
                )
                previous_id = None
                recreated = 0
                for step in range(1, 21):
                    product_line.price_unit = 11.11 + 0.01 * step
                    rounding_line = invoice.line_ids.filtered(
                        lambda line: line.display_type == "rounding"
                    )
                    current_id = rounding_line.id if rounding_line else None
                    if current_id and previous_id and current_id != previous_id:
                        recreated += 1
                    previous_id = current_id
                self.assertEqual(
                    recreated,
                    0,
                    "the rounding line must be updated, not deleted and recreated",
                )

    def test_cash_rounding_applies_without_any_tax_line(self):
        for strategy in ("biggest_tax", "add_invoice_line"):
            with self.subTest(strategy=strategy):
                invoice = self._rounded_invoice(
                    self._cash_rounding(strategy, rounding=1.0),
                    100.4,
                    self.env["account.tax"],
                )
                self.assertEqual(invoice.amount_total, 100.0)

    def test_cash_rounding_without_accounts_does_not_raise(self):
        invoice = self._rounded_invoice(
            self._cash_rounding("biggest_tax", rounding=1.0, with_accounts=False),
            100.4,
            self.env["account.tax"],
        )
        self.assertEqual(invoice.amount_total, 100.4)

    def test_tracked_base_lines_match_the_tax_computation(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "x",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "deductible_amount": 50,
                            "tax_ids": [
                                Command.set(
                                    self.company_data["default_tax_purchase"].ids
                                )
                            ],
                        }
                    )
                ],
            }
        )
        self.env["account.move.line"].create(
            [
                {
                    "move_id": invoice.id,
                    "display_type": "cogs",
                    "name": "cogs debit",
                    "account_id": self.company_data["default_account_expense"].id,
                    "balance": 70.0,
                },
                {
                    "move_id": invoice.id,
                    "display_type": "cogs",
                    "name": "cogs credit",
                    "account_id": self.company_data["default_account_revenue"].id,
                    "balance": -70.0,
                },
            ]
        )
        base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines()
        computed = self.env["account.move.line"].browse(
            [base_line["record"].id for base_line in base_lines]
        )
        self.assertEqual(
            set(invoice._get_tax_base_amls().ids),
            set(computed.ids),
            "the change detector and the tax computation must agree on base lines",
        )

    def _needed_values_key(self):
        move = self.env["account.move"].create(
            {"move_type": "entry", "date": "2026-01-01"}
        )
        return frozendict(
            {
                "move_id": move.id,
                "account_id": self.company_data["default_account_revenue"].id,
            }
        )

    def test_needed_values_merge_is_order_independent(self):
        key = self._needed_values_key()
        left = {"balance": 10.0, "amount_currency": 10.0}
        right = {
            "balance": -4.0,
            "amount_currency": -4.0,
            "discount_date": "2026-01-01",
        }
        forward = self.env["account.move"]._sync_dynamic_line_needed_values(
            [{key: left}, {key: right}]
        )
        backward = self.env["account.move"]._sync_dynamic_line_needed_values(
            [{key: right}, {key: left}]
        )
        self.assertEqual(set(forward[key]), set(backward[key]))
        self.assertEqual(
            set(forward[key]), {"balance", "amount_currency", "discount_date"}
        )
        self.assertEqual(forward[key]["balance"], backward[key]["balance"])

    def test_needed_values_merge_tolerates_a_missing_monetary_field(self):
        key = self._needed_values_key()
        merged = self.env["account.move"]._sync_dynamic_line_needed_values(
            [
                {key: {"balance": 10.0, "amount_currency": 10.0}},
                {key: {"balance": -4.0}},
            ]
        )
        self.assertEqual(merged[key]["balance"], 6.0)
        self.assertEqual(merged[key]["amount_currency"], 10.0)

    def test_sync_stack_runs_its_steps_in_list_order(self):
        container = {"records": self.env["account.move"]}
        stack, _update_containers = self.env["account.move"]._get_sync_stack(container)
        self.assertTrue(stack)
        self.assertFalse(
            [step for step in stack if isinstance(step, tuple)],
            "the stack is an ordered list of context managers, not (sequence, cm) pairs",
        )

    def test_sync_tax_lines_snapshots_only_what_it_compares(self):
        module = inspect.getmodule(AccountMove)
        tree = ast.parse(textwrap.dedent(inspect.getsource(module)))
        snapshotted = {
            constant.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and getattr(node.targets[0], "id", None) == "MOVE_TRACKED_FIELDS"
            for constant in ast.walk(node)
            if isinstance(constant, ast.Constant) and isinstance(constant.value, str)
        }
        self.assertTrue(snapshotted, "expected the snapshot to capture something")
        uses = collections.Counter(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )
        unread = sorted({field for field in snapshotted if uses[field] < 2})
        self.assertFalse(
            unread,
            "_sync_tax_lines snapshots %s and never compares them" % unread,
        )

    def test_zero_valued_needed_entries_are_treated_asymmetrically(self):
        key = self._needed_values_key()
        lone_zero = self.env["account.move"]._sync_dynamic_line_needed_values(
            [{key: {"balance": 0.0, "amount_currency": 0.0}}]
        )
        self.assertIn(key, lone_zero, "a single zero contribution is kept")

        cancelling = self.env["account.move"]._sync_dynamic_line_needed_values(
            [
                {key: {"balance": 10.0, "amount_currency": 10.0}},
                {key: {"balance": -10.0, "amount_currency": -10.0}},
            ]
        )
        self.assertNotIn(
            key, cancelling, "two contributions cancelling to zero are dropped"
        )

    def test_a_zero_installment_reaches_the_move_as_a_journal_item(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "0 then 100",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 0.0, "nb_days": 0}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 100.0, "nb_days": 30}
                    ),
                ],
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_payment_term_id": term.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "p",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        payment_terms = invoice.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        zero_rows = payment_terms.filtered(
            lambda line: not line.balance and not line.amount_currency
        )
        self.assertEqual(
            len(zero_rows),
            1,
            "the 0%% installment currently persists as a 0.00 journal item",
        )

    def test_non_deductible_lines_read_a_zero_rate_like_the_line_sync_does(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "x",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "deductible_amount": 50,
                            "tax_ids": [
                                Command.set(
                                    self.company_data["default_tax_purchase"].ids
                                )
                            ],
                        }
                    )
                ],
            }
        )
        bill.invoice_currency_rate = 0.0
        self.assertEqual(bill.invoice_currency_rate, 0.0)
        self.assertEqual(
            set(bill.line_ids.mapped("currency_rate")),
            {1.0},
            "account.move.line reads a zero rate as 1.0",
        )
        for vals in bill._prepare_non_deductible_line_vals(bill):
            self.assertEqual(
                bool(vals["balance"]),
                bool(vals["amount_currency"]),
                "a zero rate must not produce a balance of 0 against a non-zero "
                "amount_currency: the two readers of invoice_currency_rate have to "
                "agree, or the line sync silently repairs what this builds",
            )

    def _plain_invoice(self, price_unit=100.0, **move_vals):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_date_due": "2026-02-01",
                "invoice_payment_term_id": False,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "p",
                            "quantity": 1,
                            "price_unit": price_unit,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
                **move_vals,
            }
        )

    def _payment_term_line(self, move):
        return move.line_ids.filtered(lambda line: line.display_type == "payment_term")

    def test_due_date_change_recycles_the_receivable_line(self):
        invoice = self._plain_invoice()
        line = self._payment_term_line(invoice)
        line.name = "CUSTOMER PO 4711"
        line.analytic_distribution = {str(self._analytic_account().id): 100}
        line_id = line.id

        invoice.invoice_date_due = "2026-06-01"

        line = self._payment_term_line(invoice)
        self.assertEqual(
            line.id,
            line_id,
            "the receivable line carries user data the plan does not: rewriting it "
            "in place is what keeps the label and the analytic distribution",
        )
        self.assertEqual(line.name, "CUSTOMER PO 4711")
        self.assertTrue(line.analytic_distribution)
        self.assertEqual(str(line.date_maturity), "2026-06-01")

    def test_due_date_change_is_allowed_on_a_posted_invoice(self):
        invoice = self._plain_invoice()
        invoice.action_post()
        line_id = self._payment_term_line(invoice).id

        self.assertNotIn(
            "invoice_date_due",
            self.env["account.move"]._UNMODIFIABLE_WHEN_POSTED,
            "the policy this test relies on: the due date stays writable once posted",
        )
        invoice.invoice_date_due = "2026-09-09"

        line = self._payment_term_line(invoice)
        self.assertEqual(line.id, line_id)
        self.assertEqual(str(line.date_maturity), "2026-09-09")

    def test_recycling_never_moves_a_line_between_moves(self):
        term_2 = self.env["account.payment.term"].create(
            {
                "name": "2x",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 50.0, "nb_days": 5}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 50.0, "nb_days": 45}
                    ),
                ],
            }
        )
        term_3 = self.env["account.payment.term"].create(
            {
                "name": "3x",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 30.0, "nb_days": 0}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 30.0, "nb_days": 30}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 40.0, "nb_days": 60}
                    ),
                ],
            }
        )
        moves = self.env["account.move"]
        analytic_by_move = {}
        for price in (100.0, 300.0):
            move = self._plain_invoice(
                price_unit=price, invoice_payment_term_id=term_2.id
            )
            analytic = self._analytic_account("AA %s" % price)
            for line in self._payment_term_line(move):
                line.analytic_distribution = {str(analytic.id): 100}
            analytic_by_move[move] = analytic
            moves |= move

        moves.invoice_payment_term_id = term_3

        for move, analytic in analytic_by_move.items():
            for line in self._payment_term_line(move):
                self.assertFalse(
                    set(line.analytic_distribution or {}) - {str(analytic.id)},
                    "a recycled line paired with another move's key migrates "
                    "between invoices, taking its analytic distribution along, "
                    "and both moves still balance so nothing raises",
                )

    def _analytic_account(self, name="AA"):
        plan = self.env["account.analytic.plan"].search([], limit=1) or self.env[
            "account.analytic.plan"
        ].create({"name": "Plan"})
        return self.env["account.analytic.account"].create(
            {"name": name, "plan_id": plan.id}
        )

    def _foreign_currency(self, rate=2.0):
        currency = self.env.ref("base.EUR")
        if currency == self.env.company.currency_id:
            currency = self.env.ref("base.USD")
        self.env["res.currency.rate"].create(
            {
                "name": "2026-01-01",
                "currency_id": currency.id,
                "rate": rate,
                "company_id": self.env.company.id,
            }
        )
        return currency

    def test_rounding_line_uses_the_rate_its_siblings_use(self):
        currency = self._foreign_currency(rate=2.0)
        invoice = self._rounded_invoice(
            self._cash_rounding("add_invoice_line", rounding=1.0),
            100.40,
            self.env["account.tax"],
        )
        invoice.currency_id = currency
        for override in (None, 5.0):
            with self.subTest(rate=override):
                if override:
                    invoice.invoice_currency_rate = override
                receivable = invoice.line_ids.filtered(
                    lambda line: line.display_type == "payment_term"
                )
                self.assertAlmostEqual(
                    receivable.balance,
                    invoice.company_currency_id.round(
                        invoice.amount_total / invoice.invoice_currency_rate
                    ),
                    places=2,
                    msg="the rounding line converted through the rate table while "
                    "every sibling used invoice_currency_rate, and the receivable "
                    "silently absorbed the difference",
                )

    def test_rounding_line_goes_when_the_new_method_cannot_book_it(self):
        configured = self._cash_rounding("add_invoice_line", rounding=0.05)
        bare = self._cash_rounding(
            "add_invoice_line", rounding=0.05, with_accounts=False
        )
        invoice = self._rounded_invoice(configured, 100.02, self.env["account.tax"])
        self.assertTrue(
            invoice.line_ids.filtered(lambda line: line.display_type == "rounding")
        )

        invoice.invoice_cash_rounding_id = bare
        invoice.invoice_line_ids[0].price_unit = 100.03

        self.assertFalse(
            invoice.line_ids.filtered(lambda line: line.display_type == "rounding"),
            "keeping the previous method's line leaves the invoice balanced around "
            "a total that belongs to neither method",
        )
        self.assertEqual(invoice.amount_total, 100.03)

    def test_a_duplicated_dynamic_line_does_not_break_the_sync(self):
        cases = (
            (
                "rounding",
                lambda: self._rounded_invoice(
                    self._cash_rounding("add_invoice_line", rounding=0.05),
                    100.02,
                    self.env["account.tax"],
                ),
            ),
            ("balancing", lambda: self._unbalanced_entry(self.env, "first")),
        )
        for display_type, build in cases:
            with self.subTest(display_type=display_type):
                move = build()
                line = move.line_ids.filtered(
                    lambda line, dt=display_type: line.display_type == dt
                )
                self.assertTrue(line, "fixture must produce a %s line" % display_type)
                line.copy({"move_id": move.id})
                self.env.flush_all()
                self.assertEqual(
                    len(
                        move.line_ids.filtered(
                            lambda line, dt=display_type: line.display_type == dt
                        )
                    ),
                    1,
                    "a second %s line is representable, and every reader of it "
                    "reaches for a scalar field -- the sync has to converge on one "
                    "rather than raise Expected singleton from inside a create"
                    % display_type,
                )
                self.assertAlmostEqual(
                    sum(move.line_ids.mapped("balance")), 0.0, places=2
                )

    def test_deductibility_just_under_100_builds_no_orphan_total(self):
        for deductible, expected in ((99.999, 0), (99.99, 2)):
            with self.subTest(deductible=deductible):
                bill = self.env["account.move"].create(
                    {
                        "move_type": "in_invoice",
                        "partner_id": self.partner_a.id,
                        "invoice_date": "2026-01-01",
                        "invoice_line_ids": [
                            Command.create(
                                {
                                    "name": "x",
                                    "quantity": 1,
                                    "price_unit": 100.0,
                                    "deductible_amount": deductible,
                                    "tax_ids": [Command.clear()],
                                }
                            )
                        ],
                    }
                )
                lines = bill.line_ids.filtered(
                    lambda line: (
                        line.display_type
                        in ("non_deductible_product", "non_deductible_product_total")
                    )
                )
                self.assertEqual(
                    len(lines),
                    expected,
                    "the gate and the vals builder must read deductible_amount the "
                    "same way, or one alone emits a 0.00 total with no counterpart",
                )

    def test_changing_the_journal_repoints_the_private_part(self):
        first = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        account_a = self.company_data["default_account_expense"].copy()
        account_b = self.company_data["default_account_expense"].copy()
        first.non_deductible_account_id = account_a
        second = first.copy({"name": "Purchases B", "code": "PURB"})
        second.non_deductible_account_id = account_b

        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "journal_id": first.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "x",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "deductible_amount": 50,
                            "tax_ids": [
                                Command.set(
                                    self.company_data["default_tax_purchase"].ids
                                )
                            ],
                        }
                    )
                ],
            }
        )
        bill.journal_id = second

        for display_type in ("non_deductible_product_total", "non_deductible_tax"):
            line = bill.line_ids.filtered(
                lambda line, dt=display_type: line.display_type == dt
            )
            self.assertEqual(
                line.account_id,
                account_b,
                "%s stayed on the previous journal's non-deductible account"
                % display_type,
            )

    def test_merged_needed_values_do_not_alias_the_source(self):
        key = self._needed_values_key()
        tax_ids = [Command.set([1, 2])]
        source = {key: {"balance": 1.0, "amount_currency": 1.0, "tax_ids": tax_ids}}
        merged = self.env["account.move"]._sync_dynamic_line_needed_values([source])
        self.assertIsNot(
            merged[key]["tax_ids"],
            tax_ids,
            "the merged values are handed to callers while the source is the ORM "
            "cache entry for epd_needed / discount_allocation_needed",
        )
