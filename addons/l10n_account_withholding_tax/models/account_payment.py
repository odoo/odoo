# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute='_compute_display_withholding')
    withhold = fields.Selection(
        selection=[
            ('withhold_pay', 'Withhold and Pay'),
            ('withhold', 'Withhold Only'),
            ('payment', 'Payment Only'),
        ],
        copy=False,
        default='payment',
    )
    withholding_line_ids = fields.One2many(
        string='Withholding Lines',
        comodel_name='account.payment.withholding.line',
        inverse_name='payment_id',
    )
    withholding_payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    # We may need to manually set an account, for this we want it to not be readonly by default.
    outstanding_account_id = fields.Many2one(readonly=False)
    withholding_hide_tax_base_account = fields.Boolean(compute='_compute_withholding_hide_tax_base_account')
    withholding_amount = fields.Monetary(
        string="Withholding Amount",
        compute="_compute_withholding_amount",
        currency_field='currency_id',
    )
    withholding_net_amount = fields.Monetary(
        string="Net Amount",
        compute="_compute_withholding_net_amount",
        currency_field='currency_id',
        help="The amount that will actually be paid after deducting withholding taxes.",
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('company_id')
    def _compute_display_withholding(self):
        """ The withholding feature should not show on companies which does not contain any withholding taxes. """
        for company, payments in self.grouped('company_id').items():
            if not company:
                payments.display_withholding = False
                continue

            withholding_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('is_withholding_tax', '=', True),
            ])
            for payment in self:
                # To avoid displaying things for nothing, also ensure to only consider withholding taxes matching the payment type.
                payment_domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=payment.company_id, payment_type=payment.payment_type)
                payment_withholding_taxes = withholding_taxes.filtered_domain(payment_domain)

                payment.display_withholding = bool(payment_withholding_taxes)

    @api.depends('company_id')
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for payment in self:
            payment.withholding_hide_tax_base_account = bool(payment.company_id.withholding_tax_base_account_id)

    @api.depends('withhold')
    def _compute_outstanding_account_id(self):
        """ Update the computation to reset the account when withhold is changed. """
        super()._compute_outstanding_account_id()

    @api.depends('withholding_line_ids.amount')
    def _compute_withholding_amount(self):
        for payment in self:
            payment.withholding_amount = sum(payment.withholding_line_ids.mapped('amount'))

    @api.depends('withholding_amount', 'amount')
    def _compute_withholding_net_amount(self):
        for payment in self:
            payment.withholding_net_amount = payment.amount - payment.withholding_amount

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange('withholding_line_ids')
    def _onchange_withholding_line_ids(self):
        """
        Any time a line is edited, we want to check if we need to recompute the placeholders.
        The idea is to try and display accurate placeholders on lines whose tax have a sequence set.
        """
        self.ensure_one()
        if (
            not self.display_withholding
            or not self.withholding_line_ids._need_update_withholding_lines_placeholder()
        ):
            return

        self.withholding_line_ids._update_placeholders()

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        # EXTEND account
        return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'withhold')

    def _prepare_move_withholding_lines(self, default_values):
        # EXTENDS account
        withholding_lines = super()._prepare_move_withholding_lines(default_values)
        if self.withhold != 'payment' and self.withholding_line_ids:
            withholding_lines += self.withholding_line_ids._prepare_withholding_amls_create_values()
        return withholding_lines

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        withhold_payments = self.filtered(lambda p: p.withhold == 'withhold')
        regular_payments = self - withhold_payments

        if regular_payments:
            super(AccountPayment, regular_payments)._generate_journal_entry(write_off_line_vals, force_balance, line_ids)

        if withhold_payments:
            move_vals = [
                pay._generate_move_vals(write_off_line_vals, force_balance, line_ids)
                for pay in withhold_payments
            ]
            moves = self.env['account.move'].create(move_vals)
            for pay, move in zip(withhold_payments, moves):
                pay.write({'move_id': move.id, 'state': 'paid'})

    def _prepare_move_liquidity_lines(self, default_values):
        """
        Skip liquidity lines when processing a withholding-only payment,
        as no cash or bank movement should be recorded.
        """
        self.ensure_one()
        if self.withhold == 'withhold' and self.withholding_line_ids:
            return []
        return super()._prepare_move_liquidity_lines(default_values)

    @api.constrains('payment_method_line_id')
    def _check_payment_method_line_id(self):
        super(AccountPayment, self.filtered(lambda p: p.withhold != 'withhold'))._check_payment_method_line_id()
