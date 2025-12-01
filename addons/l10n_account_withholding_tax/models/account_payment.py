# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    should_withhold_tax = fields.Boolean(
        string='Apply Withholding Tax',
        help="Whether or not to apply withholding taxes on this payment.",
        compute='_compute_should_withhold_tax',
        readonly=False,
        store=True,
        copy=False,
    )
    withholding_payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    # We may need to manually set an account, for this we want it to not be readonly by default.
    outstanding_account_id = fields.Many2one(readonly=False)
    withholding_hide_tax_base_account = fields.Boolean(compute='_compute_withholding_hide_tax_base_account')

    withhold_base_amount = fields.Monetary(
        string='Withholding Base Amount',
        currency_field='currency_id',
    )
    withhold_tax_amount = fields.Monetary(string="Withholding Tax Amount", compute='_compute_withhold_tax_amount')
    withhold_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Withholding Tax',
        readonly=False,
        domain="[('company_id', '=', company_id), ('is_withholding_tax_on_payment', '=', True)]",
    )

    @api.onchange('withhold_base_amount')
    def _onchange_withhold_base_amount(self):
        """ When the amount changes, update the withholding base amount accordingly. """
        for record in self:
            record.amount = record.withhold_base_amount - record.withhold_tax_amount

    @api.depends('withhold_tax_id', 'withhold_base_amount')
    def _compute_withhold_tax_amount(self):
        """ Compute the withholding tax amount based on the selected withholding tax and base amount. """
        for record in self:
            tax_amount = 0.0
            if record.withhold_tax_id:
                taxes_res = record.withhold_tax_id._get_tax_details(
                    record.withhold_base_amount,
                    quantity=1.0,
                    product=False,
                )
                tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
                # record.amount = taxes_res['total_included']
            record.withhold_tax_amount = abs(tax_amount)

    # @api.onchange('amount', 'withhold_tax_id')
    # def _onchange_amount_withholding_tax(self):
    #     print("-------------------------------------")
    #     print("-------------------------------------")
    #     print("-------------------------------------")
    #     if self.withhold_tax_id:
    #         taxes_res = self.withhold_tax_id._get_tax_details(
    #             self.amount,
    #             quantity=1.0,
    #             product=False,
    #         )
    #         self.withhold_base_amount = taxes_res['total_excluded']

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('company_id')
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for payment in self:
            payment.withholding_hide_tax_base_account = bool(payment.company_id.withholding_tax_control_account_id)

    @api.depends('should_withhold_tax')
    def _compute_outstanding_account_id(self):
        """ Update the computation to reset the account when should_withhold_tax is unchecked. """
        super()._compute_outstanding_account_id()

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        res = super()._generate_journal_entry(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=line_ids,
        )

        if self.withhold_base_amount and self.withhold_tax_id and self.withhold_tax_amount and not self.outstanding_account_id:
            total_amount = self.withhold_base_amount
            header_vals = {
                'move_type': 'entry',
                'ref': self.memo,
                'date': self.date,
                'journal_id': self.company_id.withholding_journal_id.id,
                'company_id': self.company_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
            }

            line_vals = []

            tax_account = self.withhold_tax_id.invoice_repartition_line_ids.filtered(lambda r: r.repartition_type == 'tax').account_id
            line_vals.append(Command.create({
                'quantity': 1.0,
                'price_unit': total_amount,
                'debit': total_amount,
                'credit': 0.0,
                'account_id': self.company_id.withholding_tax_control_account_id.id,
                'tax_ids': [Command.set([self.withhold_tax_id.id])],
            }))
            self.withhold_tax_id = self.withhold_tax_id
            self.withhold_base_amount = self.withhold_base_amount
            tax_amount = self.withhold_tax_amount

            # balancing line (credit)
            line_vals.append(Command.create({
                'quantity': 1.0,
                'price_unit': total_amount,
                'debit': 0.0,
                'credit': total_amount,
                'account_id': self.company_id.withholding_tax_control_account_id.id,
                'tax_ids': False,
            }))

            # Balance line with partner account (debit)
            line_vals.append(Command.create({
                'quantity': 1.0,
                'debit': tax_amount,
                'price_unit': tax_amount,
                'credit': 0.0,
                'account_id': self.partner_id.property_account_payable_id.id,
                'tax_ids': False,
            }))

            line_vals.append(Command.create({
                'quantity': 1.0,
                'debit': 0.0,
                'price_unit': tax_amount,
                'credit': tax_amount,
                'account_id': tax_account.id,
                'tax_ids': False,
            }))
            move_id = self.with_company(self.company_id).env['account.move'].create({
                **header_vals,
                'line_ids': line_vals,
            })
            self.move_id = move_id

        return res

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        # EXTEND account to add the withholding fields in the list.
        # return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'should_withhold_tax')
        return super()._get_trigger_fields_to_synchronize() + ('should_withhold_tax','withhold_tax_id','withhold_base_amount','withhold_tax_amount')

    def _seek_for_lines(self):
        res = super()._seek_for_lines()
        if not self.withhold_tax_amount or not self.should_withhold_tax:
            return res
        res[1] = res[1].filtered(lambda line: not line.is_withhold_line)
        print(res[1])
        print(res[1])
        return res


    def _synchronize_to_moves(self, changed_fields):
        """ Updates the synchronization in order to ensure that the entry takes into account changes in the withholding lines. """
        # EXTEND account
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        withholding_payments = self.filtered(lambda payment: payment.withhold_tax_amount and payment.withhold_tax_amount)
        for pay in withholding_payments:
            withhold_base_amount = pay.withhold_base_amount
            liquidity_lines, counterpart_lines, write_off_lines = pay._seek_for_lines()

            write_off_lines += pay.move_id.line_ids.filtered(lambda line: line.is_withhold_line)

            # Reset/update the liquidity/counterpart lines.
            line_vals_list = pay._prepare_move_line_default_vals()
            liquidity_line_values = line_vals_list[0]
            counterpart_line_values = line_vals_list[1]

            # Generate the new withholding lines.
            liquidity_line_balance = liquidity_line_values['debit'] - liquidity_line_values['credit']
            liquidity_line_amount_currency = liquidity_line_values['amount_currency']
            # withholding_line_values_list = pay.withholding_line_ids._prepare_withholding_amls_create_values()
            write_off_line_ids_commands = [
                Command.create({
                    'quantity': 1.0,
                    'price_unit': pay.withhold_base_amount,
                    'debit': pay.withhold_base_amount,
                    'credit': 0.0,
                    'account_id': pay.company_id.withholding_tax_control_account_id.id,
                    'tax_ids': [Command.set([pay.withhold_tax_id.id])],
                }),
                Command.create({
                    'quantity': 1.0,
                    'price_unit': pay.withhold_base_amount,
                    'debit': 0.0,
                    'credit': pay.withhold_base_amount,
                    'account_id': pay.company_id.withholding_tax_control_account_id.id,
                    'tax_ids': False,
                }),
                Command.create({
                    'quantity': 1.0,
                    'debit': pay.withhold_tax_amount,
                    'price_unit': pay.withhold_tax_amount,
                    'credit': 0.0,
                    'account_id': pay.partner_id.property_account_payable_id.id,
                    'tax_ids': False,
                    'is_withhold_line': True,
                }),
                Command.create({
                    'quantity': 1.0,
                    'debit': 0.0,
                    'price_unit': pay.withhold_tax_amount,
                    'credit': pay.withhold_tax_amount,
                    'account_id': pay.withhold_tax_id.invoice_repartition_line_ids.filtered(lambda r:
                        r.repartition_type == 'tax').account_id.id,
                    'tax_ids': False,
                    'is_withhold_line': True,
                }),
            ]
            # for line_values in withholding_line_values_list:
            #     write_off_line_ids_commands.append(Command.create(line_values))
            #     liquidity_line_balance -= line_values['balance']
            #     liquidity_line_amount_currency -= line_values['amount_currency']
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
        if not self.withhold_tax_amount or not self.should_withhold_tax:
            return move_vals
        withhold_vals = []
        tax_amount = self.withhold_tax_amount
        total_amount = self.withhold_base_amount

        tax_account = self.withhold_tax_id.invoice_repartition_line_ids.filtered(lambda r: r.repartition_type == 'tax').account_id
        withhold_vals.append(Command.create({
            'quantity': 1.0,
            'price_unit': total_amount,
            'debit': total_amount,
            'credit': 0.0,
            'account_id': self.company_id.withholding_tax_control_account_id.id,
            'tax_ids': [Command.set([self.withhold_tax_id.id])],
            'is_withhold_line': True,
        }))
        self.withhold_tax_id = self.withhold_tax_id
        self.withhold_base_amount = self.withhold_base_amount
        self.withhold_tax_amount = self.withhold_tax_amount

        # balancing line (credit)
        withhold_vals.append(Command.create({
            'quantity': 1.0,
            'price_unit': total_amount,
            'debit': 0.0,
            'credit': total_amount,
            'account_id': self.company_id.withholding_tax_control_account_id.id,
            'tax_ids': False,
            'is_withhold_line': True,
        }))

        # Balance line with partner account (debit)
        withhold_vals.append(Command.create({
            'quantity': 1.0,
            'debit': tax_amount,
            'price_unit': tax_amount,
            'credit': 0.0,
            'account_id': self.partner_id.property_account_payable_id.id,
            'tax_ids': False,
            'is_withhold_line': True,
        }))

        withhold_vals.append(Command.create({
            'quantity': 1.0,
            'debit': 0.0,
            'price_unit': tax_amount,
            'credit': tax_amount,
            'account_id': tax_account.id,
            'tax_ids': False,
            'is_withhold_line': True,
        }))

        move_vals['line_ids'] += withhold_vals
        return move_vals
