from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.tools.reconciliation import (
    group_lines_by_matching_number,
)

_debug = DebugLog(__name__)


def _get_partial_company(partial):
    if partial.debit_move_id.move_id.is_invoice(include_receipts=True):
        return partial.debit_move_id.company_id
    return partial.credit_move_id.company_id


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Reconcile"

    debit_move_id = fields.Many2one(
        comodel_name="account.move.line",
        index=True,
        required=True,
    )
    credit_move_id = fields.Many2one(
        comodel_name="account.move.line",
        index=True,
        required=True,
    )
    full_reconcile_id = fields.Many2one(
        comodel_name="account.full.reconcile",
        index="btree_not_null",
        copy=False,
    )
    exchange_move_id = fields.Many2one(
        comodel_name="account.move",
        index="btree_not_null",
    )

    draft_caba_move_vals = fields.Json(
        string="Values that created the draft cash-basis entry"
    )

    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        help="Utility field to express amount currency",
    )
    debit_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="debit_move_id.currency_id",
        string="Currency of the debit journal item.",
    )
    credit_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="credit_move_id.currency_id",
        string="Currency of the credit journal item.",
    )

    amount = fields.Monetary(
        currency_field="company_currency_id",
        required=True,
        help="Non-negative amount concerned by this matching expressed in the company currency.",
    )
    debit_amount_currency = fields.Monetary(
        currency_field="debit_currency_id",
        required=True,
        help="Non-negative amount concerned by this matching expressed in the debit line foreign currency.",
    )
    credit_amount_currency = fields.Monetary(
        currency_field="credit_currency_id",
        required=True,
        help="Non-negative amount concerned by this matching expressed in the credit line foreign currency.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        precompute=True,
        store=True,
    )
    max_date = fields.Date(
        string="Max Date of Matched Lines",
        compute="_compute_max_date",
        precompute=True,
        store=True,
    )

    _check_distinct_move_lines = models.Constraint(
        "CHECK(debit_move_id != credit_move_id)",
        "A journal item cannot be reconciled with itself.",
    )
    _check_nonnegative_amounts = models.Constraint(
        """CHECK(
            amount >= 0 AND amount < 'Infinity'
            AND debit_amount_currency >= 0 AND debit_amount_currency < 'Infinity'
            AND credit_amount_currency >= 0 AND credit_amount_currency < 'Infinity'
        )""",
        "Partial reconciliation amounts must be finite and non-negative.",
    )
    _check_nonzero_amount = models.Constraint(
        "CHECK(amount > 0 OR debit_amount_currency > 0 OR credit_amount_currency > 0)",
        "A partial reconciliation must reconcile a non-zero amount.",
    )

    @api.constrains("debit_currency_id", "credit_currency_id")
    @_debug.perf.timed
    def _check_required_computed_currencies(self):
        bad_partials = self.filtered(
            lambda partial: (
                not partial.debit_currency_id or not partial.credit_currency_id
            )
        )
        if bad_partials:
            raise ValidationError(
                _(
                    "Missing foreign currencies on partials having ids: %s",
                    bad_partials.ids,
                )
            )

    @api.constrains("debit_move_id", "credit_move_id", "company_id")
    @_debug.perf.timed
    def _check_company_consistency(self):
        bad_partials = self.filtered(
            lambda partial: (
                partial.debit_move_id.company_id.root_id
                != partial.credit_move_id.company_id.root_id
                or partial.company_id != _get_partial_company(partial)
            )
        )
        if bad_partials:
            raise ValidationError(
                _(
                    "Partial reconciliations must belong to the same company hierarchy and use the invoice-side company."
                )
            )

    @api.constrains("debit_move_id", "credit_move_id")
    @_debug.perf.timed
    def _check_move_line_consistency(self):
        def points(line, currency, sign):
            return (
                line.company_currency_id.compare_amounts(line.balance, 0.0) == sign
                or currency.compare_amounts(line.amount_currency, 0.0) == sign
            )

        bad_partials = self.filtered(
            lambda partial: (
                partial.debit_move_id.account_id != partial.credit_move_id.account_id
                or not points(partial.debit_move_id, partial.debit_currency_id, 1)
                or not points(partial.credit_move_id, partial.credit_currency_id, -1)
            )
        )
        if bad_partials:
            raise ValidationError(
                _(
                    "Partial reconciliations require journal items on the same account, with a positive debit direction and a negative credit direction."
                )
            )

    @api.depends("debit_move_id.date", "credit_move_id.date")
    def _compute_max_date(self):
        for partial in self:
            partial.max_date = max(
                filter(
                    None,
                    [partial.debit_move_id.date, partial.credit_move_id.date],
                ),
                default=False,
            )

    @api.depends(
        "debit_move_id.move_id.move_type",
        "debit_move_id.company_id",
        "credit_move_id.company_id",
    )
    def _compute_company_id(self):
        for partial in self:
            partial.company_id = _get_partial_company(partial)

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        if not self:
            return True

        to_update_payments = self._get_to_update_payments(from_state="paid")
        moves_to_reverse = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "in", self.ids)]
        )
        moves_to_reverse |= self.exchange_move_id

        full_to_unlink = self.full_reconcile_id

        all_reconciled = self.debit_move_id | self.credit_move_id
        _debug.pipeline(
            "unlink_reverse_drop_full_payments",
            partial=self,
            moves_to_reverse=moves_to_reverse,
            full_to_unlink=full_to_unlink,
            to_update_payments=to_update_payments,
        )

        res = super().unlink()

        full_to_unlink.with_context(defer_matching_number_update=True).unlink()

        if moves_to_reverse:
            not_draft_moves = moves_to_reverse.filtered(lambda m: m.state != "draft")
            draft_moves = moves_to_reverse - not_draft_moves
            if not_draft_moves:
                not_draft_moves._reverse_moves(
                    [
                        {
                            "date": move._get_accounting_date(
                                move.date, move._affect_tax_report()
                            ),
                            "ref": _("Reversal of: %s", move.name),
                        }
                        for move in not_draft_moves
                    ],
                    cancel=True,
                )
            if draft_moves:
                draft_moves.unlink()

        all_reconciled = all_reconciled.exists()
        self._update_matching_number(all_reconciled)
        to_update_payments.state = "in_process"
        return res

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        partials = super().create(vals_list)
        paid_payments = partials._get_to_update_payments(from_state="in_process")
        if _debug.lifecycle.enabled and paid_payments:
            _debug.lifecycle(
                "payments_in_process_paid",
                partial=partials,
                paid_payments=paid_payments,
            )
        paid_payments.state = "paid"
        self._update_matching_number(partials.debit_move_id | partials.credit_move_id)
        return partials

    def _prefetch_payment_state_fields(self):
        self.fetch(
            [
                "debit_move_id",
                "credit_move_id",
                "debit_currency_id",
                "credit_currency_id",
                "debit_amount_currency",
                "credit_amount_currency",
            ]
        )
        endpoint_moves = (self.debit_move_id | self.credit_move_id).move_id
        endpoint_moves.fetch(["matched_payment_ids"])
        matched_payments = endpoint_moves.matched_payment_ids.sudo()
        matched_payments.fetch(
            [
                "move_id",
                "outstanding_account_id",
                "state",
                "payment_type",
                "currency_id",
                "amount_signed",
            ]
        )
        matched_payments.currency_id.fetch(["rounding"])
        return matched_payments

    def _get_payment_comparable_amount(self, payment):
        self.check_singleton()
        if payment.currency_id == self.debit_currency_id:
            amount = self.debit_amount_currency
        elif payment.currency_id == self.credit_currency_id:
            amount = self.credit_amount_currency
        else:
            return None
        return amount if payment.payment_type == "inbound" else -amount

    @_debug.perf.timed
    def _get_to_update_payments(self, from_state):
        self = self.union()
        candidate_payments = self._prefetch_payment_state_fields().filtered(
            lambda payment: (
                not payment.outstanding_account_id and payment.state == from_state
            )
        )
        _debug.pipeline(
            "payment_state_candidates",
            partial=self,
            from_state=from_state,
            candidates=candidate_payments,
        )

        to_update_ids = set()
        grouped_amounts = {}
        for partial in self:
            partial_moves = (partial.credit_move_id | partial.debit_move_id).move_id
            partial_payments = partial_moves.matched_payment_ids.sudo()
            for payment in candidate_payments & partial_payments:
                amount = partial._get_payment_comparable_amount(payment)
                if amount is None:
                    continue
                if not payment.currency_id.compare_amounts(
                    payment.amount_signed, amount
                ):
                    to_update_ids.add(payment.id)
                elif payment.move_id in partial_moves:
                    grouped_amounts[payment.id] = (
                        grouped_amounts.get(payment.id, 0.0) + amount
                    )

        for payment in self.env["account.payment"].browse(grouped_amounts):
            if not payment.currency_id.compare_amounts(
                payment.amount_signed, grouped_amounts[payment.id]
            ):
                to_update_ids.add(payment.id)
        _debug.logic(
            "payment_state_matches",
            partial=self,
            from_state=from_state,
            grouped=len(grouped_amounts),
            to_update=len(to_update_ids),
        )
        return self.env["account.payment"].browse(to_update_ids)

    @api.model
    @_debug.perf.timed
    def _update_matching_number(self, amls):
        if not amls:
            return
        amls = amls._all_reconciled_lines()
        _debug.pipeline("_update_matching_number_over", amls=amls)
        while amls:
            amls.lock_for_update(allow_referencing=True)
            amls.invalidate_recordset(["matching_number"])
            amls.invalidate_recordset(
                ["matched_debit_ids", "matched_credit_ids"],
                flush=False,
            )
            expanded_amls = amls._all_reconciled_lines()
            if not (expanded_amls - amls):
                break
            amls = expanded_amls
        all_partials = amls.matched_debit_ids | amls.matched_credit_ids
        number2lines = group_lines_by_matching_number(
            (partial.id, partial.debit_move_id.id, partial.credit_move_id.id)
            for partial in all_partials
        )

        amls.flush_recordset(["full_reconcile_id"])
        self.env.cr.execute_values(
            """
            UPDATE account_move_line l
               SET matching_number = CASE
                       WHEN l.full_reconcile_id IS NOT NULL THEN l.full_reconcile_id::text
                       ELSE 'P' || source.number
                   END
              FROM (VALUES %s) AS source(number, ids)
             WHERE l.id = ANY(source.ids)
        """,
            list(number2lines.items()),
            page_size=1000,
        )
        processed_amls = self.env["account.move.line"].browse(
            [_id for ids in number2lines.values() for _id in ids]
        )
        _debug.perf.count(
            "matching_numbers_written",
            rows=len(processed_amls),
            numbers=len(number2lines),
        )
        processed_amls.invalidate_recordset(["matching_number"])
        (amls - processed_amls).matching_number = False
