from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_last_5_minutes_messages(self, body):
        self.check_singleton()
        return self.env["mail.message"].search(
            [
                ("model", "=", self.move_id._name),
                ("res_id", "=", self.move_id.id),
                ("author_id", "=", self.env.user.partner_id.id),
                ("create_date", ">=", fields.Datetime.now() - relativedelta(minutes=5)),
                ("body", "=", body),
            ],
            limit=1,
        )

    @_debug.perf.timed
    def _post_matching_note(self, body):
        _debug.lifecycle("_post_matching_note", records=self)
        self.check_singleton()
        if self._get_last_5_minutes_messages(body=body):
            return
        self.move_id.message_post(body=body, author_id=self.env.user.partner_id.id)

    @_debug.perf.timed
    def _post_matching_done_confirmation(self):
        _debug.lifecycle("_post_matching_done_confirmation", records=self)
        self.check_singleton()
        if not self.is_reconciled:
            return
        body = _("Matching done")
        if reconcile_model := self.move_id.line_ids.reconcile_model_id:
            body += _(
                " - %(reconcile_model_name)s",
                reconcile_model_name=", ".join(reconcile_model.mapped("name")),
            )
        self._post_matching_note(body)

    @_debug.perf.timed
    def _post_matching_unreconciled(self):
        _debug.lifecycle("_post_matching_unreconciled", records=self)
        self.check_singleton()
        if self.is_reconciled:
            return
        self._post_matching_note(_("Matching unreconciled"))

    @_debug.perf.timed
    def _create_payment_with_move_from_invoice(self, move_id):
        return (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=move_id.ids,
                force_payment_move=True,
            )
            .create(
                {
                    "payment_date": self.date,
                }
            )
            ._create_payments()
        )

    @_debug.perf.timed
    def _reconcile_with_payments(self, payments, amls_to_create, reconciled_lines=None):
        self.check_singleton()
        has_exchange_diff = False
        if reconciled_lines:
            for reconciled_line, aml_to_create in zip(
                reconciled_lines, amls_to_create, strict=True
            ):
                exchange_diff_balance = self._lines_get_account_balance_exchange_diff(
                    reconciled_line.currency_id,
                    reconciled_line.amount_residual,
                    reconciled_line.amount_residual_currency,
                )
                has_exchange_diff = (
                    has_exchange_diff
                    or not reconciled_line.currency_id.is_zero(exchange_diff_balance)
                )
                new_balance = -(reconciled_line.amount_residual + exchange_diff_balance)

                aml_to_create["balance"] = new_balance

        _debug.pipeline(
            "payment_lines_prepared",
            stline=self,
            payments=payments,
            amls=len(amls_to_create),
            reconciled_lines=len(reconciled_lines or ()),
            has_exchange_diff=has_exchange_diff,
        )
        self.with_context(
            no_exchange_difference_no_recursive=not has_exchange_diff
        )._add_move_line_to_statement_line_move(amls_to_create)
        if payments_to_validate := payments.filtered(
            lambda p: (
                not p.move_id
                and p.state in self.env["account.payment"]._valid_payment_states()
            )
        ):
            _debug.logic(
                "payments_validated", stline=self, payment=payments_to_validate
            )
            payments_to_validate.action_validate()
