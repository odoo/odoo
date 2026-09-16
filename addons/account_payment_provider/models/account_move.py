import base64

from odoo import api, fields, models
from odoo.tools import SQL, format_date, str2bool
from odoo.tools.image import image_data_uri
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils


class AccountMove(models.Model):
    _inherit = "account.move"

    def _lock_for_payment(self):
        """Serialize payment initiation and cancellation, including stale snapshots.

        A row lock alone cannot make a repeatable-read snapshot observe a newly
        linked transaction. Updating the owner row forces that contender to retry.
        """
        if not self:
            return
        self.flush_recordset()
        self.env.cr.execute(
            SQL(
                """
            WITH locked AS MATERIALIZED (
                SELECT id FROM account_move
                WHERE id = ANY(%s) ORDER BY id FOR NO KEY UPDATE
            )
            UPDATE account_move AS invoice SET write_date = invoice.write_date
            FROM locked WHERE invoice.id = locked.id
            """,
                self.ids,
            )
        )
        self.invalidate_recordset(["state", "transaction_ids"])

    transaction_ids = fields.Many2many(
        comodel_name="payment.transaction",
        relation="account_invoice_transaction_rel",
        column1="invoice_id",
        column2="transaction_id",
        string="Transactions",
        copy=False,
        readonly=True,
    )
    authorized_transaction_ids = fields.Many2many(
        comodel_name="payment.transaction",
        string="Authorized Transactions",
        compute="_compute_authorized_transaction_ids",
        compute_sudo=True,
        copy=False,
        readonly=True,
    )
    transaction_count = fields.Count(count_of="transaction_ids")
    amount_paid = fields.Monetary(
        string="Amount paid",
        compute="_compute_amount_paid",
    )

    @api.depends("transaction_ids")
    def _compute_authorized_transaction_ids(self):
        for invoice in self:
            invoice.authorized_transaction_ids = invoice.transaction_ids.filtered(
                lambda tx: tx.state == "authorized"
            )

    @api.depends("transaction_ids")
    def _compute_amount_paid(self):
        """Sum the amounts of the transactions in state 'authorized' or 'done'."""
        for invoice in self:
            invoice.amount_paid = sum(
                invoice.transaction_ids.filtered(
                    lambda tx: tx.state in ("authorized", "done")
                ).mapped("amount")
            )

    def _prepare_online_payment_context(self):
        """Return the transactions and config relevant to online payment eligibility checks.

        Shared by :meth:`_has_to_be_paid` and :meth:`_get_online_payment_error` to avoid
        recomputing the same transaction filtering and config-parameter lookup twice.

        :return: The transactions in a pending/settled state, the subset of those still
                 pending on a real provider, and whether the online-payment feature is enabled.
        :rtype: tuple(recordset, recordset, bool)
        """
        self.check_singleton()
        transactions = self.transaction_ids.filtered(
            lambda tx: tx.state in ("pending", "authorized", "done")
        )
        pending_transactions = transactions.filtered(
            lambda tx: (
                tx.state in {"pending", "authorized"}
                and tx.provider_code not in {"none", "custom"}
            )
        )
        enabled_feature = str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account_payment_provider.enable_portal_payment")
        )
        return transactions, pending_transactions, enabled_feature

    def _has_to_be_paid(self):
        _transactions, pending_transactions, enabled_feature = (
            self._prepare_online_payment_context()
        )
        return enabled_feature and bool(
            self.state == "posted"
            and self.payment_state in ("not_paid", "in_payment", "partial")
            and not self.currency_id.is_zero(self.amount_residual)
            and self.amount_total
            and self.move_type == "out_invoice"
            and not pending_transactions
        )

    def _get_online_payment_error(self):
        """
        Returns the appropriate error message to be displayed if _has_to_be_paid() method returns False.
        """
        transactions, pending_transactions, enabled_feature = (
            self._prepare_online_payment_context()
        )
        errors = []
        if not enabled_feature:
            errors.append(_("This invoice cannot be paid online."))
        if transactions and not self.currency_id.is_zero(self.amount_residual):
            errors.append(_("There is no amount to be paid."))
        if self.state != "posted":
            errors.append(_("This invoice isn't posted."))
        if self.currency_id.is_zero(self.amount_residual):
            errors.append(_("This invoice has already been paid."))
        if self.move_type != "out_invoice":
            errors.append(_("This is not an outgoing invoice."))
        if pending_transactions:
            errors.append(_("There are pending transactions for this invoice."))
        return "\n".join(errors)

    @api.private
    def get_portal_last_transaction(self):
        self.check_singleton()
        return self.with_context(active_test=False).sudo().transaction_ids._get_last()

    def payment_action_capture(self):
        """Capture all transactions linked to this invoice."""
        self.check_singleton()
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        return self.sudo().transaction_ids.action_capture()

    def payment_action_void(self):
        """Void all transactions linked to this invoice."""
        self.check_singleton()
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        self.sudo().authorized_transaction_ids.action_void()

    def action_view_payment_transactions(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "payment.action_payment_transaction"
        )

        if len(self.transaction_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.transaction_ids.id
            action["views"] = []
        else:
            action["domain"] = [("id", "in", self.transaction_ids.ids)]

        return action

    def _prepare_payment_link_vals(self):
        next_payment_values = self._prepare_invoice_next_payment_values()
        amount_max = next_payment_values.get("amount_due")
        additional_info = {}
        open_installments = []
        installment_state = next_payment_values.get("installment_state")
        next_amount_to_pay = next_payment_values.get("next_amount_to_pay")
        if installment_state in ("next", "overdue"):
            open_installments = []
            for installment in next_payment_values.get("not_reconciled_installments"):
                data = {
                    "type": installment["type"],
                    "number": installment["number"],
                    "amount": installment["amount_residual_currency_unsigned"],
                    "date_maturity": format_date(
                        self.env, installment["date_maturity"]
                    ),
                }
                open_installments.append(data)

        elif installment_state == "epd":
            amount_max = next_amount_to_pay  # with epd, next_amount_to_pay is the invoice amount residual
            additional_info.update(
                {
                    "has_eligible_epd": True,
                    "discount_date": next_payment_values.get("discount_date"),
                }
            )

        return {
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_id.id,
            "open_installments": open_installments,
            "amount": next_amount_to_pay,
            "amount_max": amount_max,
            **additional_info,
        }

    def _generate_portal_payment_qr(self):
        self.check_singleton()
        portal_url = self._get_portal_payment_link()
        barcode = self.env["ir.actions.report"].prepare_barcode(
            barcode_type="QR", value=portal_url, width=128, height=128, quiet=False
        )
        return image_data_uri(base64.b64encode(barcode))

    def _get_portal_payment_link(self):
        self.check_singleton()
        payment_link_wizard = (
            self.env["payment.link.wizard"]
            .with_context(active_id=self.id, active_model=self._name)
            .create(
                {
                    "amount": self.amount_residual,
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
        )
        return payment_link_wizard.link
