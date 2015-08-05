# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError
from openerp.tools import float_compare

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}

class AccountPaymentMethod(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)


class AccountPaymentInvoiceAllocation(models.Model):
    _name = "account.payment.invoice.allocation"
    _description = "Allocation of a payment on an invoice"
    _order = "invoice_date_due asc"

    payment_id = fields.Many2one('account.payment', string='Payment', required=True, readonly=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=True, readonly=True, ondelete='restrict')
    amount = fields.Monetary(string='Allocation', required=True)

    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id')
    invoice_residual = fields.Monetary('Open Balance', compute='_compute_invoice_residual')
    # Note: this field is stored because it is used for sorting (which is implemented SQL-side)
    invoice_date_due = date_due = fields.Date(related='invoice_id.date_due', store=True)

    @api.one
    @api.depends('currency_id', 'payment_id.payment_date')
    def _compute_invoice_residual(self):
        """ Returns the residual of the invoice expressed in the payment's currency """
        inv_residual = self.invoice_id.residual * (self.invoice_id.type in ('in_refund', 'out_refund') and -1 or 1)
        company_currency = self.invoice_id.company_id.currency_id
        if self.payment_id.currency_id == company_currency:
            self.invoice_residual = inv_residual
        else:
            self.invoice_residual = company_currency.with_context(date=self.payment_id.payment_date).compute(inv_residual, self.payment_id.currency_id)


