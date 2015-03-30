# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

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

# TODO : multicurrency

class account_payment_method(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)


class account_register_payments(models.TransientModel):
    _name = "account.register.payments"
    _description = "Register payments on multiple invoices"

    amount = fields.Float(string='Payment Amount', required=True, digits=0, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')])
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Bank Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
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
        rec = super(account_register_payments, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Programmation error: wizard action executed without active_model or active_ids in context."))
        if active_model != 'account.invoice':
            raise UserError(_("Programmation error: the expected model for this action is 'account.invoice'. The provided one is '%d'." % active_model))

        # Checks on received invoice records
        invoices = self.env[active_model].browse(active_ids)
        if any(invoice.state != 'open' for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices"))
        if any(inv.partner_id != invoices[0].partner_id for inv in invoices):
            raise UserError(_("In order to pay multiple invoices at once, they must belong to the same partner."))
        if any(MAP_INVOICE_TYPE_PARTNER_TYPE[inv.type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type] for inv in invoices):
            raise UserError(_("You cannot mix customer and supplier invoices in a single payment."))
        if any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            raise UserError(_("In order to pay multiple invoices at once, they must use the same currency."))

        total_amount = sum(inv.residual * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.type] for inv in invoices)
        rec.update({
            'amount': abs(total_amount),
            'currency_id': invoices[0].currency_id.id,
            # TOCHECK: what if the amount actually is 0 ?
            'payment_type': total_amount > 0 and 'inbound' or 'outbound',
            'partner_id': invoices[0].partner_id.id,
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
        })
        return rec

    @api.multi
    def button_register_payments(self):
        invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))
        payment = self.env['account.payment'].create({
            'journal_id': self.journal_id.id,
            'payment_method': self.payment_method.id,
            'date': self.date,
            'invoice_ids': [(4, inv.id, None) for inv in invoices],
            'payment_type': self.payment_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_type': self.partner_type,
        })
        payment.post()


