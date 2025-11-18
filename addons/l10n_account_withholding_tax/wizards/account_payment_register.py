# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute='_compute_display_withholding')
    should_withhold_tax = fields.Boolean(
        string='Withhold Tax Amounts',
        readonly=False,
        store=True,
        copy=False,
        default=True
    )
    withholding_default_account_id = fields.Many2one(
        related='journal_id.default_account_id',
    )
    withhold_base_amount = fields.Monetary(
        string="Base Amount",
        compute='_compute_withhold_base_amount',
        store=True,
        readonly=False,
    )
    withhold_tax_amount = fields.Monetary(string="Withholding Tax Amount", compute='_compute_withhold_tax_amount')
    amount_after_withholding = fields.Monetary(
        string="Amount After Withholding",
        compute='_compute_amount_after_withholding',
    )
    withhold_account_ids = fields.Many2many(
        comodel_name='account.account',
        compute='_compute_withhold_account_ids',
        string="Withhold Accounts",
    )
    withhold_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        compute='_compute_withhold_account_ids',
        string="Withhold Taxes",
    )
    withhold_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Withholding Tax',
        compute='_compute_withhold_tax_id',
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id), ('is_withholding_tax_on_payment', '=', True), ('id', 'in', withhold_tax_ids)]",
    )
    withholding_outstanding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Outstanding Account",
        copy=False,
        domain="['|', ('account_type', 'in', ('asset_current', 'liability_current')), ('id', '=', withholding_default_account_id)]",
        check_company=True,
        compute="_compute_withholding_outstanding_account_id",
        store=True,
        readonly=False,
    )
    withholding_payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    withholding_hide_tax_base_account = fields.Boolean(compute='_compute_withholding_hide_tax_base_account')

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('amount', 'withhold_tax_amount', 'should_withhold_tax')
    def _compute_amount_after_withholding(self):
        for wizard in self:
            if wizard.should_withhold_tax:
                wizard.amount_after_withholding = wizard.amount - wizard.withhold_tax_amount

    @api.depends('withhold_tax_id', 'should_withhold_tax')
    def _compute_withhold_base_amount(self):
        for wizard in self:
            base = 0.0
            if wizard.withhold_tax_id:
                withhold_account_by_sum = wizard.line_ids.move_id._get_withhold_account_by_sum()
                for account, amount in withhold_account_by_sum.items():
                    if wizard.withhold_tax_id in account.withhold_tax_ids:
                        base = amount
            wizard.withhold_base_amount = abs(base)

    @api.depends('should_withhold_tax')
    def _compute_withhold_tax_id(self):
        for wizard in self:
            tax = self.env['account.tax']
            # Search for the last withhold move line that matches the account and partner
            withhold_tax_ids = wizard.withhold_account_ids._origin.mapped('withhold_tax_ids')
            withhold_move_line = self.env['account.move.line'].search([
                ('partner_id', '=', wizard.line_ids.partner_id.id),
                ('tax_ids', 'in', withhold_tax_ids.ids),
            ], limit=1, order='id desc')
            if withhold_move_line:
                applied_withhold_taxes = withhold_move_line.tax_ids.filtered(lambda t: t in wizard.withhold_account_ids._origin.withhold_tax_ids)
                if applied_withhold_taxes:
                    tax = applied_withhold_taxes[0]
            wizard.withhold_tax_id = tax

    @api.depends('should_withhold_tax')
    def _compute_withhold_account_ids(self):
        for wizard in self:
            accounts = wizard.line_ids.move_id._get_withhold_account_by_sum().keys()
            wizard.withhold_account_ids = [acc._origin.id for acc in accounts]
            wizard.withhold_tax_ids = wizard.withhold_account_ids._origin.mapped('withhold_tax_ids')

    @api.depends('withhold_tax_id', 'withhold_base_amount')
    def _compute_withhold_tax_amount(self):
        """ Compute the withholding tax amount based on the selected withholding tax and base amount. """
        for wizard in self:
            tax_amount = 0.0
            if wizard.withhold_tax_id:
                taxes_res = wizard.withhold_tax_id._get_tax_details(
                    wizard.withhold_base_amount,
                    quantity=1.0,
                    product=False,
                )
                tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
            wizard.withhold_tax_amount = abs(tax_amount)
            wizard.amount = wizard.withhold_base_amount

    @api.depends('withholding_payment_account_id', 'should_withhold_tax')
    def _compute_withholding_outstanding_account_id(self):
        """
        We propose a default account by getting one from the latest payment which:
         - Has the same payment method line id (and thus indirectly the same journal, and thus the same company)
         - That payment method has no payment_account_id
         - Yet the payment has an outstanding_account_id
         """
        for wizard in self:
            if not wizard.should_withhold_tax:
                wizard.withholding_outstanding_account_id = False
                continue
            if wizard.withholding_payment_account_id:
                continue
            latest_payment = self.env['account.payment'].search_read(
                domain=[
                    ('payment_method_line_id', '=', wizard.payment_method_line_id.id),
                    ('payment_method_line_id.payment_account_id', '=', False),
                    ('outstanding_account_id', '!=', False),
                ],
                fields=['outstanding_account_id'],
                limit=1,
                order='id desc',
            )
            if not latest_payment:
                wizard.withholding_outstanding_account_id = wizard.withholding_outstanding_account_id
            else:
                wizard.withholding_outstanding_account_id = latest_payment[0]['outstanding_account_id'][0]

    @api.depends('company_id', 'can_edit_wizard', 'can_group_payments', 'group_payment')
    def _compute_display_withholding(self):
        """ The withholding feature should not show on companies which does not contain any withholding taxes. """
        for company, wizards in self.grouped('company_id').items():
            if not company:
                wizards.display_withholding = False
                continue

            withholding_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('is_withholding_tax_on_payment', '=', True),
            ])
            for wizard in self:
                # To avoid displaying things for nothing, also ensure to only consider withholding taxes matching the payment type.
                payment_type = wizard.payment_type
                if any(line.is_refund for line in wizard.line_ids):
                    # In case of refunds, the payment type won't match the type_tax_use, we need to invert it.
                    if wizard.payment_type == 'inbound':
                        payment_type = 'outbound'
                    else:
                        payment_type = 'inbound'

                wizard_domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=wizard.company_id, payment_type=payment_type)
                wizard_withholding_taxes = withholding_taxes.filtered_domain(wizard_domain)

                will_create_multiple_entry = not wizard.can_edit_wizard or (wizard.can_group_payments and not wizard.group_payment)
                wizard.display_withholding = bool(wizard_withholding_taxes) and not will_create_multiple_entry

    @api.depends('company_id')
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for wizard in self:
            wizard.withholding_hide_tax_base_account = bool(wizard.company_id.withholding_tax_base_account_id)

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Update the computation of the payment vals in order to correctly set the outstanding account as well as the
        withholding line when needed.
        """
        # EXTEND 'account'
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        if not self.should_withhold_tax:
            return payment_vals

        # if self.withholding_net_amount < 0:
        #     raise UserError(self.env._("The withholding net amount cannot be negative."))

        # Prepare the withholding lines.
        withholding_account = self.company_id.withholding_tax_control_account_id
        if not withholding_account:
            raise UserError(self.env._("Please configure the withholding control account from the settings"))
        payment_vals['withholding_line_ids'] = [(Command.create({
                'analytic_distribution': False,
                'analytic_precision': 2,
                'name': False,
                'placeholder_type': 'given_by_sequence',
                'previous_placeholder_type': False,
                'tax_id': self.withhold_tax_id.id,
                'source_base_amount_currency': self.withhold_base_amount,
                'source_base_amount': self.withhold_base_amount,
                'source_tax_amount_currency': self.withhold_tax_amount,
                'source_tax_amount': self.withhold_tax_amount,
                'source_currency_id': 1,
                'source_tax_id': False,
                'base_amount': self.withhold_base_amount,
                'amount': self.withhold_tax_amount,
                'account_id': withholding_account.id,
        }))]
        return payment_vals

    # ----------------
    # Business methods
    # ----------------

    def _get_total_amount_in_wizard_currency(self):
        """
        Returns the total amount of the first batch, in the currency of the wizard.
        This information can be used to determine if we are doing a partial payment or not.
        """
        self.ensure_one()
        if not self.can_edit_wizard:
            return 0.0

        moves = self.batches[0]['lines'].move_id  # Use the move to get the TOTAL amount, including all installment.
        wizard_curr = self.currency_id
        comp_curr = self.company_currency_id

        total = 0.0
        for line in moves.line_ids.filtered(lambda batch_line: batch_line.display_type == 'payment_term'):
            currency = line.currency_id
            if currency == wizard_curr:
                # Same currency
                total += line.amount_currency
            elif currency != comp_curr and wizard_curr == comp_curr:
                # Foreign currency on source line but the company currency one on the opposite line.
                total += currency._convert(line.amount_currency, comp_curr, self.company_id, self.payment_date)
            elif currency == comp_curr and wizard_curr != comp_curr:
                # Company currency on source line but a foreign currency one on the opposite line.
                total += comp_curr._convert(line.balance, wizard_curr, self.company_id, self.payment_date)
            else:
                # Foreign currency on payment different from the one set on the journal entries.
                total += comp_curr._convert(line.balance, wizard_curr, self.company_id, self.payment_date)
        return total
