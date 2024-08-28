# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, Command, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute='_compute_display_withholding')
    withhold_tax = fields.Boolean(
        string='Withhold Tax Amounts',
        compute='_compute_withhold_tax',
        readonly=False,
        store=True,
        copy=False,
    )
    withholding_line_ids = fields.One2many(
        comodel_name='account.payment.withholding.line',
        string='Withholding Lines',
        inverse_name='payment_id',
    )
    original_amount = fields.Float()
    payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    # We may need to manually set an account, for this we want it to not be readonly by default.
    outstanding_account_id = fields.Many2one(readonly=False)

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('company_id')
    def _compute_display_withholding(self):
        """ We want to hide the withholding tax checkbox in two cases:
         - If there are now withholding taxes in the company;
         - In argentina
        """
        for payment in self:
            domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=payment.company_id, payment_type=payment.payment_type)
            available_withholding_taxes = self.env['account.tax'].search(domain)
            payment.display_withholding = available_withholding_taxes and payment.country_code != 'AR'

    @api.depends('withholding_line_ids')
    def _compute_withhold_tax(self):
        """ We enable the boolean by default only if withholding tax lines are given at the creation of the payment. """
        for wizard in self:
            wizard.withhold_tax = bool(wizard.withholding_line_ids)

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model_create_multi
    def create(self, vals_list):
        # EXTEND account to populate the original amount with the amount value at creation.
        for vals in vals_list:
            if 'amount' in vals:
                vals['original_amount'] = vals['amount']
        return super().create(vals_list)

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        # EXTEND account to add the withholding fields in the list.
        return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'withhold_tax')

    def _synchronize_to_moves(self, changed_fields):
        # EXTEND account to synchronize withholding tax lines.
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        # EXTEND account
        # We want to affect the payment in case it has withholding lines, or the withhold tax enabled.
        withholding_payments = self.filtered(lambda p: p.withholding_line_ids or p.withhold_tax)
        for pay in withholding_payments:
            # For withholding payments, we do not want to merge the writeoff lines. Instead, we will recompute them.
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            # Support the case of a withholding payment with line where we disable the "withhold tax".
            if pay.withhold_tax:
                withholding_line_vals_list = self.withholding_line_ids._prepare_withholding_line_vals()
            else:
                withholding_line_vals_list = None
            # We also recompute the value for the liquidity/counterpart line.
            # We need to make sure to provide the new write off lines in order to correctly compute the counterpart line amount.
            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=withholding_line_vals_list)
            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
            ]
            line_ids_commands.extend([Command.create(withholding_line_vals) for withholding_line_vals in line_vals_list[2:]])
            # Don't forget to remove the old writeoff lines.
            line_ids_commands.extend([Command.delete(line.id) for line in writeoff_lines])
            pay.move_id \
                .with_context(skip_invoice_sync=True) \
                .write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })

        # All other payments will use the original logic
        super(AccountPayment, self - withholding_payments)._synchronize_to_moves(changed_fields)

    def _generate_move_vals(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        # EXTEND account to prepare withholding line vals when generating the move.
        self.ensure_one()
        if self.withhold_tax:
            write_off_line_vals = write_off_line_vals or []
            write_off_line_vals.extend(self.withholding_line_ids._prepare_withholding_line_vals())
        return super()._generate_move_vals(write_off_line_vals, force_balance, line_ids)
