# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

# TODO: multicurrency and multicompany

class account_payment_method(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True)
    code = fields.Char(required=True) # For internal identification
    type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)


class account_register_payments(models.TransientModel):
    _name = "account.register.payments"
    _description = "Register payments on multiple invoices"

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')])
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    hide_payment_method = fields.Boolean(default=True, copy=False)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
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
                'date': self.date,
                'invoice_id': invoice.id,
                'payment_type': self.payment_type,
                'amount': invoice.residual,
                'partner_id': invoice.partner_id.id,
            })


class account_payment(models.Model):
    _name = "account.payment"
    _description = "Payments"

    @api.one
    @api.depends('invoice_id', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.invoice_id:
            self.destination_account_id = self.invoice_id.account_id.id
        elif self.payment_type == 'transfer':
            self.destination_account_id = self.env.user.company_id.transfer_account.id
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
    state = fields.Selection([('draft','Draft'), ('confirmed','Confirmed')], readonly=True, default='draft')

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Transfer Money')], default='outbound', required=True)
    payment_method = fields.Many2one('account.payment.method', string='Payment Method', required=True)
    # default True to prevent a visual glitch
    hide_payment_method = fields.Boolean(default=True, copy=False)
    payment_state = fields.Selection([('todo', 'To Process'), ('done', 'Processed'), ('failed', 'Failed')], required=True, default="todo")

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], default='supplier')
    partner_id = fields.Many2one('res.partner', string='Partner')

    amount = fields.Float(string='Amount', required=True, digits=0)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    reference = fields.Char('Ref', help="Transaction reference number.")
    journal_id = fields.Many2one('account.journal', string='Cash / Bank Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', required=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    invoice_id = fields.Many2one('account.invoice', string="Invoice", domain=[('state', '=', 'open')])
    payment_difference = fields.Float(compute='_compute_payment_difference')
    payment_difference_handling = fields.Selection([('open', 'Keep Open'), ('reconcile', 'Reconcile Payment Balance')], default='open', string="Payment Difference")
    writeoff_account = fields.Many2one('account.account', string="Counterpart Account", domain=[('deprecated', '=', False)])

    move_lines = fields.One2many('account.move.line', 'payment_id', copy=False, readonly=True, ondelete='restrict')

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        if self.amount == 0.0:
            raise ValidationError('Please enter payment amount.')
        if self.amount < 0.0:
            raise ValidationError('The payment amount must always be positive.')
        if self.invoice_id and self.amount > self.invoice_id.residual:
            raise ValidationError('The amount cannot be greater than the residual amount of the invoice.')

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Check partner type isn't contradictory with invoice type, if so remove the invoice
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
        if self.payment_type == 'inbound':
            self.partner_type = 'customer'
        elif self.payment_type == 'outbound':
            self.partner_type = 'supplier'
        # Set payment method domain
        return self._onchange_journal()

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        if self.invoice_id:
            self.amount = self.invoice_id.residual
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
            # payment_type and partner_type will be set by _onchange_invoice. Otherwise, _onchange_invoice()
            # might be called after _onchange_partner_type() or _onchange_payment_type(), which set
            # self.invoice_id = False resulting in a buggy behaviour.
            res.pop('payment_type', None)
            res.pop('partner_type', None)
        return res

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal ' + journal.name + ' does not have a sequence, please specify one.'))
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal ' + journal.name + ' is deactivated.'))
        name = journal.sequence_id.next_by_id()
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
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.partner_id.id or False, # TOCHECK .commercial_partner_id.id ?
            'date': self.date,
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
            'payment_id': self.id,
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
                or self.journal_id.default_credit_account_id.id,
            'journal_id': self.journal_id.id,
        }

    @api.model
    def create(self, vals):
        # TODO: all this logic is managed by the onchanges, there should be a way to have the same behavious server-side and client-side
        invoice_id = self.env['account.invoice'].browse(vals['invoice_id'])
        if not 'amount' in vals:
            vals['amount'] = invoice_id.residual
        if not 'payment_type' in vals:
            vals['payment_type'] = invoice_id.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        if not 'partner_type' in vals:
            vals['partner_type'] = invoice_id.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier'
        if not 'partner_id' in vals:
            vals['partner_id'] = invoice_id.partner_id.id
        if not 'payment_method' in vals:
            journal_id = self.env['account.journal'].browse(vals['journal_id'])
            payment_methods = vals['payment_type'] == 'inbound' and journal_id.inbound_payment_methods or journal_id.outbound_payment_methods
            if payment_methods:
                vals['payment_method'] = payment_methods[0].id
            else:
                # TODO
                raise UserError(_('No %s payment method enabled on journal %s') % vals['payment_type'], journal_id.name)

        # Use the right sequence to get the name and create the record
        if self.payment_type == 'transfer':
            sequence = 'sequence_payment_transfer'
        else:
            seqs = [['sequence_payment_supplier_invoice', 'sequence_payment_supplier_refund'],
                    ['sequence_payment_customer_refund', 'sequence_payment_customer_invoice']]
            sequence = seqs[bool(vals['partner_type'] == 'customer')][bool(vals['payment_type'] == 'inbound')]
        vals['name'] = self.env.ref('account.'+sequence).with_context(ir_sequence_date=self.date).next_by_id()

        return super(account_payment, self).create(vals)

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If an invoice is specified, it is reconciled with the payment.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        aml_obj = self.env['account.move.line']
        for res in self:
            # Prepare values
            amount = res.amount * (res.payment_type == 'outbound' and 1 or -1)
            from_cur = res.journal_id.currency
            to_cur = res.company_id.currency_id # TODO : before ir_sequence_date=self.date
            debit, credit, amount_currency = aml_obj.with_context(date=res.date).compute_amount_fields(amount, from_cur, to_cur)

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
                if res.payment_difference != 0.0 and res.payment_difference_handling == 'reconcile':
                    res.invoice_id.register_payment(counterpart_aml, res.writeoff_account, res.journal_id)
                else:
                    res.invoice_id.register_payment(counterpart_aml)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if res.payment_type == 'transfer':
                dst_move = res.env['account.move'].create(res._get_move_vals(res.destination_journal_id))
                transfer_debit_aml_dict = res._get_shared_move_line_vals(credit, debit, -amount_currency, dst_move.id)
                transfer_debit_aml_dict.update({
                    'name': 'TODO',
                    'payment_id': res.id,
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
            if res.payment_method.code == 'manual':
                res.payment_state = 'done'

    @api.multi
    def button_create_and_post(self):
        # When you click a button, the record is created before the button's method is called.
        # In action_account_invoice_payment, there is no 'Create' button, so we simulate it with this hack.
        for rec in self:
            try:
                with self._cr.savepoint():
                    rec.post()
            except Exception:
                # If an error occurs in post(), the payment must be deleted.
                # We use an explicit rollback to revert ORM operations done in post()
                # then invalidate affected caches, delete the record and propagate the exception
                self.invalidate_cache()
                self.env['account.move'].invalidate_cache()
                self.env['account.move.line'].invalidate_cache()

                rec.unlink()
                self._cr.commit()
                raise

    @api.multi
    def unlink(self):
        for rec in self:
            moves = rec.move_lines.mapped('move_id')
            for move in moves:
                if rec.invoice_id:
                    move.line_id.remove_move_reconcile()
                move.button_cancel()
                move.unlink()
        return super(account_payment, self).unlink()
