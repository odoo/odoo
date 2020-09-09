from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class account_payment(models.Model):
    _inherit = "account.payment"

    payment_type = fields.Selection(selection_add=[('depense', 'Dépense')])
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmé'), ('approve', 'Approuvé'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'), ('cancelled', 'Cancelled')])
    cash_id = fields.Many2one('optesis.cash', string='Brouillard de caisse')
    expense_lines = fields.One2many('account.payment.line', 'payment_id', string='Ligne de dépense')
    tax_line_ids = fields.One2many('account.invoice.tax', 'payment_id', string='Tax Lines', oldname='tax_line',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    currency_id = fields.Many2one('res.currency', string='Currency',  default=lambda self: self.env.user.company_id.currency_id)
    amount_untaxed = fields.Monetary(string='Montant HT', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Float(string='Montant de paiement', required=True, compute='_amount_all')


    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.invoice_ids:
            self.destination_account_id = self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            if not self.company_id.transfer_account_id.id:
                raise UserError(_('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
            self.destination_account_id = self.company_id.transfer_account_id.id
        elif self.payment_type == 'depense':
            self.destination_account_id = self.journal_id.default_debit_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.property_account_receivable_id.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable_id.id
        elif self.partner_type == 'customer':
            default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
            self.destination_account_id = default_account.id
        elif self.partner_type == 'supplier':
            default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
            self.destination_account_id = default_account.id
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.expense_lines:
            if not line.account_id:
                continue
            price_unit = line.price_unit 
            taxes = line.taxes_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped

    def _prepare_tax_line_vals(self, line, tax):
        """ Prepare values to create an account.invoice.tax line

        The line parameter is an account.invoice.line, and the
        tax parameter is the output of account.tax.compute_all().
        """
        vals = {
            'invoice_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] or False,
            'account_id': (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
            'analytic_tag_ids': tax['analytic'] and line.analytic_tag_ids.ids or False,
        }

        # If the taxes generate moves on the same financial account as the invoice line,
        # propagate the analytic account from the invoice line to the tax line.
        # This is necessary in situations were (part of) the taxes cannot be reclaimed,
        # to ensure the tax move is allocated to the proper analytic account.
    
        return vals

    @api.onchange('expense_lines')
    def _onchange_expense_lines(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.filtered('manual')
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return

    @api.onchange('cash_id')
    def _onchange_cash_id(self):
        if self.cash_id:
            self.journal_id = self.cash_id.journal_id.id


    @api.multi
    @api.depends('expense_lines.price_subtotal')
    def _amount_all(self):
        for rec in self:
            amount_untaxed = amount_tax = 0.0
            for line in rec.expense_lines:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            rec.update({
                'amount_untaxed': rec.currency_id.round(amount_untaxed),
                'amount_tax': rec.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'amount': amount_untaxed + amount_tax,
            })
    
    @api.multi
    def create_cash_line(self):
        for rec in self:
            cash_line = self.env['optesis.cash.line']

            if rec.payment_type == 'outbound':
               cash_amount = -rec.amount
            if rec.payment_type == 'inbound':
                cash_amount = rec.amount   
            if rec.payment_type == 'depense':
                cash_amount = -rec.amount
            if rec.payment_type == 'transfer' and rec.destination_journal_id.type == 'cash':
                cash_amount = rec.amount
            if rec.payment_type == 'transfer' and rec.journal_id.type == 'cash':
                cash_amount = -rec.amount

            vals = {
                'payment_date': rec.payment_date,
                'communication': rec.communication,
                'partner_id': rec.partner_id.id,
                'name': rec.name,
                'cash_amount': cash_amount,
                'cash_id': rec.cash_id.id,
            }

            cash_line.create(vals)
        return True


    @api.multi
    def action_confirm(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            rec.write({'state': 'confirm'})
        return True

    
    @api.multi
    def action_approve(self):
        for rec in self:
            self.create_cash_line()
            rec.write({'state': 'approve'})
        return True

    @api.multi
    def action_reject(self):
        for rec in self:
            rec.write({'state': 'draft'})
        return True
    
    @api.multi
    def action_post(self):
        for rec in self:

            if rec.state != 'approve':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                    
                if rec.payment_type == 'depense':
                    sequence_code = 'account.payment.expense'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            # Create the journal entry
            if rec.payment_type == 'depense':
                move = rec._create_expense_entry(rec.expense_lines, rec.tax_line_ids)
            else:
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name}) 
        return True
    
    def _create_expense_entry(self, expense_lines, tax_line_ids):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        move = self.env['account.move'].create(self._get_move_vals())
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)

        debit_counterpart, credit_counterpart, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(self.amount_total, self.currency_id, self.company_id.currency_id)

        for line in expense_lines:
            debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(line.price_subtotal, self.currency_id, self.company_id.currency_id)
            #Write line corresponding to invoice payment
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            counterpart_aml_dict.update({'name': line.name, 'currency_id': currency_id, 'account_id': line.account_id.id, 'analytic_account_id': line.account_analytic_id.id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

            #Reconcile with the invoices
            if self.payment_difference_handling == 'reconcile' and self.payment_difference:
                writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(line.price_subtotal, line.currency_id, line.company_id.currency_id)
                writeoff_line['name'] = line.name
                writeoff_line['account_id'] = line.account_id.id
                writeoff_line['analytic_account_id'] = line.account_analytic_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = aml_obj.create(writeoff_line)
                if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
        
        for tax in tax_line_ids:
            debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(tax.amount, self.currency_id, self.company_id.currency_id)
            #Write line corresponding to invoice payment
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            counterpart_aml_dict.update({'name': tax.name, 'currency_id': currency_id, 'account_id': tax.account_id.id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

            #Reconcile with the invoices
            if self.payment_difference_handling == 'reconcile' and self.payment_difference:
                writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(tax.amount, tax.currency_id, tax.company_id.currency_id)
                writeoff_line['name'] = tax.name
                writeoff_line['account_id'] = tax.account_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = aml_obj.create(writeoff_line)
                if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
        

        #Write counterpart lines
        if not self.currency_id.is_zero(self.amount_total):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0

            liquidity_aml_dict = self._get_shared_move_line_vals(credit_counterpart, debit_counterpart, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-self.amount_total))
            aml_obj.create(liquidity_aml_dict)

        #validate the payment
        if not self.journal_id.post_at_bank_rec:
            move.post()

        #reconcile the invoice receivable/payable line(s) with the payment
        if self.invoice_ids:
            self.invoice_ids.register_payment(counterpart_aml)

        return move
    

class account_payment_line(models.Model):
    _name = "account.payment.line"
    _description = "Ligne de paiements"

    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Article', ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Compte',  help="The income or expense account related to the selected product.")
    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique')
    quantity = fields.Float(string='Quantite', required=True, default=1)
    price_unit = fields.Float(string='Prix unitaire', required=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous total', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',  default=lambda self: self.env.user.company_id.currency_id)
    payment_id = fields.Many2one('account.payment')
    company_id = fields.Many2one('res.company', string='Société',  default=lambda self: self.env.user.company_id)

    @api.depends('quantity', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(line.price_unit, line.currency_id, line.quantity, product=line.product_id, partner=line.payment_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


    @api.onchange("product_id")
    def onchange_product(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.name
                line.account_id =  line.product_id.property_account_expense_id or line.product_id.categ_id.property_account_expense_categ_id
                line.taxes_id = [(6, 0, [taxe.id for taxe in line.product_id.supplier_taxes_id])]


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    payment_id = fields.Many2one('account.payment', string='Paiement', ondelete='cascade', index=True)