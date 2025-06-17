# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute='_compute_display_withholding')
    should_withhold_tax = fields.Boolean(
        string='Withhold Tax Amounts',
        help="Withhold tax amounts from the payment amount.",
        compute='_compute_should_withhold_tax',
        readonly=False,
        store=True,
        copy=False,
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
                ('is_withholding_tax_on_payment', '=', True),
            ])
            for payment in self:
                # To avoid displaying things for nothing, also ensure to only consider withholding taxes matching the payment type.
                payment_domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=payment.company_id, payment_type=payment.payment_type)
                payment_withholding_taxes = withholding_taxes.filtered_domain(payment_domain)

                payment.display_withholding = bool(payment_withholding_taxes)

    @api.depends('withholding_line_ids')
    def _compute_should_withhold_tax(self):
        """ Ensures that we display the line table if any withholding line has been added to the payment. """
        for payment in self:
            payment.should_withhold_tax = bool(payment.withholding_line_ids)

    @api.depends('company_id')
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for payment in self:
            payment.withholding_hide_tax_base_account = bool(payment.company_id.withholding_tax_base_account_id)

    @api.depends('should_withhold_tax')
    def _compute_outstanding_account_id(self):
        """ Update the computation to reset the account when should_withhold_tax is unchecked. """
        super()._compute_outstanding_account_id()

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
        # EXTEND account to add the withholding fields in the list.
        return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'should_withhold_tax')

    def _synchronize_to_moves(self, changed_fields):
        """ Updates the synchronization in order to ensure that the entry takes into account changes in the withholding lines. """
        # EXTEND account
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        withholding_payments = self.filtered(lambda payment: payment.withholding_line_ids and payment.should_withhold_tax)
        for pay in withholding_payments:
            liquidity_lines, counterpart_lines, write_off_lines = pay._seek_for_lines()

            # Reset/update the liquidity/counterpart lines.
            line_vals_list = pay._prepare_move_line_default_vals()
            liquidity_line_values = line_vals_list[0]
            counterpart_line_values = line_vals_list[1]

            # Generate the new withholding lines.
            liquidity_line_balance = liquidity_line_values['debit'] - liquidity_line_values['credit']
            liquidity_line_amount_currency = liquidity_line_values['amount_currency']
            withholding_line_values_list = pay.withholding_line_ids._prepare_withholding_amls_create_values()
            write_off_line_ids_commands = []
            for line_values in withholding_line_values_list:
                write_off_line_ids_commands.append(Command.create(line_values))
                liquidity_line_balance -= line_values['balance']
                liquidity_line_amount_currency -= line_values['amount_currency']
            if liquidity_line_balance > 0.0:
                liquidity_line_values['debit'] = liquidity_line_balance
                liquidity_line_values['credit'] = 0.0
            else:
                liquidity_line_values['debit'] = 0.0
                liquidity_line_values['credit'] = -liquidity_line_balance
            liquidity_line_values['amount_currency'] = liquidity_line_amount_currency

            line_ids_commands = [
                Command.update(liquidity_lines.id, liquidity_line_values) if liquidity_lines else Command.create(liquidity_line_values),
                Command.update(counterpart_lines.id, counterpart_line_values) if counterpart_lines else Command.create(counterpart_line_values),
            ] + [
                Command.delete(line.id)
                for line in write_off_lines
            ] + write_off_line_ids_commands

            pay.move_id \
                .with_context(skip_invoice_sync=True) \
                .write({
                    'name': '/',  # Set the name to '/' to allow it to be changed
                    'date': pay.date,
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                    'journal_id': pay.journal_id.id,
                })

        # All other payments will use the original logic
        super(AccountPayment, self - withholding_payments)._synchronize_to_moves(changed_fields)

    def _generate_move_vals(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        """ Ensure that the generated payment entry takes into account the withholding lines. """
        # EXTEND account
        move_vals = super()._generate_move_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance, line_ids=line_ids)
        if not self.withholding_line_ids or not self.should_withhold_tax:
            return move_vals

        liquidity_line_values = move_vals['line_ids'][0][2]
        liquidity_line_balance = liquidity_line_values['debit'] - liquidity_line_values['credit']
        liquidity_line_amount_currency = liquidity_line_values['amount_currency']
        withholding_line_values_list = self.withholding_line_ids._prepare_withholding_amls_create_values()
        for line_values in withholding_line_values_list:
            move_vals['line_ids'].append(Command.create(line_values))
            liquidity_line_balance -= line_values['balance']
            liquidity_line_amount_currency -= line_values['amount_currency']
        liquidity_line_values['amount_currency'] = liquidity_line_amount_currency
        if liquidity_line_balance > 0.0:
            liquidity_line_values['debit'] = liquidity_line_balance
            liquidity_line_values['credit'] = 0.0
        else:
            liquidity_line_values['debit'] = 0.0
            liquidity_line_values['credit'] = -liquidity_line_balance
        return move_vals