class account_payment(models.Model):
    _name = "account.payment"
    _description = "Payments"

    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.invoice_ids:
            self.destination_account_id = self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            if not self.company_id.transfer_account_id.id:
                raise UserError(_('Transfer account not defined on the company.'))
            self.destination_account_id = self.company_id.transfer_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.property_account_receivable.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable.id

    @api.one
    @api.depends('invoice_ids', 'amount', 'date', 'currency_id')
    def _compute_payment_difference(self):
        if len(self.invoice_ids) != 1:
            self.payment_difference = 0
            return
        if self.invoice_ids[0].currency_id == self.currency_id:
            amount = self.amount
        else:
            amount = self.currency_id.with_context(date=self.date).compute(self.amount, self.invoice_ids[0].currency_id)
        self.payment_difference = self.invoice_ids[0].residual - amount

    name = fields.Char(readonly=True, copy=False)
    state = fields.Selection([('draft','Draft'), ('confirmed','Confirmed')], readonly=True, default='draft', copy=False)

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Transfer Money')], default='outbound', required=True)
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    payment_state = fields.Selection([('todo', 'To Process'), ('done', 'Processed'), ('failed', 'Failed')], required=True, default="todo", copy=False)
    payment_reference = fields.Char(copy=False, readonly=True, help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], default='supplier')
    partner_id = fields.Many2one('res.partner', string='Partner')

    amount = fields.Float(string='Amount', required=True, digits=0)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    reference = fields.Char('Ref', help="Transaction reference number.")
    journal_id = fields.Many2one('account.journal', string='Bank Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', required=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    invoice_ids = fields.Many2many('account.invoice', 'account_invoice_payment_rel', 'payment_id', 'invoice_id', string="Invoices", readonly=True)
    payment_difference = fields.Float(compute='_compute_payment_difference')
    payment_difference_handling = fields.Selection([('open', 'Keep Open'), ('reconcile', 'Reconcile Payment Balance')], default='open', string="Payment Difference", copy=False)
    writeoff_account = fields.Many2one('account.account', string="Counterpart Account", domain=[('deprecated', '=', False)], copy=False)

    move_line_ids = fields.One2many('account.move.line', 'payment_id', readonly=True, ondelete='restrict')

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
        res = self._onchange_journal()
        if not res.get('domain', {}):
            res['domain'] = {}
        res['domain']['journal_id'] = self.payment_type == 'inbound' and [('at_least_one_inbound', '=', True)] or [('at_least_one_outbound', '=', True)]
        res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        return res

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
        return {}

    @api.onchange('invoice_ids')
    def _onchange_invoice(self):
        if len(self.invoice_ids) == 1:
            self.amount = self.invoice_ids[0].residual
            self.currency_id = self.invoice_ids[0].currency_id
            self.payment_type = self.amount < 0 and 'inbound' or 'outbound'
            self.partner_type = MAP_INVOICE_TYPE_PARTNER_TYPE[self.invoice_ids[0].type]
            self.partner_id = self.invoice_ids[0].partner_id

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

        vals['name'] = sequence.with_context(ir_sequence_date=vals['date']).next_by_id()
        return super(account_payment, self).create(vals)

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
    def cancel(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
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

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, create a payment journal entry for each invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            if rec.invoice_ids:
                if len(rec.invoice_ids) == 1:
                    amount = -rec.amount * MAP_INVOICE_TYPE_PAYMENT_SIGN[rec.invoice_ids[0].type]
                    counterpart_aml = rec._create_payment_entry(amount, rec.invoice_ids[0])
                    if rec.payment_difference != 0.0 and rec.payment_difference_handling == 'reconcile':
                        rec.invoice_ids[0].register_payment(counterpart_aml, rec.writeoff_account, rec.journal_id)
                    else:
                        rec.invoice_ids[0].register_payment(counterpart_aml)
                else:
                    for invoice in rec.invoice_ids:
                        amount = -invoice.residual * MAP_INVOICE_TYPE_PAYMENT_SIGN[invoice.type]
                        counterpart_aml = rec._create_payment_entry(amount, invoice)
                        invoice.register_payment(counterpart_aml)
            else:
                counterpart_aml = rec._create_payment_entry(amount)
                # In case of a transfer, the first journal entry created debited the source liquidity account and credited
                # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
                if rec.payment_type == 'transfer':
                    transfer_debit_aml = rec._create_transfer_entry(-amount)
                    (counterpart_aml + transfer_debit_aml).reconcile()

            rec.state = 'confirmed'
            if rec.payment_method.code == 'manual':
                rec.payment_state = 'done'

    def _create_payment_entry(self, amount, invoice_id=False):
        """ Create a journal entry corresponding to a payment, return the reconciliable move line
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency = aml_obj.with_context(date=self.date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, invoice_id)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals())
        aml_obj.create(liquidity_aml_dict)

        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, invoice_id)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(invoice_id))
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        move.post()
        return counterpart_aml

    def _create_transfer_entry(self, amount):
        """ Create the journal entry corresponding to the 'incoming money' part of an internal transfer, return the reconciliable move line
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency = aml_obj.with_context(date=self.date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
        amount_currency = self.destination_journal_id.currency and self.currency_id.with_context(date=self.date).compute(amount, self.destination_journal_id.currency) or 0

        dst_move = self.env['account.move'].create(self._get_move_vals(self.destination_journal_id))

        dst_liquidity_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
        dst_liquidity_aml_dict.update({
            'name': _('Transfer from %s') % self.journal_id.name,
            'account_id': self.destination_journal_id.default_credit_account_id.id,
            'currency_id': self.destination_journal_id.currency.id,
            'payment_id': self.id,
            'journal_id': self.destination_journal_id.id})
        aml_obj.create(dst_liquidity_aml_dict)

        transfer_debit_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, dst_move.id)
        transfer_debit_aml_dict.update({
            'name': '/',
            'payment_id': self.id,
            'account_id': self.company_id.transfer_account_id.id,
            'currency_id': self.destination_journal_id.currency.id,
            'journal_id': self.destination_journal_id.id})
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
        name = journal.with_context(ir_sequence_date=self.date).sequence_id.next_by_id()
        return {
            'name': name,
            'date': self.date,
            'ref': self.reference or name,
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
        """
        return {
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.partner_id.commercial_partner_id.id or False,
            'date': self.date,
            'invoice': invoice_id and invoice_id.id or False,
            'move_id': move_id,
            'debit': debit,
            'credit': credit,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'amount_currency': amount_currency or False,
        }

    def _get_counterpart_move_line_vals(self, invoice_id=False):
        return {
            'name': invoice_id and invoice_id.number or '/',
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
            'account_id': self.payment_type in ('outbound','transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
            'payment_id': self.id,
            'journal_id': self.journal_id.id,
        }
