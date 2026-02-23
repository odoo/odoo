# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, Command


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    apply_withhold_tax = fields.Boolean(
        string='Apply Withholding Tax',
        help="Whether or not to apply withholding taxes on this payment.",
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

    @api.depends('apply_withhold_tax')
    def _compute_outstanding_account_id(self):
        """ Update the computation to reset the account when apply_withhold_tax is unchecked. """
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
        # EXTEND account
        # return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'should_withhold_tax')
        return super()._get_trigger_fields_to_synchronize() + ('apply_withhold_tax', 'withhold_tax_id', 'withhold_base_amount', 'withhold_tax_amount')


    def _prepare_move_withholding_lines(self, default_values):
        # EXTENDS account
        write_off_lines = super()._prepare_move_withholding_lines(default_values)
        if self.apply_withhold_tax and self.withhold_tax_amount:
            write_off_lines = [
                {
                    'quantity': 1.0,
                    'price_unit': self.withhold_base_amount,
                    'debit': self.withhold_base_amount,
                    'credit': 0.0,
                    'account_id': self.company_id.withholding_tax_control_account_id.id,
                    'tax_ids': [Command.set([self.withhold_tax_id.id])],
                    'is_withhold_line': True,
                },
                {
                    'quantity': 1.0,
                    'price_unit': self.withhold_base_amount,
                    'debit': 0.0,
                    'credit': self.withhold_base_amount,
                    'account_id': self.company_id.withholding_tax_control_account_id.id,
                    'tax_ids': False,
                    'is_withhold_line': True,
                },
                {
                    'quantity': 1.0,
                    'debit': self.withhold_tax_amount,
                    'price_unit': self.withhold_tax_amount,
                    'credit': 0.0,
                    'account_id': self.partner_id.property_account_payable_id.id,
                    'tax_ids': False,
                    'is_withhold_line': True,
                },
                {
                    'quantity': 1.0,
                    'debit': 0.0,
                    'price_unit': self.withhold_tax_amount,
                    'credit': self.withhold_tax_amount,
                    'account_id': self.withhold_tax_id.invoice_repartition_line_ids.filtered(lambda r:
                        r.repartition_type == 'tax').account_id.id,
                    'tax_ids': False,
                    'is_withhold_line': True,
                },
            ]
        return write_off_lines
