# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from odoo.addons.loyalty.const import LOYALTY_PAYMENT_CODES


class AccountPayment(models.Model):
    _inherit = "account.payment"

    loyalty_card_id = fields.Many2one(
        string="Card",
        comodel_name="loyalty.card",
        compute="_compute_loyalty_card_id",
        store=True,
        readonly=False,
        copy=False,
        index="btree_not_null",
        domain="""[
            ('program_type', '=', payment_method_code),
            ('points', '>', 0),
            ('company_id', 'in', [False, company_id]),
            '|',
                ('program_type', '!=', 'ewallet'),
                ('partner_id', 'child_of', commercial_partner_id),
        ]""",
        help="The gift card or eWallet whose balance is used to make the payment.",
    )
    loyalty_card_balance = fields.Monetary(
        string="Card Balance", compute="_compute_loyalty_card_balance", currency_field="currency_id"
    )
    is_loyalty_payment = fields.Boolean(compute="_compute_is_loyalty_payment")
    show_loyalty_card_id = fields.Boolean(compute="_compute_is_loyalty_payment")

    # === COMPUTE METHODS === #

    @api.depends("payment_method_line_id", "partner_id")
    def _compute_is_loyalty_payment(self):
        for payment in self:
            payment.is_loyalty_payment = payment.payment_method_code in LOYALTY_PAYMENT_CODES
            # The eWallet of the customer is selected automatically when they have only one.
            payment.show_loyalty_card_id = payment.is_loyalty_payment and (
                payment.payment_method_code != "ewallet"
                or len(payment._get_available_loyalty_cards()) > 1
            )

    @api.depends("payment_method_line_id", "partner_id")
    def _compute_loyalty_card_id(self):
        for payment in self:
            card = payment.loyalty_card_id
            if payment.payment_method_code not in LOYALTY_PAYMENT_CODES:
                payment.loyalty_card_id = False
            elif payment.payment_method_code == "ewallet":
                available_cards = payment._get_available_loyalty_cards()
                payment.loyalty_card_id = card if card in available_cards else available_cards[:1]
            elif card.program_type != payment.payment_method_code:
                payment.loyalty_card_id = False
            else:
                payment.loyalty_card_id = card

    @api.depends("loyalty_card_id", "currency_id", "date")
    def _compute_loyalty_card_balance(self):
        for payment in self:
            card = payment.loyalty_card_id
            payment.loyalty_card_balance = card and card._get_payment_balance(
                payment.currency_id, payment.company_id, payment.date
            )

    @api.depends("payment_method_line_id")
    def _compute_use_electronic_payment_method(self):
        """Override of `account_payment` to hide the token and transaction fields of loyalty
        payments, which never use them."""
        super()._compute_use_electronic_payment_method()
        for payment in self:
            if payment.payment_method_code in LOYALTY_PAYMENT_CODES:
                payment.use_electronic_payment_method = False

    def _get_available_loyalty_cards(self):
        """Return the eWallets of the customer that can be used to pay."""
        self.ensure_one()
        if self.payment_method_code != "ewallet" or not self.partner_id:
            return self.env["loyalty.card"]
        return self.env["loyalty.card"]._get_payment_cards(
            "ewallet", self.partner_id, self.company_id
        )

    # === ONCHANGE METHODS === #

    @api.onchange("loyalty_card_id")
    def _onchange_loyalty_card_id(self):
        """Use the balance of the card as amount if the current amount exceeds it."""
        if not self.loyalty_card_id or self.payment_type != "inbound":
            return
        balance = self.loyalty_card_balance
        if not self.amount or self.currency_id.compare_amounts(self.amount, balance) > 0:
            self.amount = balance

    # === CONSTRAINT METHODS === #

    @api.constrains("payment_method_line_id", "loyalty_card_id", "state")
    def _check_loyalty_card_id(self):
        for payment in self:
            if not payment.loyalty_card_id or payment.state in ("draft", "canceled", "rejected"):
                if payment.payment_method_code in LOYALTY_PAYMENT_CODES and payment.state not in (
                    "draft",
                    "canceled",
                    "rejected",
                ):
                    raise ValidationError(
                        self.env._(
                            "Please select the card to use to pay with %s.",
                            payment.payment_method_line_id.name,
                        )
                    )
                continue
            card = payment.loyalty_card_id
            if card.program_type != payment.payment_method_code:
                raise ValidationError(
                    self.env._(
                        "The card %(code)s cannot be used with the payment method %(method)s.",
                        code=card.code,
                        method=payment.payment_method_line_id.name,
                    )
                )
            if card.program_type == "ewallet" and (
                card.partner_id.commercial_partner_id != payment.commercial_partner_id
            ):
                raise ValidationError(
                    self.env._(
                        "The eWallet %(code)s does not belong to %(partner)s.",
                        code=card.code,
                        partner=payment.partner_id.display_name,
                    )
                )

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._sync_loyalty_card_points()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if {"state", "amount", "loyalty_card_id", "payment_type", "currency_id"} & vals.keys():
            self._sync_loyalty_card_points()
        return res

    def unlink(self):
        self._get_loyalty_history_lines().sudo().unlink()
        return super().unlink()

    # === BUSINESS METHODS === #

    def _get_loyalty_history_lines(self):
        return (
            self
            .env["loyalty.history"]
            .sudo()
            .search([("order_model", "=", self._name), ("order_id", "in", self.ids)])
        )

    def _sync_loyalty_card_points(self):
        """Consume (or credit back, for outbound payments) the balance of the cards used to pay.

        The balance of a card is consumed when its payment is confirmed and restored when the
        payment is reset to draft, canceled, rejected or deleted.

        :raise ValidationError: If the balance of a card is insufficient.
        """
        history_lines = self._get_loyalty_history_lines()
        lines_per_payment = history_lines.grouped(lambda line: line.order_id)
        for payment in self:
            lines = lines_per_payment.get(payment.id, self.env["loyalty.history"])
            card = payment.loyalty_card_id.sudo()
            if not card or payment.state in ("draft", "canceled", "rejected"):
                lines.unlink()
                continue

            sign = -1 if payment.payment_type == "inbound" else 1
            points = sign * card._amount_to_points(
                payment.amount, payment.currency_id, payment.company_id, payment.date
            )
            current_points = sum(lines.mapped("issued")) - sum(lines.mapped("used"))
            if lines.card_id == card and not float_compare(
                current_points, points, precision_digits=2
            ):
                continue  # Already in sync.

            card.lock_for_update()
            lines.unlink()
            card.invalidate_recordset(["points"])
            if points < 0 and float_compare(card.points, -points, precision_digits=2) < 0:
                raise ValidationError(
                    self.env._(
                        "The balance of the card %(code)s (%(balance)s) is insufficient to pay"
                        " %(amount)s.",
                        code=card.code,
                        balance=payment.currency_id.format(
                            card._get_payment_balance(
                                payment.currency_id, payment.company_id, payment.date
                            )
                        ),
                        amount=payment.currency_id.format(payment.amount),
                    )
                )
            if not card._is_usable_for_payment():
                raise ValidationError(self.env._("The card %s can no longer be used.", card.code))
            card._adjust_points(
                points,
                self.env._("Payment %s", payment.name or payment.memo or ""),
                order_model=self._name,
                order_id=payment.id,
            )
