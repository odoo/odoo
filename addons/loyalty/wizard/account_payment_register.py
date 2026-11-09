# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.loyalty.const import LOYALTY_PAYMENT_CODES


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    loyalty_card_id = fields.Many2one(
        string="Card",
        comodel_name="loyalty.card",
        compute="_compute_loyalty_card_id",
        store=True,
        readonly=False,
        domain="""[
            ('program_type', '=', payment_method_code),
            ('points', '>', 0),
            ('company_id', 'in', [False, company_id]),
            '|',
                ('program_type', '!=', 'ewallet'),
                ('partner_id', 'child_of', partner_id),
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
        for wizard in self:
            wizard.is_loyalty_payment = wizard.payment_method_code in LOYALTY_PAYMENT_CODES
            # The eWallet of the customer is selected automatically when they have only one.
            wizard.show_loyalty_card_id = wizard.is_loyalty_payment and (
                wizard.payment_method_code != "ewallet"
                or len(wizard._get_available_loyalty_cards()) > 1
            )

    @api.depends("payment_method_line_id", "partner_id")
    def _compute_loyalty_card_id(self):
        for wizard in self:
            card = wizard.loyalty_card_id
            if wizard.payment_method_code not in LOYALTY_PAYMENT_CODES:
                wizard.loyalty_card_id = False
            elif wizard.payment_method_code == "ewallet":
                available_cards = wizard._get_available_loyalty_cards()
                wizard.loyalty_card_id = card if card in available_cards else available_cards[:1]
            elif card.program_type != wizard.payment_method_code:
                wizard.loyalty_card_id = False
            else:
                wizard.loyalty_card_id = card

    @api.depends("loyalty_card_id", "currency_id", "payment_date")
    def _compute_loyalty_card_balance(self):
        for wizard in self:
            card = wizard.loyalty_card_id
            wizard.loyalty_card_balance = card and card._get_payment_balance(
                wizard.currency_id, wizard.company_id, wizard.payment_date
            )

    @api.depends("loyalty_card_balance")
    def _compute_amount(self):
        """Override of `account` to limit the amount to the balance of the card."""
        super()._compute_amount()
        for wizard in self:
            if (
                wizard.loyalty_card_id
                and wizard.payment_type == "inbound"
                and wizard.currency_id.compare_amounts(wizard.amount, wizard.loyalty_card_balance)
                > 0
            ):
                wizard.amount = wizard.loyalty_card_balance

    def _get_available_loyalty_cards(self):
        """Return the eWallets of the customer that can be used to pay."""
        self.ensure_one()
        if self.payment_method_code != "ewallet" or not self.partner_id:
            return self.env["loyalty.card"]
        return self.env["loyalty.card"]._get_payment_cards(
            "ewallet", self.partner_id, self.company_id
        )

    # === BUSINESS METHODS === #

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.loyalty_card_id:
            payment_vals["loyalty_card_id"] = self.loyalty_card_id.id
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        if self.loyalty_card_id:
            payment_vals["loyalty_card_id"] = self.loyalty_card_id.id
        return payment_vals

    def _create_payments(self):
        if self.is_loyalty_payment and not self.loyalty_card_id:
            raise UserError(
                self.env._(
                    "Please select the card to use to pay with %s.",
                    self.payment_method_line_id.name,
                )
            )
        return super()._create_payments()
