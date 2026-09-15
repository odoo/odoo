import ast
import collections
import inspect
import textwrap
from datetime import date, timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tools import SQL

from odoo.addons.account.models.account_move_line import AccountMoveLine
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tools.display_types import (
    NON_ACCOUNTABLE_DISPLAY_TYPES,
)
from odoo.addons.account.tools.reconciliation import prepare_partial_amounts


@tagged("post_install", "-at_install")
class TestMarinAccountMoveLineFixes(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Regression Plan"}
        )
        cls.aa_1, cls.aa_2 = cls.env["account.analytic.account"].create(
            [
                {"name": "AA 60", "plan_id": cls.analytic_plan.id},
                {"name": "AA 40", "plan_id": cls.analytic_plan.id},
            ]
        )

    def test_discount_allocation_analytic_distribution_is_weighted(self):
        discount_account = self.company_data["default_account_expense"].copy()
        self.company_data[
            "company"
        ].account_discount_expense_allocation_id = discount_account

        distribution = {str(self.aa_1.id): 60.0, str(self.aa_2.id): 40.0}
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "discount": 5,
                            "analytic_distribution": distribution,
                        }
                    ),
                ],
            }
        )

        discount_lines = invoice.line_ids.filtered(
            lambda l: l.display_type == "discount"
        )
        self.assertTrue(discount_lines, "discount allocation lines should be generated")
        for line in discount_lines:
            self.assertEqual(
                {k: round(v, 2) for k, v in (line.analytic_distribution or {}).items()},
                distribution,
                "discount line analytic distribution must be weighted 60/40, not 50/50",
            )

    def test_term_key_recomputes_on_discount_date_change(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            products=self.product_a,
            post=False,
        )
        term_line = invoice.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        term_line.check_singleton()

        before = term_line.term_key
        term_line.discount_date = "2099-01-01"
        after = term_line.term_key

        self.assertNotEqual(
            before, after, "term_key must refresh when discount_date changes"
        )
        self.assertEqual(after["discount_date"], term_line.discount_date)

    def test_hash_guard_covers_balance(self):
        self.company_data["default_journal_sale"].restrict_mode_hash_table = True
        move = self.init_invoice(
            "out_invoice", self.partner_a, "2023-01-01", amounts=[1000.0], post=True
        )
        self.assertTrue(move.inalterable_hash)
        product_line = move.line_ids.filtered(lambda l: l.display_type == "product")

        with self.assertRaises(UserError):
            product_line.write({"balance": product_line.balance + 10.0})
        with self.assertRaises(UserError):
            product_line.write({"debit": product_line.debit + 10.0})

        move.invalidate_recordset()
        results = move.company_id._check_hash_integrity()["results"]
        self.assertFalse(
            any("corrupted" in (r.get("msg_cover") or "").lower() for r in results)
        )

        move.write({"ref": "still editable"})
        product_line.write({"name": product_line.name})

    def test_hash_guard_allows_balance_on_unhashed_move(self):
        move = self.init_invoice(
            "out_invoice", self.partner_a, "2023-01-01", amounts=[1000.0], post=False
        )
        self.assertFalse(move.inalterable_hash)
        product_line = move.line_ids.filtered(lambda l: l.display_type == "product")
        product_line.write({"balance": product_line.balance - 5.0})

    def test_parent_id_not_stale_on_sequence_change(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {"display_type": "line_section", "name": "SEC", "sequence": 5}
                    ),
                    Command.create(
                        {"name": "p", "quantity": 1, "price_unit": 10, "sequence": 10}
                    ),
                ],
            }
        )
        product_line = move.line_ids.filtered(lambda l: l.display_type == "product")
        section = move.line_ids.filtered(lambda l: l.display_type == "line_section")
        self.assertEqual(product_line.parent_id, section)

        section.write({"sequence": 20})
        self.assertFalse(
            product_line.parent_id,
            "parent_id must recompute automatically once the section moves after it",
        )

    def test_deductible_amount_boundary_tolerance(self):
        move = self.init_invoice(
            "in_invoice", self.partner_a, "2023-01-01", amounts=[100.0], post=False
        )
        product_line = move.line_ids.filtered(lambda l: l.display_type == "product")[:1]
        product_line.deductible_amount = 100.000001
        product_line.deductible_amount = 0.0
        product_line.deductible_amount = 100.0
        with self.assertRaises(ValidationError):
            product_line.deductible_amount = 100.01
        with self.assertRaises(ValidationError):
            product_line.deductible_amount = -0.01

    def test_payment_date_timezone_consistency(self):
        AML = self.env["account.move.line"]
        recv = self.company_data["default_account_receivable"]
        misc = self.company_data["default_account_revenue"]
        journal = self.company_data["default_journal_misc"]
        d_disc = date(2026, 7, 7)
        d_mat = date(2026, 7, 10)
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": date(2026, 7, 1),
                "line_ids": [
                    Command.create(
                        {
                            "account_id": recv.id,
                            "balance": 100.0,
                            "date_maturity": d_mat,
                        }
                    ),
                    Command.create({"account_id": misc.id, "balance": -100.0}),
                ],
            }
        )
        line = move.line_ids.filtered(lambda l: l.account_id == recv)
        line.discount_date = d_disc
        self.env.flush_all()

        with freeze_time("2026-07-08 03:00:00"):
            line_tz = line.with_context(tz="Pacific/Midway")
            aml_tz = AML.with_context(tz="Pacific/Midway")

            line_tz.invalidate_recordset(["payment_date"])
            py_val = line_tz.payment_date

            sql = aml_tz._field_to_sql("account_move_line", "payment_date")
            self.env.cr.execute(
                SQL("SELECT %s FROM account_move_line WHERE id = %s", sql, line.id)
            )
            sql_val = self.env.cr.fetchone()[0]

            self.assertEqual(
                py_val, d_disc, "compute must use user-tz today (discount_date valid)"
            )
            self.assertEqual(sql_val, d_disc, "SQL must use the same user-tz today")
            self.assertEqual(py_val, sql_val, "compute and SQL sort value must agree")

            found = aml_tz.search([("id", "=", line.id), ("payment_date", "=", d_disc)])
            self.assertIn(
                line, found, "search filter must agree with the computed payment_date"
            )

    def test_payment_date_equality_means_due_by(self):
        journal = self.company_data["default_journal_misc"]
        debit_account = self.company_data["default_account_expense"]
        credit_account = self.company_data["default_account_revenue"]
        today = fields.Date.context_today(self.env["account.move.line"])

        def line_due(days):
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": "2026-01-01",
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": debit_account.id,
                                "balance": 10.0,
                                "name": "d",
                                "date_maturity": today + timedelta(days=days),
                            }
                        ),
                        Command.create(
                            {
                                "account_id": credit_account.id,
                                "balance": -10.0,
                                "name": "c",
                            }
                        ),
                    ],
                }
            )
            return move.line_ids.filtered(lambda l: l.account_id == debit_account)

        early, on_target, late = line_due(-30), line_due(10), line_due(40)
        pool = early + on_target + late
        target = today + timedelta(days=10)

        def search(operator):
            return self.env["account.move.line"].search(
                [("id", "in", pool.ids), ("payment_date", operator, target)]
            )

        self.assertEqual(
            search("="),
            early + on_target,
            "'=' on payment_date means due BY the date, so it includes earlier lines",
        )
        self.assertEqual(
            search("!="),
            late,
            "'!=' is the complement of that, so it means due AFTER the date -- it "
            "does NOT mean 'payment date is not this date', and the earlier line "
            "is deliberately absent",
        )
        self.assertNotEqual(
            search("!="),
            pool.filtered(lambda line: line.payment_date != target),
            "the domain and the Python attribute disagree here on purpose; if this "
            "ever starts holding, the remap above was removed and the comment on "
            "_search_payment_date is stale",
        )

    def test_name_retranslates_on_partner_language_change(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        partner_en = self.env["res.partner"].create(
            {"name": "EN partner", "lang": "en_US"}
        )
        partner_fr = self.env["res.partner"].create(
            {"name": "FR partner", "lang": "fr_FR"}
        )
        product = self.env["product.product"].create(
            {"name": "Gadget", "type": "consu"}
        )
        product.description_sale = "English description"
        product.with_context(lang="fr_FR").description_sale = "Description francaise"

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = partner_en
        with move_form.invoice_line_ids.new() as line:
            line.product_id = product
        invoice = move_form.save()
        product_line = invoice.line_ids.filtered(lambda l: l.display_type == "product")
        self.assertIn("English description", product_line.name)

        with Form(invoice) as invoice_form:
            invoice_form.partner_id = partner_fr

        self.assertIn(
            "Description francaise",
            product_line.name,
            "line label must re-translate when the partner language changes",
        )
        self.assertNotIn("English description", product_line.name)

    def test_line_compute_depends_completeness(self):
        def deps(fname):
            field = self.env["account.move.line"]._fields[fname]
            return " ".join(self.env.registry.field_depends.get(field, ()))

        self.assertIn("display_type", deps("currency_id"))
        self.assertIn("company_id", deps("currency_id"))
        self.assertIn("partner_id", deps("translated_product_name"))
        self.assertIn("reversed_entry_id", deps("is_refund"))
        parent_field = self.env["account.move.line"]._fields["parent_id"]
        self.assertTrue(
            self.env.registry.field_depends.get(parent_field),
            "parent_id must declare dependencies",
        )

    def test_every_computed_line_field_declares_dependencies(self):
        deliberately_undeclared = {
            "account_id",
            "partner_id",
            "move_attachment_ids",
        }
        model = self.env["account.move.line"]
        undeclared = {
            name
            for name, field in model._fields.items()
            if field.compute
            and not field.related
            and not self.env.registry.field_depends.get(field)
            and not [
                key
                for key in self.env.registry.field_depends_context.get(field, ())
                if key != "access"
            ]
        }
        self.assertFalse(
            undeclared - deliberately_undeclared,
            "a computed field with no @api.depends and no @api.depends_context is "
            "never invalidated; add the dependency, or add the field here with the "
            "reason it does not need one",
        )
        self.assertFalse(
            (deliberately_undeclared & set(model._fields)) - undeclared,
            "this exemption is no longer needed: the field declares a dependency "
            "now, so drop it from the list rather than leave a stale licence",
        )

    def test_discount_allocation_follows_a_discount_change(self):
        discount_account = self.company_data["default_account_expense"].copy()
        self.company_data[
            "company"
        ].account_discount_expense_allocation_id = discount_account
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "discount": 10.0,
                        }
                    ),
                ],
            }
        )
        product_line = invoice.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        )

        def allocated():
            return sorted(
                invoice.line_ids.filtered(
                    lambda l: l.display_type == "discount"
                ).mapped("balance")
            )

        self.assertEqual(allocated(), [-10.0, 10.0])
        product_line.discount = 40.0
        self.assertEqual(
            allocated(),
            [-40.0, 40.0],
            "the discount allocation lines must follow the discount they book",
        )
        product_line.discount = 25.0
        self.assertEqual(allocated(), [-25.0, 25.0])
        self.env.invalidate_all()
        self.assertEqual(
            allocated(),
            [-25.0, 25.0],
            "and the stored lines, not merely the cache, must carry the new amount",
        )

    def test_price_subtotal_follows_amount_currency_on_an_entry(self):
        journal = self.company_data["default_journal_misc"]
        debit_account = self.company_data["default_account_expense"]
        credit_account = self.company_data["default_account_revenue"]
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": "2026-01-01",
                "line_ids": [
                    Command.create(
                        {"account_id": debit_account.id, "balance": 100.0, "name": "d"}
                    ),
                    Command.create(
                        {
                            "account_id": credit_account.id,
                            "balance": -100.0,
                            "name": "c",
                        }
                    ),
                ],
            }
        )
        debit_line, credit_line = entry.line_ids
        self.assertEqual(debit_line.price_subtotal, 100.0)

        entry.write(
            {
                "line_ids": [
                    Command.update(
                        debit_line.id, {"balance": 250.0, "amount_currency": 250.0}
                    ),
                    Command.update(
                        credit_line.id, {"balance": -250.0, "amount_currency": -250.0}
                    ),
                ]
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            debit_line.price_subtotal,
            250.0,
            "price_subtotal must follow amount_currency on a non-invoice move",
        )

    def test_exchange_move_is_linked_to_the_partial_that_produced_it(self):
        company = self.company_data["company"]
        currency = self.setup_other_currency(
            "EUR", rates=[("2024-01-01", 2.0), ("2024-06-01", 4.0)]
        )
        journal = self.company_data["default_journal_misc"]
        company.currency_exchange_journal_id = journal
        account = self.company_data["default_account_receivable"]
        account.reconcile = True
        counterpart = self.company_data["default_account_expense"]

        def entry(entry_date, amount_currency, rate):
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": entry_date,
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": account.id,
                                "partner_id": self.partner_a.id,
                                "currency_id": currency.id,
                                "amount_currency": amount_currency,
                                "balance": amount_currency / rate,
                            }
                        ),
                        Command.create(
                            {
                                "account_id": counterpart.id,
                                "partner_id": self.partner_a.id,
                                "currency_id": currency.id,
                                "amount_currency": -amount_currency,
                                "balance": -amount_currency / rate,
                            }
                        ),
                    ],
                }
            )
            move.action_post()
            return move.line_ids.filtered(lambda line: line.account_id == account)

        debit = entry("2024-01-15", 600.0, 2.0)
        credit_same_rate = entry("2024-02-15", -300.0, 2.0)
        credit_other_rate = entry("2024-07-15", -300.0, 4.0)

        amls = debit + credit_same_rate + credit_other_rate
        amls._reconcile_plan([amls])

        partial_same_rate = debit.matched_credit_ids.filtered(
            lambda partial: partial.credit_move_id == credit_same_rate
        )
        partial_other_rate = debit.matched_credit_ids.filtered(
            lambda partial: partial.credit_move_id == credit_other_rate
        )
        self.assertTrue(partial_same_rate and partial_other_rate)
        self.assertFalse(
            partial_same_rate.exchange_move_id,
            "the same-rate match produced no exchange difference and must own none",
        )
        self.assertTrue(
            partial_other_rate.exchange_move_id,
            "the exchange difference belongs to the match that generated it",
        )

        exchange_move = partial_other_rate.exchange_move_id
        partial_same_rate.unlink()
        self.assertFalse(
            self.env["account.move"].search_count(
                [("reversed_entry_id", "=", exchange_move.id)]
            ),
            "undoing an unrelated match must not reverse this exchange difference",
        )
        self.assertEqual(
            debit.amount_residual_currency,
            300.0,
            "600 - 300 still open in the foreign currency",
        )
        self.assertEqual(
            debit.amount_residual,
            150.0,
            "300 - 75 (the surviving match) - 75 (its exchange difference)",
        )

    def test_default_read_field_set_is_resolved_per_user(self):
        group_xmlid = "analytic.group_analytic_accounting"
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        restricted_fname = next(
            (
                fname
                for fname, field in self.env["account.move.line"]._fields.items()
                if field.groups == group_xmlid
            ),
            None,
        )
        if not (group and restricted_fname):
            self.skipTest(
                "no field restricted to %s on account.move.line here" % group_xmlid
            )

        base = self.env.ref("base.group_user")
        privileged, plain = self.env["res.users"].create(
            [
                {
                    "name": "Privileged",
                    "login": "aml_privileged",
                    "group_ids": [Command.set([base.id, group.id])],
                },
                {
                    "name": "Plain",
                    "login": "aml_plain",
                    "group_ids": [Command.set([base.id])],
                },
            ]
        )
        AML = self.env["account.move.line"]
        for warmer, other in ((privileged, plain), (plain, privileged)):
            self.env.registry.clear_cache()
            AML.with_user(warmer)._get_fields_default_read()
            self.assertEqual(
                restricted_fname in AML.with_user(other)._get_fields_default_read(),
                other == privileged,
                "the field set must follow the reader, not whoever warmed the cache",
            )

    def test_technical_fields_stay_out_of_read_for_every_spelling_of_all(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "balance": balance,
                        }
                    )
                    for balance in (100.0, -100.0)
                ],
            }
        )
        for record in (move, move.line_ids[0]):
            technical = {
                fname
                for fname, field in record._fields.items()
                if not record._is_readable_by_default(field)
            }
            self.assertTrue(
                technical, "%s must exclude something to test" % record._name
            )
            for fields_arg in (None, []):
                self.assertFalse(
                    set(record.read(fields_arg)[0]) & technical,
                    "%s.read(%r) resolved %s"
                    % (record._name, fields_arg, sorted(technical)),
                )

    def test_sibling_of_an_excluded_compute_is_excluded_too(self):
        AML = self.env["account.move.line"]
        for compute in (
            "_compute_epd",
            "_compute_discount_allocation",
        ):
            written = [
                fname
                for fname, field in AML._fields.items()
                if field.compute == compute
            ]
            self.assertGreater(len(written), 1, "expected a multi-field compute")
            resolved = [
                f for f in written if AML._is_readable_by_default(AML._fields[f])
            ]
            self.assertFalse(
                resolved,
                "%s is skipped by default, but %s would still trigger it"
                % (compute, resolved),
            )

    def _parse_method_source(self, method):
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
        except SyntaxError:
            tree = None
        node = tree.body[0] if tree and tree.body else None
        if not isinstance(node, ast.FunctionDef) or node.name != method.__name__:
            self.fail(
                "inspect.getsource did not return the body of %s; the module on "
                "disk has moved under the imported code object, which happens when "
                "another session edits account_move_line.py mid-run" % method.__name__
            )
        return tree, node

    def test_tax_ids_skip_list_derives_from_the_display_type_tuple(self):
        tree, definition = self._parse_method_source(AccountMoveLine._compute_tax_ids)
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        docstring = ast.get_docstring(definition) or ""
        literals.discard(docstring)
        restated = literals & set(NON_ACCOUNTABLE_DISPLAY_TYPES)
        self.assertFalse(
            restated,
            "derive the skip list from NON_ACCOUNTABLE_DISPLAY_TYPES instead of "
            "restating %s" % sorted(restated),
        )

    def test_one_full_reconcile_per_batch_across_overlapping_plans(self):
        account = self.company_data["default_account_receivable"]
        account.reconcile = True
        journal = self.company_data["default_journal_misc"]
        counterpart = self.company_data["default_account_expense"]

        def entry(balance):
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": "2024-01-01",
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": account.id,
                                "partner_id": self.partner_a.id,
                                "balance": balance,
                            }
                        ),
                        Command.create(
                            {
                                "account_id": counterpart.id,
                                "partner_id": self.partner_a.id,
                                "balance": -balance,
                            }
                        ),
                    ],
                }
            )
            move.action_post()
            return move.line_ids.filtered(lambda line: line.account_id == account)

        invoice_line = entry(90.0)
        credits = entry(-30.0) + entry(-30.0) + entry(-30.0)

        FullReconcile = self.env["account.full.reconcile"]
        before = FullReconcile.search_count([])
        self.env["account.move.line"]._reconcile_plan(
            [invoice_line + credit for credit in credits]
        )
        created = FullReconcile.search_count([]) - before

        involved = invoice_line + credits
        self.assertTrue(all(involved.mapped("reconciled")))
        self.assertEqual(
            len(involved.full_reconcile_id),
            1,
            "all four lines belong to one full reconciliation",
        )
        self.assertEqual(
            created,
            1,
            "one batch, one account.full.reconcile -- surplus batches leave orphans",
        )

    def test_partial_amounts_at_par_clamps_to_what_is_left(self):
        company_currency = self.company_data["currency"]
        foreign = self.setup_other_currency("EUR", rates=[("2024-01-01", 0.5)])
        context = {
            "recon_currency": company_currency,
            "company_currency": company_currency,
            "debit_currency": foreign,
            "credit_currency": foreign,
            "exchange_line_mode": False,
            "min_recon_amount": 100.0,
            "debit_available": {foreign: {"rate": 0.5}},
            "credit_available": {foreign: {"rate": 0.5}},
            "remaining_debit_amount_curr": 40.0,
            "remaining_credit_amount_curr": -1000.0,
        }
        partials = prepare_partial_amounts(context)
        self.assertEqual(partials["partial_amount"], 100.0)
        self.assertEqual(
            partials["partial_debit_amount_currency"],
            40.0,
            "0.5 * 100 is 50, but only 40 is left on the debit side",
        )
        self.assertEqual(
            partials["partial_credit_amount_currency"],
            50.0,
            "the credit side has room, so the rate result stands",
        )

    def test_partial_amounts_at_par_ignores_rates_in_exchange_line_mode(self):
        company_currency = self.company_data["currency"]
        foreign = self.setup_other_currency("EUR", rates=[("2024-01-01", 0.5)])
        context = {
            "recon_currency": company_currency,
            "company_currency": company_currency,
            "debit_currency": foreign,
            "credit_currency": foreign,
            "exchange_line_mode": True,
            "min_recon_amount": 100.0,
            "debit_available": {foreign: {"rate": 0.5}},
            "credit_available": {foreign: {"rate": 0.5}},
            "remaining_debit_amount_curr": 1000.0,
            "remaining_credit_amount_curr": -1000.0,
        }
        partials = prepare_partial_amounts(context)
        self.assertEqual(partials["partial_amount"], 100.0)
        self.assertEqual(partials["partial_debit_amount_currency"], 0.0)
        self.assertEqual(partials["partial_credit_amount_currency"], 0.0)

    def test_reconciling_a_shape_and_its_mirror_agree(self):
        company = self.company_data["company"]
        currency = self.setup_other_currency("EUR", rates=[("2024-01-01", 0.8)])
        journal = self.company_data["default_journal_misc"]
        company.currency_exchange_journal_id = journal
        account = self.company_data["default_account_receivable"]
        account.reconcile = True
        counterpart = self.company_data["default_account_expense"]

        def line(amount_currency, balance, day):
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": "2024-01-%s" % day,
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": account.id,
                                "partner_id": self.partner_a.id,
                                "currency_id": currency.id,
                                "amount_currency": amount_currency,
                                "balance": balance,
                            }
                        ),
                        Command.create(
                            {
                                "account_id": counterpart.id,
                                "partner_id": self.partner_a.id,
                                "currency_id": currency.id,
                                "amount_currency": -amount_currency,
                                "balance": -balance,
                            }
                        ),
                    ],
                }
            )
            move.action_post()
            return move.line_ids.filtered(lambda x: x.account_id == account)

        def reconcile(sign):
            amls = (
                line(0.0, sign * 100.0, "10")
                + line(sign * -80.0, sign * -100.0, "11")
                + line(sign * 50.0, sign * 62.5, "12")
            )
            amls._reconcile_plan([amls])
            amls.invalidate_recordset()
            partials = amls.matched_debit_ids | amls.matched_credit_ids
            return (
                len(partials),
                sorted(round(sign * x.amount_residual, 2) for x in amls),
                sorted(round(sign * x.amount_residual_currency, 2) for x in amls),
            )

        self.assertEqual(
            reconcile(1),
            reconcile(-1),
            "the same reconciliation mirrored must give the same answer mirrored",
        )

    def test_sync_invoice_snapshots_only_what_it_compares(self):
        tree, _definition = self._parse_method_source(AccountMoveLine._sync_invoice)
        snapshot = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "existing"
        )
        keys = [
            key.value
            for dict_node in ast.walk(snapshot)
            if isinstance(dict_node, ast.Dict)
            for key in dict_node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        ]
        self.assertTrue(keys, "expected the snapshot to capture something")
        uses = collections.Counter(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )
        unread = sorted({key for key in keys if uses[key] < 2})
        self.assertFalse(
            unread,
            "_sync_invoice snapshots %s and never compares them" % unread,
        )
