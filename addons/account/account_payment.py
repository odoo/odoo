# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

# TODO: multicurrency and multicompany

class account_payment_method(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)


class account_register_payments(models.TransientModel):
    _name = "account.register.payments"
    _description = "Register payments on multiple invoices"

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Collect Money')])
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    hide_payment_method = fields.Boolean(default=True, copy=False)
    date_paid = fields.Date(string='Date paid', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Cash / Bank Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type:
            return {'domain': {'payment_method': [('type', '=', self.payment_type)]}}

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_methods or self.journal_id.outbound_payment_methods
            if payment_methods:
                self.payment_method = payment_methods[0]
            # Hide payment method if only 'Manual' is available
            self.hide_payment_method = len(payment_methods) == 1 and payment_methods[0].code == 'manual'

    @api.model
    def default_get(self, fields):
        # TOCHECK: allow to reconcile different type of invoices at once ?
        # TODO: return action False to close dialog if error
        res = super(account_register_payments, self).default_get(fields)
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

        res.update({
            'payment_type': records[0].type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound',
            'partner_type': records[0].type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'
        })
        return res

    @api.multi
    def button_register_payments(self):
        for invoice in self.env['account.invoice'].browse(self._context.get('active_ids')):
            self.env['account.payment'].create({
                'journal_id': self.journal_id.id,
                'payment_method': self.payment_method.id,
                'date_paid': self.date_paid,
                'invoice_id': invoice.id,
                'payment_type': self.payment_type,
                'payment_amount': invoice.residual,
                'partner_id': invoice.partner_id.id,
            })


class account_payment(models.Model):
    _name = "account.payment"
    _description = "Payments"

    @api.one
    @api.depends('invoice_id', 'payment_type', 'partner_type', 'partner_id', 'destination_journal_id')
    def _compute_destination_account_id(self):
        if self.invoice_id:
            self.destination_account_id = self.invoice_id.account_id.id
        elif self.payment_type == 'transfer':
            self.destination_account_id = self.env.user.company_id.transfer_account
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.property_account_receivable.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable.id

    @api.one
    @api.depends('invoice_id', 'payment_amount')
    def _compute_payment_difference(self):
        self.payment_difference = self.invoice_id and self.invoice_id.residual - self.payment_amount or 0

    name = fields.Char(readonly=True, copy=False)
    state = fields.Selection([('draft','Draft'), ('confirmed','Confirmed')], readonly=True, default='draft')

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Transfer Money')], default='outbound', required=True)
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    hide_payment_method = fields.Boolean(default=True, copy=False)
    payment_state = fields.Selection([('todo', 'To Process'), ('done', 'Processed'), ('failed', 'Failed')], required=True, default="todo")

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], default='supplier')
    partner_id = fields.Many2one('res.partner', string='Partner')

    payment_amount = fields.Float(string='Amount', required=True, digits=0)
    date_paid = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    reference = fields.Char('Ref', help="Transaction reference number.")
    journal_id = fields.Many2one('account.journal', string='Cash / Bank Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', required=True)
    # For money transfer, the user selects destination_journal_id to determine the destination_account_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    invoice_id = fields.Many2one('account.invoice', string="Invoice", domain=[('state', '=', 'open')])
    payment_difference = fields.Float(compute='_compute_payment_difference')
    payment_difference_handling = fields.Selection([('open', 'Keep Open'), ('reconcile', 'Reconcile Payment Balance')], default='open', string="Payment Difference")
    writeoff_account = fields.Many2one('account.account', string="Counterpart Account", domain=[('deprecated', '=', False)])

    @api.one
    @api.constrains('payment_amount')
    def _check_amount(self):
        if self.payment_amount == 0.0:
            raise ValidationError('Please enter payment amount.')
        if self.payment_amount < 0.0:
            raise ValidationError('The payment amount must always be positive.')
        if self.invoice_id and self.payment_amount > self.invoice_id.residual:
            raise ValidationError('The amount cannot be greater than the residual amount of the invoice.')

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Check payment type isn't contradictory with invoice type, if so remove the invoice
        if self.invoice_id:
            expected_partner_type = self.invoice_id.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'
            if self.partner_type != expected_partner_type:
                self.invoice_id = False
        # Set partner_id domain
        if self.partner_type:
            return {'domain': {'partner_id': [(self.partner_type, '=', True)]}}

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        # Check payment type isn't contradictory with invoice type, if so remove the invoice
        if self.invoice_id:
            expected_payment_type = self.invoice_id.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            if self.payment_type != expected_payment_type:
                self.invoice_id = False
        # Set default partner type for the payment type
        if self.payment_type in ('inbound', 'outbound'):
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        # Set payment method domain
        return self._onchange_journal()

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        if self.invoice_id:
            self.payment_amount = self.invoice_id.residual
            self.payment_type = self.invoice_id.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            self.partner_type = self.invoice_id.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'
            self.partner_id = self.invoice_id.partner_id

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_methods or self.journal_id.outbound_payment_methods
            if payment_methods:
                self.payment_method = payment_methods[0]
            # Hide payment method if only 'Manual' is available
            self.hide_payment_method = len(payment_methods) == 1 and payment_methods[0].code == 'manual'
            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'
            return {'domain': {'payment_method': [('type', '=', payment_type), ('id', 'in', payment_methods.ids)]}}

    @api.model
    def default_get(self, fields):
        # Allows to pass invoice in context
        res = super(account_payment, self).default_get(fields)
        if self._context.get('invoice_id'):
            res.update({'invoice_id': self._context['invoice_id']})
            # Avoid a weird bug with onchange and default values by doing what _onchange_invoice would do
            invoice = self.env['account.invoice'].browse(self._context['invoice_id'])
            res.update({'payment_type': invoice.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'})
            res.update({'partner_type': invoice.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'})
        return res

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal ' + journal.name + ' does not have a sequence, please specify one.'))
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal ' + journal.name + ' is deactivated.'))
        return {
            'name': journal.sequence_id.next_by_id(),
            'date': self.date_paid,
            'ref': self.reference,
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id):
        """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed) """
        return {
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.partner_id.id or False, # TOCHECK .commercial_partner_id.id ?
            'date': self.date_paid,
            'invoice': self.invoice_id and self.invoice_id.id or False,
            'move_id': move_id,
            'debit': debit,
            'credit': credit,
            'currency_id': self.journal_id.currency.id,
            'amount_currency': amount_currency or False,
        }

    def _get_counterpart_move_line_vals(self):
        if self.invoice_id:
            name = self.invoice_id.number or '/'
        else:
            name = 'TODO'
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
        }

    def _get_liquidity_move_line_vals(self):
        if self.payment_type == 'transfer':
            name = 'TODO'
        else:
            prefixes = [["Payment to ", "Refund from "],
                        ["Refund to ", "Payment from "]]
            prefix = prefixes[bool(self.partner_type == 'customer')][bool(self.payment_type == 'inbound')]
            name = prefix + self.partner_id.name
        return {
            'name': name,
            'account_id': self.payment_type == 'outbound' \
                and self.journal_id.default_debit_account_id.id \
                or self.journal_id.default_credit_account_id.id, # TOCHECK
            'journal_id': self.journal_id.id,
            'payment_method': self.payment_method.id,
        }

    @api.model
    def create(self, vals):
        # Use the right sequence to get the name and create the record
        if self.payment_type == 'transfer':
            sequence = 'sequence_payment_transfer'
        else:
            seqs = [['sequence_payment_supplier_invoice', 'sequence_payment_supplier_refund'],
                    ['sequence_payment_customer_refund', 'sequence_payment_customer_invoice']]
            sequence = seqs[bool(vals['partner_type'] == 'customer')][bool(vals['payment_type'] == 'inbound')]
        vals['name'] = self.env.ref('account.'+sequence).with_context(ir_sequence_date=self.date_paid).next_by_id()

        # Make sure everything is consistent
        if self.payment_type == 'transfer':
            self.invoice_id = False

        return super(account_payment, self).create(vals)

    @api.multi
    def post(self):
        """ Create the journal entry for the payment. In an invoice is specified, reconcile it with the payment """
        for res in self:
            # Prepare values
            aml_obj = self.env['account.move.line']
            amount = res.payment_amount * (res.payment_type == 'outbound' and 1 or -1)
            from_cur = res.journal_id.currency
            to_cur = res.company_id.currency_id # TODO : before ir_sequence_date=self.date_paid
            debit, credit, amount_currency = aml_obj.with_context(date=res.date_paid).compute_amount_fields(amount, from_cur, to_cur)

            # Create the journal entry
            move = res.env['account.move'].create(res._get_move_vals())
            liquidity_aml_dict = res._get_shared_move_line_vals(credit, debit, -amount_currency, move.id)
            liquidity_aml_dict.update(res._get_liquidity_move_line_vals())
            liquidity_aml = aml_obj.create(liquidity_aml_dict)
            counterpart_aml_dict = res._get_shared_move_line_vals(debit, credit, amount_currency, move.id)
            counterpart_aml_dict.update(res._get_counterpart_move_line_vals())
            counterpart_aml = aml_obj.create(counterpart_aml_dict)
            move.post()

            # Reconcile the invoice, if present
            if res.invoice_id:
                writeoff_account = res.payment_difference_handling == 'reconcile' and res.writeoff_account or False
                writeoff_journal = res.payment_difference_handling == 'reconcile' and res.journal_id or False
                aml_to_reconcile = res.invoice_id.move_id.line_id.filtered(lambda r: r.account_id.internal_type in ('payable', 'receivable') and not r.reconciled)
                (aml_to_reconcile + counterpart_aml).reconcile(writeoff_account, writeoff_journal)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if res.payment_type == 'transfer':
                dst_move = res.env['account.move'].create(res._get_move_vals(res.destination_journal_id))
                transfer_debit_aml_dict = res._get_shared_move_line_vals(credit, debit, -amount_currency, dst_move.id)
                transfer_debit_aml_dict.update({
                    'name': 'TODO',
                    'account_id': res.env.user.company_id.transfer_account.id,
                    'journal_id': res.destination_journal_id.id })
                transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)
                dst_liquidity_aml_dict = res._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
                dst_liquidity_aml_dict.update({
                    'name': 'TODO',
                    'account_id': res.destination_journal_id.default_credit_account_id.id,
                    'journal_id': res.destination_journal_id.id })
                aml_obj.create(dst_liquidity_aml_dict)
                dst_move.post()

                (counterpart_aml + transfer_debit_aml).reconcile()

            res.state = 'confirmed'
            if res.payment_method == 'manual'
                res.payment_state = 'done'

    @api.multi
    def button_create_and_post(self):
        # When you click a button, the record is created before the button's method is called.
        # In action_account_invoice_payment, there is no 'Create' button, so we simulate it with this hack.
        for rec in self:
            rec.post()

    @api.multi
    def unlink(self):
        for rec in self:
            move = rec.move_line.move_id
            if rec.invoice_id:
                move.line_id.remove_move_reconcile()
            move.button_cancel()
            move.unlink()
        return super(account_payment, self).unlink()
