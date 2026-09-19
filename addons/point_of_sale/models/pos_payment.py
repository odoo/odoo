from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, formatLang

from ..tools import debug_log as dbg


class PosPayment(models.Model):
    _name = "pos.payment"
    _description = "Point of Sale Payments"
    _order = "id desc"
    _inherit = ["mixin.pos.load"]

    name = fields.Char(
        string="Label",
        readonly=True,
    )
    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Order",
        index=True,
        required=True,
        ondelete="cascade",
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
        help="Total amount of the payment.",
    )
    payment_method_id = fields.Many2one(
        comodel_name="pos.payment.method",
        required=True,
    )
    payment_date = fields.Datetime(
        string="Date",
        default=lambda self: fields.Datetime.now(),
        readonly=True,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="pos_order_id.currency_id",
        string="Currency",
    )
    currency_rate = fields.Float(
        related="pos_order_id.currency_rate",
        string="Conversion Rate",
        help="Conversion rate from company currency to order currency.",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="pos_order_id.partner_id",
        string="Customer",
    )
    session_id = fields.Many2one(
        comodel_name="pos.session",
        related="pos_order_id.session_id",
        string="Session",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        related="session_id.user_id",
        string="Employee",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="pos_order_id.company_id",
        string="Company",
    )
    card_type = fields.Char(
        string="Type of card used",
        help="The type of the payment card (e.g. CREDIT CARD OR DEBIT CARD)",
    )
    card_brand = fields.Char(
        string="Brand of card",
        help="The brand of the payment card (e.g. Visa, AMEX, ...)",
    )
    card_no = fields.Char(string="Card Number(Last 4 Digit)")
    cardholder_name = fields.Char(string="Card Owner name")
    payment_ref_no = fields.Char(
        string="Payment reference number",
        help="Payment reference number from payment provider terminal",
    )
    payment_method_authcode = fields.Char(string="Payment APPR Code")
    payment_method_issuer_bank = fields.Char(string="Payment Issuer Bank")
    payment_method_payment_mode = fields.Char(string="Payment Mode")
    transaction_id = fields.Char(string="Payment Transaction ID")
    payment_status = fields.Char()
    ticket = fields.Char(string="Payment Receipt Info")
    is_change = fields.Boolean(
        string="Is this payment change?",
        default=False,
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        index="btree_not_null",
    )
    uuid = fields.Char(
        default=lambda self: str(uuid4()),
        copy=False,
        readonly=True,
    )

    _unique_uuid = models.Constraint(
        "unique (uuid)", "A payment with this uuid already exists"
    )

    @api.model
    def _get_pos_client_computed_fields(self):
        return {
            "currency_id",
            "currency_rate",
            "partner_id",
            "user_id",
            "display_name",
        }

    @api.model
    def _load_pos_data_fields(self, config):
        computed = self._get_pos_client_computed_fields()
        return [
            name
            for name, field in self._fields.items()
            if field.type != "binary" and (field.store or name in computed)
        ]

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("pos_order_id", "in", [order["id"] for order in data["pos.order"]])]

    @api.depends("name", "amount", "currency_id")
    def _compute_display_name(self):
        for payment in self:
            if payment.name:
                payment.display_name = f"{payment.name} {formatLang(self.env, payment.amount, currency_obj=payment.currency_id)}"
            else:
                payment.display_name = formatLang(
                    self.env, payment.amount, currency_obj=payment.currency_id
                )

    @api.constrains(
        "amount", "pos_order_id", "payment_method_id", "payment_date", "is_change"
    )
    def _check_order_is_editable(self):
        for payment in self:
            if (
                payment.pos_order_id.state == "done"
                or payment.pos_order_id.account_move
                or payment.account_move_id.state == "posted"
            ):
                raise ValidationError(
                    _("You cannot edit a payment for a posted order.")
                )

    def write(self, vals):
        dbg.lifecycle.debug(
            "pos.payment.write: %s keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if {
            "amount",
            "pos_order_id",
            "payment_method_id",
            "payment_date",
            "is_change",
            "uuid",
        }.intersection(vals):
            self._check_order_is_editable()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_order(self):
        dbg.lifecycle.debug("pos.payment.unlink: %s", dbg.rec(self))
        self._check_order_is_editable()

    @api.constrains("payment_method_id", "pos_order_id")
    def _check_payment_method_id(self):
        for payment in self:
            if (
                payment.payment_method_id
                not in payment.session_id.config_id.payment_method_ids
            ):
                raise ValidationError(
                    _(
                        "The payment method selected is not allowed in the config of the POS session."
                    )
                )

    @dbg.timed
    def _create_payment_moves(self, is_reverse=False):
        result = self.env["account.move"]
        change_payment = self.filtered(
            lambda p: p.is_change and p.payment_method_id.type == "cash"
        )
        payment_to_change = self.filtered(
            lambda p: not p.is_change and p.payment_method_id.type == "cash"
        )[:1]
        payments = self
        if change_payment and payment_to_change:
            payments = self - change_payment
        dbg.pipeline.debug(
            "[payments] %s: reverse=%s change=%s folded into %s",
            dbg.rec(self),
            is_reverse,
            dbg.rec(change_payment),
            dbg.rec(payment_to_change),
        )

        for payment in payments:
            if payment.account_move_id:
                dbg.logic.debug(
                    "[payments] %s already has move %s",
                    payment.id,
                    dbg.rec(payment.account_move_id),
                )
                continue
            order = payment.pos_order_id
            payment_method = payment.payment_method_id
            if payment_method.type == "pay_later" or float_is_zero(
                payment.amount, precision_rounding=order.currency_id.rounding
            ):
                dbg.logic.debug(
                    "[order:%s] payment %s skipped: type=%s amount=%s",
                    order.uuid,
                    payment.id,
                    payment_method.type,
                    payment.amount,
                )
                continue
            accounting_partner = payment.partner_id.commercial_partner_id
            pos_session = order.session_id
            journal = pos_session.config_id.journal_id
            if change_payment and payment == payment_to_change:
                pos_payment_ids = payment.ids + change_payment.ids
                payment_amount = payment.amount + sum(change_payment.mapped("amount"))
            else:
                pos_payment_ids = payment.ids
                payment_amount = payment.amount
            payment_move = (
                self.env["account.move"]
                .with_context(default_journal_id=journal.id)
                .create(
                    {
                        "journal_id": journal.id,
                        "date": fields.Date.context_today(order, order.date_order),
                        "ref": _(
                            "Invoice payment for %(order)s (%(account_move)s) using %(payment_method)s",
                            order=order.name,
                            account_move=order.account_move.name,
                            payment_method=payment_method.name,
                        ),
                        "pos_payment_ids": pos_payment_ids,
                    }
                )
            )
            result |= payment_move
            payment.write({"account_move_id": payment_move.id})
            amounts = pos_session._update_amounts(
                {"amount": 0, "amount_converted": 0},
                {"amount": payment_amount},
                payment.payment_date,
            )
            credit_line_vals = pos_session._prepare_credit_line_vals(
                {
                    "account_id": accounting_partner.with_company(
                        order.company_id
                    ).property_account_receivable_id.id,
                    "partner_id": accounting_partner.id,
                    "move_id": payment_move.id,
                    "no_followup": False,
                },
                amounts["amount"],
                amounts["amount_converted"],
            )
            is_split_transaction = payment.payment_method_id.split_transactions
            if is_split_transaction and is_reverse:
                reversed_move_receivable_account_id = accounting_partner.with_company(
                    order.company_id
                ).property_account_receivable_id.id
            elif is_reverse:
                reversed_move_receivable_account_id = (
                    payment.payment_method_id.receivable_account_id.id
                    or order.company_id.account_default_pos_receivable_account_id.id
                )
            else:
                reversed_move_receivable_account_id = (
                    order.company_id.account_default_pos_receivable_account_id.id
                )
            debit_line_vals = pos_session._prepare_debit_line_vals(
                {
                    "account_id": reversed_move_receivable_account_id,
                    "move_id": payment_move.id,
                    "partner_id": accounting_partner.id
                    if is_split_transaction and is_reverse
                    else False,
                    "no_followup": False,
                },
                amounts["amount"],
                amounts["amount_converted"],
            )
            self.env["account.move.line"].create([credit_line_vals, debit_line_vals])
            payment_move._post()
            dbg.pipeline.debug(
                "[order:%s] payment move %s: amount=%s receivable=%s split=%s",
                order.uuid,
                dbg.rec(payment_move),
                payment_amount,
                reversed_move_receivable_account_id,
                is_split_transaction,
            )
        return result

    def _get_receivable_lines_for_invoice_reconciliation(self, receivable_account):

        result = self.env["account.move.line"]
        for payment in self:
            if not payment.account_move_id:
                continue

            currency = payment.currency_id
            is_positive_amount = currency.compare_amounts(payment.amount, 0) > 0

            for line in payment.account_move_id.line_ids:
                if (
                    currency.compare_amounts(line.balance, 0) == 0
                    or line.account_id != receivable_account
                    or line.reconciled
                ):
                    continue

                if is_positive_amount:
                    if currency.compare_amounts(line.balance, 0) < 0:
                        result |= line
                elif currency.compare_amounts(line.balance, 0) > 0:
                    result |= line

        dbg.logic.debug(
            "[payments] %s receivable lines for reconciliation on %s: %s",
            dbg.rec(self),
            receivable_account.code,
            dbg.rec(result),
        )
        return result
