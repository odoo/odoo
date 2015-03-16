# -*- coding: utf-8 -*-

import time

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

'''
Thing that don't work :
    - pay more than invoice amount
    - domain on journal_id via onchange to hide journals with no payment method corresponding to the payment type
    - close wizard if warning: use a server action that throws warning or open wizard action ?

Thing that may be not far from working:
    - domains set via onchanges for the form view consistency
    - multicurrency (check with transfer use cases)
'''

class account_payment_method(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True)
    code = fields.Char(required=True) # For internal identification
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)


class account_register_payments(models.TransientModel):
    _name = "account.register.payments"
    _description = "Register payments on multiple invoices"

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')])
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Bank Journal', required=True, domain=[('type', '=', 'bank')])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type:
            return {'domain': {'payment_method': [('payment_type', '=', self.payment_type)]}}

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_methods or self.journal_id.outbound_payment_methods
            self.payment_method = payment_methods and payment_methods[0] or False

    @api.model
    def default_get(self, fields):
        # TODO: return action False to close dialog if error
        rec = super(account_register_payments, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        if not active_model or not active_ids:
            raise osv.except_osv(_("Programmation error : wizard action executed without active_model or active_ids in context."))
        if active_model != 'account.invoice':
            raise osv.except_osv(_("Programmation error : the expected model for this action is 'account.invoice'. The provided one is '%d'." % active_model))
        records = self.env[active_model].browse(active_ids)
        if any(invoice.state != 'open' for invoice in records):
            raise UserError(_("You can only register payments for open invoices"))
        if len(set(r.type for r in records)) > 1:
            raise UserError(_("You can only register batch payments for invoices of the same type."))

        rec.update({
            'payment_type': records[0].type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound',
        })
        return rec

    @api.multi
    def button_register_payments(self):
        for invoice in self.env['account.invoice'].browse(self._context.get('active_ids')):
            payment = self.env['account.payment'].create({
                'journal_id': self.journal_id.id,
                'payment_method': self.payment_method.id,
                'date': self.date,
                'invoice_id': invoice.id,
                'payment_type': self.payment_type,
                'amount': invoice.residual,
                'partner_id': invoice.partner_id.id,
                'partner_type': invoice.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'
            })
            payment.post()


class account_payment(models.Model):
    _name = "account.payment"
    _description = "Payments"

    @api.one
    @api.depends('invoice_id', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.invoice_id:
            self.destination_account_id = self.invoice_id.account_id.id
        elif self.payment_type == 'transfer':
            self.destination_account_id = self.env.user.company_id.transfer_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.property_account_receivable.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable.id

    @api.one
    @api.depends('invoice_id', 'amount')
    def _compute_payment_difference(self):
        self.payment_difference = self.invoice_id and self.invoice_id.residual - self.amount or 0

    name = fields.Char(readonly=True, copy=False)
    state = fields.Selection([('draft','Draft'), ('confirmed','Confirmed')], readonly=True, default='draft', copy=False)

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Transfer Money')], default='outbound', required=True)
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    payment_state = fields.Selection([('todo', 'To Process'), ('done', 'Processed'), ('failed', 'Failed')], required=True, default="todo", copy=False)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], default='supplier')
    partner_id = fields.Many2one('res.partner', string='Partner')

    amount = fields.Float(string='Amount', required=True, digits=0)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    reference = fields.Char('Ref', help="Transaction reference number.")
    journal_id = fields.Many2one('account.journal', string='Bank Journal', required=True, domain=[('type', '=', 'bank')])
    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', required=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain=[('type', '=', 'bank')])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    invoice_id = fields.Many2one('account.invoice', string="Invoice", domain=[('state', '=', 'open')], default=lambda self: self._context.get('invoice_id'), copy=False)
    payment_difference = fields.Float(compute='_compute_payment_difference')
    payment_difference_handling = fields.Selection([('open', 'Keep Open'), ('reconcile', 'Reconcile Payment Balance')], default='open', string="Payment Difference", copy=False)
    writeoff_account = fields.Many2one('account.account', string="Counterpart Account", domain=[('deprecated', '=', False)], copy=False)

    move_lines = fields.One2many('account.move.line', 'payment_id', copy=False, readonly=True, ondelete='restrict')

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0.0:
            raise ValidationError('The payment amount must be strictly positive.')

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Set partner_id domain
        if self.partner_type:
            return {'domain': {'partner_id': [(self.partner_type, '=', True)]}}

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        # Set default partner type for the payment type
        if self.payment_type == 'inbound':
            self.partner_type = 'customer'
        elif self.payment_type == 'outbound':
            self.partner_type = 'supplier'
        # Set payment method domain
        # TODO: set journal_id domain in order to hide journal with no inbound/outbound payment method
        return self._onchange_journal()

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency and self.journal_id.currency or self.company_id.currency_id
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_methods or self.journal_id.outbound_payment_methods
            self.payment_method = payment_methods and payment_methods[0] or False
            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'
            return {'domain': {'payment_method': [('payment_type', '=', payment_type), ('id', 'in', payment_methods.ids)]}}

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        if self.invoice_id:
            self.amount = self.invoice_id.residual
            self.currency_id = self.invoice_id.currency_id
            self.payment_type = self.invoice_id.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            self.partner_type = self.invoice_id.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'
            self.partner_id = self.invoice_id.partner_id

    @api.model
    def create(self, vals):
        # Use the right sequence to get the name and create the record
        if vals['payment_type'] == 'transfer':
            sequence = self.env.ref('account.sequence_payment_transfer')
        else:
            if vals['partner_type'] == 'customer':
                if vals['payment_type'] == 'inbound':
                    sequence = self.env.ref('account.sequence_payment_customer_invoice')
                if vals['payment_type'] == 'outbound':
                    sequence = self.env.ref('account.sequence_payment_customer_refund')
            if vals['partner_type'] == 'supplier':
                if vals['payment_type'] == 'inbound':
                    sequence = self.env.ref('account.sequence_payment_supplier_refund')
                if vals['payment_type'] == 'outbound':
                    sequence = self.env.ref('account.sequence_payment_supplier_invoice')

        date_str = isinstance(vals['date'], str) and vals['date'] or fields.Date.to_string(vals['date'])
        vals['name'] = sequence.with_context(ir_sequence_date=date_str).next_by_id()
        return super(account_payment, self).create(vals)

    @api.multi
    def cancel(self):
        for rec in self:
            moves = rec.move_lines.mapped('move_id')
            for move in moves:
                if rec.invoice_id:
                    move.line_id.remove_move_reconcile()
                move.button_cancel()
                move.unlink()
            rec.state = 'draft'
            rec.payment_state = 'todo'

    @api.multi
    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_("In order to delete a payment, it must first be canceled."))
        return super(account_payment, self).unlink()

