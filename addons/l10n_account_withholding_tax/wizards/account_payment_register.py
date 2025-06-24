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
        compute='_compute_should_withhold_tax',
        readonly=False,
        store=True,
        copy=False,
    )
    withholding_line_ids = fields.One2many(
        string="Withholding Lines",
        comodel_name='account.payment.register.withholding.line',
        inverse_name='payment_register_id',
        compute='_compute_withholding_line_ids',
        store=True,
        readonly=False,
    )
    withholding_net_amount = fields.Monetary(
        string='Net Amount',
        help="Net amount after deducting the withholding lines",
        compute='_compute_withholding_net_amount',
        store=True,
    )
    # We need to define the outstanding account of the payment in order for it to have the proper journal entry.
    # To that end, we'll have this field required if we have a withholding tax impacting the payment, and we don't have a payment account set on the payment method.
    withholding_default_account_id = fields.Many2one(
        related='journal_id.default_account_id',
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

    @api.depends('withholding_line_ids.amount', 'amount')
    def _compute_withholding_net_amount(self):
        """
        The net amount is the one that will actually be paid by the payer.
        It is simply the payment amount - the sum of withholding taxes.
        """
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.withholding_net_amount = wizard.amount - sum(wizard.withholding_line_ids.mapped('amount'))
            else:
                wizard.withholding_net_amount = 0.0

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
                wizard_domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=wizard.company_id, payment_type=wizard.payment_type)
                wizard_withholding_taxes = withholding_taxes.filtered_domain(wizard_domain)

                will_create_multiple_entry = not wizard.can_edit_wizard or (wizard.can_group_payments and not wizard.group_payment)
                wizard.display_withholding = bool(wizard_withholding_taxes) and not will_create_multiple_entry

    @api.depends(
        'can_edit_wizard',
        'display_withholding',
    )
    def _compute_withholding_line_ids(self):
        """
        When opening the wizard, we want to compute the default withholding lines by looking at the invoice lines to see
        if they have withholding taxes set on them.
        """
        for wizard in self:
            # Disable the withholding lines.
            if not wizard.display_withholding or not wizard.can_edit_wizard:
                wizard.withholding_line_ids = [Command.clear()]
                continue

            # Compute the lines themselves once; when opening the wizard.
            if not wizard.withholding_line_ids:
                batch = wizard.batches[0]
                base_lines = []
                for move in batch['lines'].move_id:
                    move_base_lines, _move_tax_lines = move._get_rounded_base_and_tax_lines()
                    base_lines += move_base_lines

                wizard.withholding_line_ids = wizard.withholding_line_ids._prepare_withholding_lines_commands(
                    base_lines=base_lines,
                    company=wizard.company_id or self.env.company,
                )

    @api.depends('withholding_line_ids')
    def _compute_should_withhold_tax(self):
        """ Ensures that we display the line table if any withholding line has been added to the payment. """
        for wizard in self:
            wizard.should_withhold_tax = bool(wizard.withholding_line_ids)

    @api.depends('company_id')
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for wizard in self:
            wizard.withholding_hide_tax_base_account = bool(wizard.company_id.withholding_tax_base_account_id)

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
            or not self.can_edit_wizard
            or not self.withholding_line_ids._need_update_withholding_lines_placeholder()
        ):
            return

        self.withholding_line_ids._update_placeholders()

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

        if not self.withholding_line_ids or not self.should_withhold_tax:
            return payment_vals

        if self.withholding_net_amount < 0:
            raise UserError(self.env._("The withholding net amount cannot be negative."))

        # Prepare the withholding lines.
        withholding_account = self.withholding_outstanding_account_id
        if withholding_account:
            payment_vals['outstanding_account_id'] = withholding_account.id
            if not withholding_account.reconcile and withholding_account.account_type not in ('asset_cash', 'liability_credit_card', 'off_balance'):
                withholding_account.reconcile = True
        payment_vals['should_withhold_tax'] = self.should_withhold_tax
        payment_vals['withholding_line_ids'] = []
        for withholding_line_values in self.withholding_line_ids.with_context(active_test=False).copy_data():
            del withholding_line_values['payment_register_id']
            del withholding_line_values['placeholder_value']
            payment_vals['withholding_line_ids'].append(Command.create(withholding_line_values))
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