class AccountPayment(models.Model):
    _name = "account.payment"
    _description = "Payments"
    _order = "payment_date desc, name desc"

    name = fields.Char(readonly=True, copy=False, default="Draft Payment") # The name is attributed upon post()
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled')], readonly=True, default='draft', copy=False, string="Status")
    amount = fields.Monetary(string='Payment Amount', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    amount_readonly = fields.Monetary(related='amount', string='Subtotal') # Hack to use amount twice in different places with attrs invisible
    invoice_allocation_ids = fields.One2many('account.payment.invoice.allocation', 'payment_id', string="Allocation",
        readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id,
        readonly=True, states={'draft': [('readonly', False)]})
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False,
        readonly=True, states={'draft': [('readonly', False)]})
    communication = fields.Char(string='Memo',
        readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, domain=[('type', 'in', ('bank', 'cash'))],
        default=lambda self: next(iter(self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))])), False),
        readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True, store=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')],
        readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner',
        readonly=True, states={'draft': [('readonly', False)]})

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Internal Transfer')], string='Payment Type',
        required=True, readonly=True, states={'draft': [('readonly', False)]})
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Type', required=True, oldname="payment_method",
        readonly=True, states={'draft': [('readonly', False)]})
    payment_reference = fields.Char(copy=False, readonly=True, help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")

    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', readonly=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain=[('type', 'in', ('bank', 'cash'))],
        readonly=True, states={'draft': [('readonly', False)]})

    payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True)
    payment_difference_handling = fields.Selection([('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')], default='open', string="Payment Difference", copy=False,
        readonly=True, states={'draft': [('readonly', False)]})
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain=[('deprecated', '=', False)], copy=False,
        readonly=True, states={'draft': [('readonly', False)]})

    invoices_num = fields.Integer(compute="_compute_invoice_ids", help="Technical field used for usablity purposes")
    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method', help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
    payment_method_code = fields.Char(related='payment_method_id.code', help="Technical field used to adapt the interface to the payment type selected.")
    invoice_ids = fields.One2many('account.invoice', compute='_compute_invoice_ids', string="Invoices")
    # FIXME: ondelete='restrict' not working (eg. cancel a bank statement line reconciled with a payment)
    move_line_ids = fields.One2many('account.move.line', 'payment_id', readonly=True, copy=False, ondelete='restrict')

    @api.one
    @api.depends('payment_type', 'journal_id')
    def _compute_hide_payment_method(self):
        if not self.journal_id:
            self.hide_payment_method = True
        else:
            journal_payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            self.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[0].code == 'manual'

    @api.one
    @api.depends('invoice_allocation_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        if self.invoice_allocation_ids:
            self.destination_account_id = self.invoice_allocation_ids[0].invoice_id.account_id.id
        elif self.payment_type == 'transfer':
            self.destination_account_id = self.company_id.transfer_account_id.id
            if not self.destination_account_id:
                raise UserError(_('Transfer account not defined on the company.'))
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.property_account_receivable_id.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable_id.id
            if not self.destination_account_id:
                raise UserError(_('No payable/receivable account configured.'))

    @api.one
    @api.depends('invoice_allocation_ids')
    def _compute_invoice_ids(self):
        self.invoice_ids = self.invoice_allocation_ids.mapped('invoice_id')
        self.invoices_num = len(self.invoice_allocation_ids)

    @api.depends('amount')
    def _compute_payment_difference(self):
        if self.invoice_allocation_ids:
            self.payment_difference = sum(alloc.invoice_residual for alloc in self.invoice_allocation_ids) - self.amount

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0.0:
            raise ValidationError(_('The payment amount must be strictly positive.'))

    @api.onchange('invoice_allocation_ids')
    def _onchange_invoice_allocation_ids(self):
        if self.invoice_allocation_ids:
            self.amount = sum(alloc.amount for alloc in self.invoice_allocation_ids)

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount < 0:
            self.amount = 0;
        total_to_allocate = self.amount
        for alloc in self.invoice_allocation_ids.filtered(lambda r: r.invoice_id.type in ('in_refund', 'out_refund')):
            if float_compare(alloc.amount, alloc.invoice_residual, 4) != 0:
                alloc.amount = alloc.invoice_residual
            total_to_allocate -= alloc.invoice_residual
        for alloc in self.invoice_allocation_ids.filtered(lambda r: r.invoice_id.type in ('in_invoice', 'out_invoice')):
            to_allocate = min(alloc.invoice_residual, total_to_allocate)
            if float_compare(alloc.amount, to_allocate, 4) != 0:
                alloc.amount = to_allocate
            total_to_allocate -= to_allocate

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency_id or self.company_id.currency_id
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            self.payment_method_id = payment_methods and payment_methods[0] or False
            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'
            return {'domain': {'payment_method_id': [('payment_type', '=', payment_type), ('id', 'in', payment_methods.ids)]}}

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Set partner_id domain
        if self.partner_type:
            return {'domain': {'partner_id': [(self.partner_type, '=', True)]}}

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        # Set payment method domain
        return {'domain': {
            'payment_method_id': [('payment_type', '=', self.payment_type)],
            'journal_id': [('type', 'in', ('bank', 'cash'))] + (self.payment_type == 'inbound' \
                and [('at_least_one_inbound', '=', True)] \
                or [('at_least_one_outbound', '=', True)])
            }}

    @api.model
    def default_get(self, fields):
        context = dict(self.env.context or {})
        rec = super(AccountPayment, self).default_get(fields)

        # Registering a payment for 1..n invoice(s)
        if context.get('active_model') == 'account.invoice' and context.get('active_ids'):
            invoices = self.env['account.invoice'].browse(context.get('active_ids'))
            if any(invoice.state != 'open' for invoice in invoices):
                raise UserError(_("You can only register payments for open invoices"))
            if any(inv.partner_id != invoices[0].partner_id for inv in invoices):
                raise UserError(_("In order to pay multiple invoices at once, they must belong to the same partner."))
            if any(MAP_INVOICE_TYPE_PARTNER_TYPE[inv.type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type] for inv in invoices):
                raise UserError(_("You cannot mix customer invoices and vendor bills in a single payment."))
            if any(inv.currency_id != invoices[0].currency_id for inv in invoices):
                raise UserError(_("In order to pay multiple invoices at once, they must use the same currency."))

            total_amount = sum(inv.residual * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.type] for inv in invoices)
            rec.update({
                'communication': ', '.join((inv.reference if inv.type in ('in_invoice', 'in_refund') else inv.number) for inv in invoices),
                'currency_id': invoices[0].currency_id.id,
                'payment_type': total_amount > 0 and 'inbound' or 'outbound',
                'partner_id': invoices[0].partner_id.id,
                'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
                'amount': abs(total_amount),
                'invoice_allocation_ids': [(0, None, {
                    'invoice_id': inv.id,
                    'amount': inv.residual * (inv.type in ('in_refund', 'out_refund') and -1 or 1),
                }) for inv in invoices],
            })

        return rec

    @api.model
    def create(self, vals):
        self._check_communication(vals['payment_method_id'], vals.get('communication', ''))
        if vals.get('invoice_allocation_subtotal'):
            vals['amount'] = vals['invoice_allocation_subtotal']
        return super(AccountPayment, self).create(vals)

    def _check_communication(self, payment_method_id, communication):
        """ This method is to be overwritten by payment type modules. The method body would look like :
            if payment_method_id == self.env.ref('my_module.payment_method_id').id:
                try:
                    communication.decode('ascii')
                except UnicodeError:
                    raise ValidationError(_("The communication cannot contain any special character"))
        """
        pass

    @api.multi
    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_("You can not delete a payment that is already posted"))
        return super(AccountPayment, self).unlink()

    @api.multi
    def cancel(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                move.button_cancel()
                move.unlink()
            rec.state = 'draft'

    @api.multi
    def button_journal_entries(self):
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('payment_id', 'in', self.ids)],
        }

    @api.multi
    def button_invoices(self):
        return {
            'name': _('Paid Invoices'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.invoice',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [x.id for x in self.invoice_ids])],
        }

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because an invoice of the payment is not open !"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence = rec.env.ref('account.sequence_payment_transfer')
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence = rec.env.ref('account.sequence_payment_customer_invoice')
                    if rec.payment_type == 'outbound':
                        sequence = rec.env.ref('account.sequence_payment_customer_refund')
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence = rec.env.ref('account.sequence_payment_supplier_refund')
                    if rec.payment_type == 'outbound':
                        sequence = rec.env.ref('account.sequence_payment_supplier_invoice')
            rec.name = sequence.with_context(ir_sequence_date=rec.payment_date).next_by_id()

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.state = 'posted'

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_id = len(self.invoice_allocation_ids) == 1 and self.invoice_allocation_ids[0].invoice_id or False
        total_debit, total_credit, total_amount_currency = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        if len(self.invoice_allocation_ids) > 1:
            total_amount = 0
            for alloc in self.invoice_allocation_ids:
                # Create a reconciliable journal item
                alloc_amount = alloc.amount * (self.payment_type == 'outbound' and 1 or -1)
                debit = alloc_amount > 0 and alloc_amount or 0
                credit = alloc_amount < 0 and -alloc_amount or 0
                amount_currency = self.currency_id != self.company_id.currency_id and self.company_id.currency_id.with_context(date=self.payment_date).compute(alloc_amount, self.currency_id) or 0
                total_amount = total_amount + debit - credit # Avoid unbalanced journal entry due to rounding error
                counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, alloc.invoice_id)
                counterpart_aml_dict.update(self._get_counterpart_move_line_vals(alloc.invoice_id))
                counterpart_aml_dict.update({'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False})
                counterpart_aml = aml_obj.create(counterpart_aml_dict)
                alloc.invoice_id.register_payment(counterpart_aml)
            total_debit = total_amount > 0 and total_amount or 0
            total_credit = total_amount < 0 and -total_amount or 0
        else:
            # Create reconciliable journal item
            counterpart_aml_dict = self._get_shared_move_line_vals(total_debit, total_credit, total_amount_currency, move.id, invoice_id)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(invoice_id))
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

            # Reconcile it with the invoice if present
            if invoice_id:
                if self.payment_difference_handling == 'reconcile':
                    invoice_id.register_payment(counterpart_aml, self.writeoff_account_id, self.journal_id)
                else:
                    invoice_id.register_payment(counterpart_aml)

        liquidity_aml_dict = self._get_shared_move_line_vals(total_credit, total_debit, -total_amount_currency, move.id, invoice_id)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)

        move.post()
        return move

    def _create_transfer_entry(self, amount):
        """ Create the journal entry corresponding to the 'incoming money' part of an internal transfer, return the reconciliable move line
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
        amount_currency = self.destination_journal_id.currency_id and self.currency_id.with_context(date=self.payment_date).compute(amount, self.destination_journal_id.currency_id) or 0

        dst_move = self.env['account.move'].create(self._get_move_vals(self.destination_journal_id))

        dst_liquidity_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
        dst_liquidity_aml_dict.update({
            'name': _('Transfer from %s') % self.journal_id.name,
            'account_id': self.destination_journal_id.default_credit_account_id.id,
            'currency_id': self.destination_journal_id.currency_id.id,
            'payment_id': self.id,
            'journal_id': self.destination_journal_id.id})
        aml_obj.create(dst_liquidity_aml_dict)

        transfer_debit_aml_dict = self._get_shared_move_line_vals(credit, debit, 0, dst_move.id)
        transfer_debit_aml_dict.update({
            'name': self.name,
            'payment_id': self.id,
            'account_id': self.company_id.transfer_account_id.id,
            'journal_id': self.destination_journal_id.id})
        if self.currency_id != self.company_id.currency_id:
            transfer_debit_aml_dict.update({
                'currency_id': self.currency_id.id,
                'amount_currency': -self.amount,
            })
        transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)
        dst_move.post()
        return transfer_debit_aml

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        return {
            'name': name,
            'date': self.payment_date,
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
        """
        return {
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.partner_id.commercial_partner_id.id or False,
            'invoice_id': invoice_id and invoice_id.id or False,
            'move_id': move_id,
            'debit': debit,
            'credit': credit,
            'amount_currency': amount_currency or False,
        }

    def _get_counterpart_move_line_vals(self, invoice=False):
        if self.payment_type == 'transfer':
            name = self.name
        else:
            name = invoice and invoice.number + ': ' or ''
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    name += _("Customer Payment")
                elif self.payment_type == 'outbound':
                    name += _("Customer Refund")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name += _("Vendor Refund")
                elif self.payment_type == 'outbound':
                    name += _("Vendor Payment")
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
        }

    def _get_liquidity_move_line_vals(self, amount):
        name = self.name
        if self.payment_type == 'transfer':
            name = _('Transfer to %s') % self.destination_journal_id.name
        vals = {
            'name': name,
            'account_id': self.payment_type in ('outbound','transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
            'payment_id': self.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

        # If the journal has a currency specified, the journal item need to be expressed in this currency
        if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
            amount = self.currency_id.with_context(date=self.payment_date).compute(amount, self.journal_id.currency_id)
            debit, credit, amount_currency = self.env['account.move.line'].with_context(date=self.payment_date).compute_amount_fields(amount, self.journal_id.currency_id, self.company_id.currency_id)
            vals.update({
                'amount_currency': amount_currency,
                'currency_id': self.journal_id.currency_id.id,
            })

        return vals