# Warning: below this point lies crappy that code that generates journal entries and craves refactoring

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If an invoice is specified, it is reconciled with the payment.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        for rec in self:
            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            debit, credit, amount_currency = aml_obj.compute_amount_fields(amount, rec.currency_id, rec.company_id.currency_id, rec.date)

            move = rec.env['account.move'].create(rec._get_move_vals())

            liquidity_aml_dict = rec._get_shared_move_line_vals(credit, debit, -amount_currency, move.id)
            liquidity_aml_dict.update(rec._get_liquidity_move_line_vals())
            aml_obj.create(liquidity_aml_dict)

            counterpart_aml_dict = rec._get_shared_move_line_vals(debit, credit, amount_currency, move.id)
            counterpart_aml_dict.update(rec._get_counterpart_move_line_vals())
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

            move.post()

            # Reconcile the invoice, if present
            if rec.invoice_id:
                if rec.payment_difference != 0.0 and rec.payment_difference_handling == 'reconcile':
                    rec.invoice_id.register_payment(counterpart_aml, rec.writeoff_account, rec.journal_id)
                else:
                    rec.invoice_id.register_payment(counterpart_aml)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                debit, credit, amount_currency = aml_obj.compute_amount_fields(-amount, rec.destination_journal_id.currency, rec.currency_id, rec.date)

                dst_move = rec.env['account.move'].create(rec._get_move_vals(rec.destination_journal_id))

                dst_liquidity_aml_dict = rec._get_shared_move_line_vals(credit, debit, -amount_currency, dst_move.id)
                dst_liquidity_aml_dict.update({
                    'name': _('Transfer from %s') % self.journal_id.name,
                    'account_id': rec.destination_journal_id.default_credit_account_id.id,
                    'currency_id': rec.destination_journal_id.currency.id,
                    'journal_id': rec.destination_journal_id.id })
                aml_obj.create(dst_liquidity_aml_dict)

                transfer_debit_aml_dict = rec._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
                transfer_debit_aml_dict.update({
                    'name': '/',
                    'payment_id': rec.id,
                    'account_id': rec.env.user.company_id.transfer_account_id.id,
                    'currency_id': rec.destination_journal_id.currency.id,
                    'journal_id': rec.destination_journal_id.id })
                transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)

                dst_move.post()

                (counterpart_aml + transfer_debit_aml).reconcile()

            rec.state = 'confirmed'
            if rec.payment_method.code == 'manual':
                rec.payment_state = 'done'

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = journal.with_context(ir_sequence_date=self.date).sequence_id.next_by_id()
        return {
            'name': name,
            'date': self.date,
            'ref': self.reference or name,
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }


    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id):
        """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed) """
        return {
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.partner_id.commercial_partner_id.id or False,
            'date': self.date,
            'invoice': self.invoice_id and self.invoice_id.id or False,
            'move_id': move_id,
            'debit': debit,
            'credit': credit,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'amount_currency': amount_currency or False,
        }

    def _get_counterpart_move_line_vals(self):
        return {
            'name': self.invoice_id and self.invoice_id.number or '/',
            'account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
            'payment_id': self.id,
        }

    def _get_liquidity_move_line_vals(self):
        if self.payment_type == 'transfer':
            name = _('Transfer to %s') % self.destination_journal_id.name
        else:
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    prefix = _("Payment from ")
                if self.payment_type == 'outbound':
                    prefix = _("Refund to ")
            if self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    prefix = _("Refund from ")
                if self.payment_type == 'outbound':
                    prefix = _("Payment to ")
            name = prefix + self.partner_id.name
        return {
            'name': name,
            'account_id': self.payment_type == 'outbound' \
                and self.journal_id.default_debit_account_id.id \
                or self.journal_id.default_credit_account_id.id,
            'journal_id': self.journal_id.id,
        }
