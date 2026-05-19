# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, Command


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
    withholding_entry_id = fields.Many2one(
        comodel_name='account.move',
        string='Withholding Journal Entry',
        readonly=True,
        copy=False,
    )
    withholding_total_tax_amount = fields.Monetary(
        string="Total Withholding Tax Amount",
        compute='_compute_withholding_total_tax_amount',
        help="Total withholding amount for the move",
    )
    withholding_net_amount = fields.Monetary(
        string="Net Amount",
        compute='_compute_withholding_net_amount',
        help="Total amount after withholding taxes",
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

    @api.depends('withholding_line_ids')
    def _compute_withholding_total_tax_amount(self):
        for payment in self:
            payment.withholding_total_tax_amount = abs(
                sum(line.amount for line in payment.withholding_line_ids)
            )

    @api.depends('withholding_total_tax_amount', 'amount')
    def _compute_withholding_net_amount(self):
        """
        The net amount is the one that will actually be paid by the payer.
        It is simply the payment amount - the sum of withholding taxes.
        """
        for payment in self:
            if payment.withholding_total_tax_amount:
                payment.withholding_net_amount = payment.amount - payment.withholding_total_tax_amount
            else:
                payment.withholding_net_amount = payment.amount

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
        return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'should_withhold_tax')

    def _prepare_move_withholding_lines(self, default_values):
        # EXTENDS account
        withholding_lines = super()._prepare_move_withholding_lines(default_values)
        if self.should_withhold_tax and self.withholding_line_ids:
            withholding_lines += self.withholding_line_ids._prepare_withholding_amls_create_values()
        return withholding_lines

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        if self.company_id.withhold_applicable_on != 'payment_bill':
            return super()._generate_journal_entry(
                write_off_line_vals=write_off_line_vals,
                force_balance=force_balance,
                line_ids=line_ids,
            )
        self.ensure_one()
        lines_per_type = self._prepare_move_lines_per_type(
            write_off_line_vals=None,
            force_balance=self.withholding_net_amount,
        )

        payment_lines = lines_per_type.get('liquidity_lines', []) + lines_per_type.get('counterpart_lines', []) + lines_per_type.get('write_off_lines', [])
        payment_move_vals = self._generate_move_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=[Command.create(line) for line in payment_lines],
        )
        payment_move = self.env['account.move'].create(payment_move_vals)
        self.write({
            'move_id': payment_move.id,
            'state': 'paid',
        })

        if lines_per_type.get('withholding_lines', []):
            withholding_move_vals = self._generate_move_vals(
                line_ids=[Command.create(line) for line in lines_per_type.get('withholding_lines', [])],
            )
            withholding_move_vals.update({
                'journal_id': self.company_id.withholding_journal_id.id,
            })
            withholding_move = self.env['account.move'].create(withholding_move_vals)
            withholding_move.action_post()
            self.write({
                'withholding_entry_id': withholding_move.id
            })

    def _synchronize_to_moves(self, changed_fields, skip_withholding_lines=False):
        regular_sync_payments = self.filtered(
            lambda p: p.company_id.withhold_applicable_on != 'payment_bill' or (p.move_id and not p.withholding_entry_id)
        )
        if regular_sync_payments:
            super(AccountPayment, regular_sync_payments)._synchronize_to_moves(changed_fields, skip_withholding_lines=False)

        payment_bill_sync_payments = self - regular_sync_payments
        if not payment_bill_sync_payments:
            return

        super(AccountPayment, payment_bill_sync_payments)._synchronize_to_moves(changed_fields, skip_withholding_lines=True)
        for pay in payment_bill_sync_payments:

            if not pay.withholding_entry_id or pay.withholding_entry_id.state == 'posted':
                continue

            wh_move = pay.withholding_entry_id

            # recompute withholding lines
            withholding_lines = self._prepare_move_withholding_lines({})

            commands = [(5, 0, 0)]
            for vals in withholding_lines:
                commands.append((0, 0, vals))

            wh_move.write({
                'date': pay.date,
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'line_ids': commands,
            })
            wh_reconc = pay.withholding_entry_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
            inv_reconc = pay.invoice_ids.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)
            pay_reconc = pay.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)
            (inv_reconc + wh_reconc + pay_reconc).reconcile()

    def _prepare_move_lines_per_type(self, write_off_line_vals=None, force_balance=None):
        line_vals_per_type = super()._prepare_move_lines_per_type(write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        if self.company_id.withhold_applicable_on == 'payment_bill':
            withholding_amount = abs(sum(line['balance'] for line in line_vals_per_type.get('withholding_lines', [])))
            counterpart_lines = line_vals_per_type.get('counterpart_lines', [])
            for line in counterpart_lines:
                line['balance'] -= withholding_amount
                if line.get('amount_currency'):
                    line['amount_currency'] -= withholding_amount
            line_vals_per_type.update({
                'counterpart_lines': counterpart_lines,
            })
        return line_vals_per_type

    def action_payment_l10n_withholding_entry(self):
        self.ensure_one()
        return {
            'name': "Withholding Entry",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.withholding_entry_id.id,
            'context': {'create': False},
        }

    def action_draft(self):
        super().action_draft()
        if self.withholding_entry_id:
            self.withholding_entry_id.button_draft()

    def write(self, vals):
        if vals.get('state') in ('paid', 'reconciled') and not vals.get('move_id'):
            self.withholding_entry_id.filtered(lambda m: m.state == 'draft').action_post()
        return super().write(vals)
