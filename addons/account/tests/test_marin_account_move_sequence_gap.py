import psycopg

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMarinAccountMoveSequenceGap(AccountTestInvoicingCommon):
    def _deps(self, fname):
        field = self.env["account.move"]._fields[fname]
        return tuple(self.env.registry.field_depends.get(field, ()))

    def _invoice(self, journal=None, nlines=1):
        vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2024-03-05",
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(self.tax_sale_a.ids)],
                    }
                )
                for _i in range(nlines)
            ],
        }
        if journal:
            vals["journal_id"] = journal.id
        return self.env["account.move"].create(vals)

    def test_sequence_mixin_cache_key_is_per_move_not_per_batch(self):
        journal_a = self.company_data["default_journal_sale"]
        journal_b = journal_a.copy({"name": "Second Sale", "code": "SSAL2"})
        moves = self._invoice(journal_a) | self._invoice(journal_b)
        moves.action_post()

        cache = moves._get_sequence_cache()
        self.assertTrue(cache, "the mixin must have cached the assigned sequences")
        self.assertGreater(
            len(moves.journal_id), 1, "the batch must span more than one journal"
        )
        for move in moves:
            self.assertTrue(
                moves._is_sequence_computed_with_mixin(move, cache),
                "a move numbered by the mixin must be recognised even when the "
                "recordset it is judged in spans several journals",
            )

    def test_multi_journal_post_raises_no_spurious_sequence_gap(self):
        journal_a = self.company_data["default_journal_sale"]
        journal_b = journal_a.copy({"name": "Third Sale", "code": "SSAL3"})
        moves = self.env["account.move"]
        for _i in range(3):
            moves |= self._invoice(journal_a)
            moves |= self._invoice(journal_b)
        moves.action_post()
        moves._update_sequence_made_gap()

        self.assertFalse(
            any(moves.mapped("made_sequence_gap")),
            "a contiguous multi-journal batch must not be flagged as holding gaps",
        )

    def test_amounts_depend_on_every_line_field_the_compute_reads(self):
        deps = self._deps("amount_untaxed")
        self.assertIn("line_ids.display_type", deps)
        self.assertIn("line_ids.tax_repartition_line_id", deps)

    def test_tax_totals_declaration_stays_narrow_on_purpose(self):
        deps = self._deps("tax_totals")
        self.assertNotIn("invoice_currency_rate", deps)
        self.assertIn("invoice_line_ids.price_subtotal", deps)

    def test_tax_lock_date_message_declares_each_trigger_once(self):
        deps = self._deps("tax_lock_date_message")
        duplicated = [d for d in deps if d.startswith("invoice_line_ids.")]
        self.assertFalse(
            duplicated,
            f"these duplicate the line_ids.* triggers already declared: {duplicated}",
        )

    def test_suitable_journal_ids_declares_only_what_it_reads(self):
        deps = self._deps("suitable_journal_ids")
        self.assertNotIn("invoice_filter_type_domain", deps)
        self.assertIn("move_type", deps)
        self.assertIn("company_id", deps)

    def test_suitable_journal_ids_is_searched_once_per_distinct_key(self):
        moves = self.env["account.move"]
        for _i in range(6):
            moves |= self._invoice()
        moves.invalidate_recordset(["suitable_journal_ids"])
        self.env.flush_all()

        searches = []
        Journal = type(self.env["account.journal"])
        original = Journal.search

        def counting(journal_self, *args, **kwargs):
            searches.append(1)
            return original(journal_self, *args, **kwargs)

        self.patch(Journal, "search", counting)
        moves.mapped("suitable_journal_ids")

        self.assertEqual(
            len(searches),
            1,
            "the journal search must be issued once per distinct "
            "(move_type, company_id), not once per move",
        )
        self.assertTrue(all(moves.mapped("suitable_journal_ids")))

    def test_invoice_line_ids_is_not_a_subset_of_line_ids_before_save(self):
        draft = self.env["account.move"].new(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": self.product_a.id, "price_unit": 100.0}
                    )
                ],
            }
        )
        self.assertTrue(draft.invoice_line_ids)
        self.assertFalse(
            draft.invoice_line_ids <= draft.line_ids,
            "if this ever becomes True the guard in _inverse_partner_id can be "
            "simplified; until then line_ids alone would iterate nothing",
        )

    def test_partner_change_propagates_to_lines_before_save(self):
        move = self.env["account.move"].new(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": self.product_a.id, "price_unit": 100.0}
                    )
                ],
            }
        )
        move.partner_id = self.partner_b
        move._inverse_partner_id()
        self.assertEqual(
            move.invoice_line_ids.partner_id,
            self.partner_b.commercial_partner_id,
            "line partners must follow the invoice partner in the form",
        )

    def test_next_installment_values_are_keyed(self):
        move = self._invoice()
        move.action_post()
        values = move._prepare_next_installment_values(
            move.line_ids.filtered(
                lambda line: line.display_type == "payment_term"
            )._prepare_installments_data()
        )
        self.assertEqual(
            set(values),
            {
                "installment_state",
                "amount_due",
                "next_amount_to_pay",
                "next_payment_reference",
                "next_due_date",
                "additional_info",
            },
        )

    def test_invoice_next_payment_values_still_exposes_its_contract(self):
        move = self._invoice()
        move.action_post()
        values = move._prepare_invoice_next_payment_values()
        for key in (
            "payment_state",
            "installment_state",
            "next_amount_to_pay",
            "next_payment_reference",
            "amount_paid",
            "amount_due",
            "next_due_date",
            "due_date",
            "not_reconciled_installments",
            "is_last_installment",
        ):
            self.assertIn(key, values)
        self.assertNotIn("additional_info", values)

    def test_made_gaps_index_covers_the_dashboard_query(self):
        self.env.cr.execute(
            """
            SELECT indexdef FROM pg_indexes
             WHERE tablename = 'account_move' AND indexname = 'account_move_made_gaps'
            """
        )
        row = self.env.cr.fetchone()
        self.assertTrue(row, "the partial index must exist")
        indexdef = row[0]
        for column in ("journal_id", "company_id", "date", "sequence_prefix"):
            self.assertIn(
                column,
                indexdef,
                "the index must carry every column the journal dashboard's hole "
                f"count filters or groups by; {column} is missing",
            )

    def test_autopost_batch_reraises_a_retryable_database_error(self):
        move = self._invoice()
        move.write({"auto_post": "at_date", "invoice_date": "2024-01-01"})
        move.date = "2024-01-01"

        calls = []
        AccountMove = type(self.env["account.move"])
        self.patch(
            type(self.env["ir.cron"]),
            "_commit_progress",
            lambda records, *a, **kw: None,
        )

        def exploding_post(records, soft=True):
            calls.append(len(records))
            raise psycopg.errors.SerializationFailure("simulated contention")

        self.patch(AccountMove, "_post", exploding_post)
        with self.assertRaises(psycopg.errors.SerializationFailure):
            self.env["account.move"]._autopost_draft_entries()

        self.assertEqual(
            len(calls),
            1,
            "the batch attempt must propagate, not fall through to the per-move "
            f"loop; _post was entered {len(calls)} times",
        )
