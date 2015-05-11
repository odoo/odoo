# -*- coding: utf-8 -*-

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.tools import float_is_zero

from openerp.exceptions import UserError, RedirectWarning

import openerp.addons.decimal_precision as dp

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Supplier Bill
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Supplier Refund
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class AccountInvoice(models.Model):
    _name = "account.invoice"
    _inherit = ['mail.thread']
    _description = "Invoice"
    _order = "date_invoice desc, number desc, id desc"

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            amount_total_signed = self.currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = self.currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_signed = amount_total_signed * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    @api.model
    def _default_journal(self):
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id

    @api.model
    @api.returns('account.analytic.journal', lambda r: r.id)
    def _get_journal_analytic(self, inv_type):
        """ Return the analytic journal corresponding to the given invoice type. """
        journal_type = TYPE2JOURNAL.get(inv_type, 'sale')
        journal = self.env['account.analytic.journal'].search([('type', '=', journal_type)], limit=1)
        if not journal:
            raise UserError(_("You must define an analytic journal of type '%s'!") % (journal_type,))
        return journal

    @api.model
    def _get_reference_type(self):
        return [('none', _('Free Reference'))]

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_signed = 0.0
        sign = self.type in ['in_refund', 'in_invoice'] and -1 or 1
        for line in self.sudo().move_id.line_ids:
            if line.account_id.internal_type in ('receivable', 'payable'):
                residual_signed += line.amount_residual * sign
                if line.currency_id == self.currency_id:
                    residual += line.currency_id and line.amount_residual_currency or line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual_signed = residual_signed
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, digits_rounding_precision):
            self.reconciled = True

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('journal_id.type', 'in', ('bank', 'cash')), ('account_id', '=', self.account_id.id), ('partner_id', '=', self.partner_id.id), ('reconciled', '=', False), ('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credit from %s')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debit from %s')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id:
                        amount_to_show = line.currency_id.compute(abs(line.amount_residual_currency), self.currency_id)
                    else:
                        amount_to_show = line.company_id.currency_id.compute(abs(line.amount_residual), self.currency_id)
                    info['content'].append({
                        'ref': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': self.currency_id.symbol,
                        'id': line.id,
                        'position': self.currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment % line.partner_id.name
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.one
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            for payment in self.payment_move_line_ids:
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                elif self.type in ('in_invoice', 'out_refund'):
                    amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                #we don't take into account the movement created due to a change difference
                if payment.currency_id and payment.move_id.rate_diff_partial_rec_id:
                    continue
                # get the payment value in invoice currency
                if payment.currency_id and amount_currency != 0:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = payment.company_id.currency_id.compute(-amount, self.currency_id)
                info['content'].append({
                    'name': payment.name,
                    'ref': payment.journal_id.name,
                    'amount': amount_to_show,
                    'currency': self.currency_id.symbol,
                    'digits': [69, self.currency_id.decimal_places],
                    'position': self.currency_id.position,
                    'date': payment.date,
                })
            self.payments_widget = json.dumps(info)

    @api.one
    @api.depends('move_id.line_ids.amount_residual')
    def _compute_payments(self):
        payment_lines = []
        for line in self.move_id.line_ids:
            payment_lines.extend([rp.credit_move_id.id for rp in line.matched_credit_ids])
            payment_lines.extend([rp.debit_move_id.id for rp in line.matched_debit_ids])
        self.payment_move_line_ids = self.env['account.move.line'].browse(payment_lines).sorted()

    name = fields.Char(string='Reference/Description', index=True,
        readonly=True, states={'draft': [('readonly', False)]}, copy=False, help='The name that will be used on account move lines')
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.",
        readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Bill'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
        ], readonly=True, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')

    number = fields.Char(related='move_id.name', store=True, readonly=True, copy=False)
    move_name = fields.Char(string='Journal Entry', readonly=True,
        default=False, copy=False,
        help="Technical field holding the number given to the invoice, automatically set when the invoice is validated then stored to set the same number again if the invoice is cancelled, set to draft and re-validated.")
    reference = fields.Char(string='Partner\'s Invoice Reference',
        help="The partner reference of this invoice.")
    reference_type = fields.Selection('_get_reference_type', string='Payment Reference',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default='none')
    comment = fields.Text('Additional Information')

    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' when invoice is in Pro-forma status, invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice, an invoice number is generated. Its in open status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    sent = fields.Boolean(readonly=True, default=False, copy=False,
        help="It indicates that the invoice has been sent.")
    date_invoice = fields.Date(string='Invoice Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)
    date_due = fields.Date(string='Due Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True, copy=False,
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. The payment term may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the payment term and the due date empty, it "
             "means direct payment.")
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term',
        readonly=True, states={'draft': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "
             "The payment term may compute several due dates, for example 50% now, 50% in one month.")
    date = fields.Date(string='Accounting Date',
        copy=False,
        help="Keep empty to use the invoice date.",
        readonly=True, states={'draft': [('readonly', False)]})

    account_id = fields.Many2one('account.account', string='Account',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain=[('deprecated', '=', False)], help="The partner account used for this invoice.")
    invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', oldname='invoice_line',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    tax_line_ids = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines', oldname='tax_line',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    move_id = fields.Many2one('account.move', string='Journal Entry',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Journal Items.")

    amount_untaxed = fields.Monetary(string='Untaxed Amount',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount')
    amount_tax = fields.Monetary(string='Tax',
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    amount_total_signed = fields.Monetary(string='Total', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount',
        help="Total amount in the currency of the company, negative for credit notes.")
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    check_total = fields.Monetary(string='Verification Total',
        readonly=True, states={'draft': [('readonly', False)]}, default=0.0)

    reconciled = fields.Boolean(string='Paid/Reconciled', store=True, readonly=True, compute='_compute_residual',
        help="It indicates that the invoice has been paid and the journal entry of the invoice has been reconciled with one or several journal entries of payment.")
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Supplier Refund, otherwise a Partner bank account number.',
        readonly=True, states={'draft': [('readonly', False)]})

    residual = fields.Monetary(string='Amount Due',
        compute='_compute_residual', store=True, help="Remaining amount due.")
    residual_signed = fields.Monetary(string='Amount Due', currency_field='company_currency_id',
        compute='_compute_residual', store=True, help="Remaining amount due in the currency of the company.")
    payment_ids = fields.Many2many('account.payment', 'account_invoice_payment_rel', 'invoice_id', 'payment_id', string="Payments", copy=False, readonly=True)
    payment_move_line_ids = fields.Many2many('account.move.line', string='Payments', compute='_compute_payments')
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
        readonly=True, states={'draft': [('readonly', False)]})
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity',
        related='partner_id.commercial_partner_id', store=True, readonly=True,
        help="The commercial entity that will be used on Journal Entries for this invoice")

    outstanding_credits_debits_widget = fields.Text(compute='_get_outstanding_info_JSON')
    payments_widget = fields.Text(compute='_get_payment_info_JSON')
    has_outstanding = fields.Boolean(compute='_get_outstanding_info_JSON')

    _sql_constraints = [
        ('number_uniq', 'unique(number, company_id, journal_id, type)', 'Invoice Number must be unique per Company!'),
    ]

    @api.model
    def create(self, vals):
        return super(AccountInvoice, self.with_context(mail_create_nolog=True)).create(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        def get_view_id(xid, name):
            try:
                return self.env['ir.model.data'].xmlid_to_res_id('account.' + xid, raise_if_not_found=True)
            except ValueError:
                view = self.env['ir.ui.view'].search([('name', '=', name)], limit=1)
                if not view:
                    return False
                return view.id

        context = self._context
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner = self.env['res.partner'].browse(context['active_ids'])[0]
            if not view_type:
                view_id = get_view_id('invoice_tree', 'account.invoice.tree')
                view_type = 'tree'
            elif view_type == 'form':
                if partner.supplier and not partner.customer:
                    view_id = get_view_id('invoice_supplier_form', 'account.invoice.supplier.form')
                elif partner.customer and not partner.supplier:
                    view_id = get_view_id('invoice_form', 'account.invoice.form')
        return super(AccountInvoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        return self.env['report'].get_action(self, 'account.report_invoice')

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def compute_taxes(self):
        """Function used in other module to compute the taxes on a fresh invoice created (onchanges did not applied)"""
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            # Delete non-manual tax lines
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            self.invalidate_cache()

            # Generate one tax line per tax, however many invoice lines it's applied to
            tax_grouped = invoice.get_taxes_values()

            # Create new tax lines
            for tax in tax_grouped.values():
                account_invoice_tax.create(tax)

        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line_ids': []})

    @api.multi
    def confirm_paid(self):
        return self.write({'state': 'paid'})

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should refund it instead.'))
            elif invoice.move_name:
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(AccountInvoice, self).unlink()

    @api.onchange('invoice_line_ids')
    @api.multi
    def _onchange_invoice_line_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        p = self.partner_id
        company_id = self.company_id.id
        type = self.type
        if p:
            partner_id = p.id
            rec_account = p.property_account_receivable
            pay_account = p.property_account_payable
            if company_id:
                if p.property_account_receivable.company_id and \
                        p.property_account_receivable.company_id.id != company_id and \
                        p.property_account_payable.company_id and \
                        p.property_account_payable.company_id.id != company_id:
                    prop = self.env['ir.property']
                    rec_dom = [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)]
                    pay_dom = [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)]
                    res_dom = [('res_id', '=', 'res.partner,%s' % partner_id)]
                    rec_prop = prop.search(rec_dom + res_dom) or prop.search(rec_dom)
                    pay_prop = prop.search(pay_dom + res_dom) or prop.search(pay_dom)
                    rec_account = rec_prop.get_by_record(rec_prop)
                    pay_account = pay_prop.get_by_record(pay_prop)
                    if not rec_account and not pay_account:
                        action = self.env.ref('account.action_account_config')
                        msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                        raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term.id
            fiscal_position = p.property_account_position.id
            bank_id = p.bank_ids and p.bank_ids.ids[0] or False
        self.account_id = account_id
        self.payment_term_id = payment_term_id
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'in_refund'):
            self.partner_bank_id = bank_id

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # When no payment term defined
            self.date_due = self.date_due or self.date_invoice
        else:
            pterm = self.payment_term_id
            pterm_list = pterm.compute(value=1, date_ref=date_invoice)[0]
            self.date_due = max(line[0] for line in pterm_list)

    @api.multi
    def action_cancel_draft(self):
        # go from canceled state to draft state
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': self.id,
                    'name': tax['name'],
                    'tax_id': tax['id'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
                    'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
                }

                # If the taxes generate moves on the same financial account as the invoice line,
                # propagate the analytic account from the invoice line to the tax line.
                # This is necessary in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = tax['id']
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
        return tax_grouped

    @api.one
    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        """ Reconcile payable/receivable lines from the invoice with payment_line """
        line_to_reconcile = self.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        return (line_to_reconcile + payment_line).reconcile(writeoff_acc_id, writeoff_journal_id)

    @api.v7
    def assign_outstanding_credit(self, cr, uid, id, payment_id, context=None):
        return self.browse(cr, uid, id, context).register_payment(self.pool.get('account.move.line').browse(cr, uid, payment_id, context))

    @api.multi
    def action_date_assign(self):
        for inv in self:
            # Here the onchange will automatically write to the database
            inv._onchange_payment_term_date_invoice()
        return True

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """ finalize_invoice_move_lines(move_lines) -> move_lines

            Hook method to be overridden in additional modules to verify and
            possibly alter the move lines to be created by an invoice, for
            special cases.
            :param move_lines: list of dictionaries with the account.move.lines (as for create())
            :return: the (possibly updated) final move_lines to create for this invoice
        """
        return move_lines

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.context_today(self))
                line['currency_id'] = currency.id
                line['amount_currency'] = line['price']
                line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines

    @api.model
    def invoice_line_move_line_get(self):
        res = []
        for line in self.invoice_line_ids:
            tax_ids = []
            for tax in line.invoice_line_tax_ids:
                tax_ids.append((4, tax.id, None))
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        tax_ids.append((4, child.id, None))

            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name.split('\n')[0][:64],
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': line.price_subtotal,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uos_id': line.uos_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'tax_ids': tax_ids,
                'invoice': self.id,
            }
            if line['account_analytic_id']:
                move_line_dict['analytic_lines'] = [(0, 0, line._get_analytic_line())]
            res.append(move_line_dict)
        return res

    @api.model
    def tax_line_move_line_get(self):
        res = []
        for tax_line in self.tax_line_ids:
            res.append({
                'tax_line_id': tax_line.tax_id.id,
                'type': 'tax',
                'name': tax_line.name,
                'price_unit': tax_line.amount,
                'quantity': 1,
                'price': tax_line.amount,
                'account_id': tax_line.account_id.id,
                'account_analytic_id': tax_line.account_analytic_id.id,
            })
        return res

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        return "%s-%s-%s-%s-%s" % (
            invoice_line['account_id'],
            invoice_line.get('tax_line_id', 'False'),
            invoice_line.get('product_id', 'False'),
            invoice_line.get('analytic_account_id', 'False'),
            invoice_line.get('date_maturity', 'False'),
        )

    def group_lines(self, iml, line):
        """Merge account move lines (and hence analytic lines) if invoice line hashcodes are equals"""
        if self.journal_id.group_invoice_lines:
            line2 = {}
            for x, y, l in line:
                tmp = self.inv_line_characteristic_hashcode(l)
                if tmp in line2:
                    am = line2[tmp]['debit'] - line2[tmp]['credit'] + (l['debit'] - l['credit'])
                    line2[tmp]['debit'] = (am > 0) and am or 0.0
                    line2[tmp]['credit'] = (am < 0) and -am or 0.0
                    line2[tmp]['analytic_lines'] += l['analytic_lines']
                else:
                    line2[tmp] = l
            line = []
            for key, val in line2.items():
                line.append((0, 0, val))
        return line

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                    raise UserError(_('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.compute(total, date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['dont_create_taxes'] = True
            ctx['invoice'] = inv.move_name and inv or False
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        return True

    @api.multi
    def invoice_validate(self):
        return self.write({'state': 'open'})

    @api.model
    def line_get_convert(self, line, part):
        return {
            'date_maturity': line.get('date_maturity', False),
            'partner_id': part,
            'name': line['name'][:64],
            'debit': line['price'] > 0 and line['price'],
            'credit': line['price'] < 0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_lines': line.get('analytic_lines', []),
            'amount_currency': line['price'] > 0 and abs(line.get('amount_currency', False)) or -abs(line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'quantity': line.get('quantity', 1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uos_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
            'invoice': line.get('invoice', False),
            'tax_ids': line.get('tax_ids', False),
            'tax_line_id': line.get('tax_line_id', False),
        }

    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            if inv.payment_move_line_ids:
                raise UserError(_('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))

        # First, set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'move_id': False})
        if moves:
            # second, invalidate the move(s)
            moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        return True

    ###################

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.number or TYPES[inv.type], inv.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.iteritems():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new refund from the invoice.
            This method may be overridden to implement custom
            refund generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice to refund
            :param string date_invoice: refund creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the refund from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the refund
        """
        values = {}
        for field in ['name', 'reference', 'comment', 'date_due', 'partner_id', 'company_id',
                'account_id', 'currency_id', 'payment_term_id', 'user_id', 'fiscal_position_id']:
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = filter(lambda l: l.manual, invoice.tax_line_ids)
        values['tax_line_ids'] = self._refund_cleanup_lines(tax_lines)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.number

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        return values

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                    description=description, journal_id=journal_id)
            new_invoices += self.create(values)
        return new_invoices

    @api.v8
    def pay_and_reconcile(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None):
        """ Create and post an account.payment for the invoice self, which creates a journal entry that reconciles the invoice.

            :param pay_journal: journal in which the payment entry will be created
            :param pay_amount: amount of the payment to register, defaults to the residual of the invoice
            :param date: payment date, defaults to fields.Date.context_today(self)
            :param writeoff_acc: account in which to create a writeoff if pay_amount < self.residual, so that the invoice is fully paid
        """
        assert len(self) == 1, "Can only pay one invoice at a time."
        payment_type = self.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        if payment_type == 'inbound':
            payment_method = self.env.ref('account.account_payment_method_manual_in')
            journal_payment_methods = pay_journal.inbound_payment_methods
        else:
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            journal_payment_methods = pay_journal.outbound_payment_methods
        if payment_method not in journal_payment_methods:
            raise UserError(_('No appropriate payment method enabled on journal %s') % pay_journal.name)

        payment = self.env['account.payment'].create({
            'invoice_ids': [(6, 0, self.ids)],
            'amount': pay_amount or self.residual,
            'payment_date': date or fields.Date.context_today(self),
            'communication': self.type in ('in_invoice', 'in_refund') and self.reference or self.number,
            'partner_id': self.partner_id.id,
            'partner_type': self.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
            'journal_id': pay_journal.id,
            'payment_type': payment_type,
            'payment_method': payment_method.id,
            'payment_difference_handling': writeoff_acc and 'reconcile' or 'open',
            'writeoff_account': writeoff_acc and writeoff_acc.id or False,
        })
        payment.post()

    @api.v7
    def pay_and_reconcile(self, cr, uid, ids, pay_journal_id, pay_amount=None, date=None, writeoff_acc_id=None, context=None):
        recs = self.browse(cr, uid, ids, context)
        pay_journal = self.pool.get('account.journal').browse(cr, uid, pay_journal_id, context=context)
        writeoff_acc = self.pool.get('account.account').browse(cr, uid, writeoff_acc_id, context=context)
        return recs.pay_and_reconcile(pay_journal, pay_amount, date, writeoff_acc)

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'paid' and self.type in ('out_invoice', 'out_refund'):
            return 'account.mt_invoice_paid'
        elif 'state' in init_values and self.state == 'open' and self.type in ('out_invoice', 'out_refund'):
            return 'account.mt_invoice_validated'
        elif 'state' in init_values and self.state == 'draft' and self.type in ('out_invoice', 'out_refund'):
            return 'account.mt_invoice_created'
        return super(AccountInvoice, self)._track_subtype(init_values)


class AccountInvoiceLine(models.Model):
    _name = "account.invoice.line"
    _description = "Invoice Line"
    _order = "invoice_id,sequence,id"

    @api.multi
    def _get_analytic_line(self):
        ref = self.invoice_id.number
        if not self.invoice_id.journal_id.analytic_journal_id:
            raise UserError(_("No Analytic Journal! You have to define an analytic journal on the '%s' journal!") % (self.invoice_id.journal_id.name,))
        return {
            'name': self.name,
            'date': self.invoice_id.date_invoice,
            'account_id': self.account_analytic_id.id,
            'unit_amount': self.quantity,
            'amount': self.price_subtotal_signed,
            'product_id': self.product_id.id,
            'product_uom_id': self.uos_id.id,
            'general_account_id': self.account_id.id,
            'journal_id': self.invoice_id.journal_id.analytic_journal_id.id,
            'ref': ref,
        }

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign

    @api.model
    def _default_price_unit(self):
        if not self._context.get('check_total'):
            return 0
        currency = self.invoice_id and self.invoice_id.currency_id or None
        total = self._context['check_total']
        for l in self._context.get('invoice_line_ids', []):
            if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                vals = l[2]
                price = vals.get('price_unit', 0) * (1 - vals.get('discount', 0) / 100.0)
                total = total - (price * vals.get('quantity'))
                taxes = vals.get('invoice_line_tax_ids')
                if taxes and len(taxes[0]) >= 3 and taxes[0][2]:
                    taxes = self.env['account.tax'].browse(taxes[0][2])
                    tax_res = taxes.compute_all(price, currency, vals.get('quantity'), vals.get('product_id'), self._context.get('partner_id'))
                    for tax in tax_res['taxes']:
                        total = total - tax['amount']
        return total

    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            if self._context.get('type') in ('out_invoice', 'in_refund'):
                return journal.default_credit_account_id.id
            return journal.default_debit_account_id.id

    name = fields.Text(string='Description', required=True)
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.")
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
        ondelete='cascade', index=True)
    uos_id = fields.Many2one('product.uom', string='Unit of Measure',
        ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product',
        ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=True, domain=[('deprecated', '=', False)],
        default=_default_account,
        help="The income or expense account related to the selected product.")
    price_unit = fields.Monetary(string='Unit Price', required=True,
        default=_default_price_unit)
    price_subtotal = fields.Monetary(string='Amount',
        store=True, readonly=True, compute='_compute_price')
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit notes.")
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'),
        default=0.0)
    invoice_line_tax_ids = fields.Many2many('account.tax',
        'account_invoice_line_tax', 'invoice_line_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none')], oldname='invoice_line_tax_id')
    account_analytic_id = fields.Many2one('account.analytic.account',
        string='Analytic Account')
    company_id = fields.Many2one('res.company', string='Company',
        related='invoice_id.company_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner',
        related='invoice_id.partner_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True)
    company_currency_id = fields.Many2one('res.currency', related='invoice_id.company_currency_id', readonly=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountInvoiceLine, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('type'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='product_id']"):
                if self._context['type'] in ('in_invoice', 'in_refund'):
                    node.set('domain', "[('purchase_ok', '=', True)]")
                else:
                    node.set('domain', "[('sale_ok', '=', True)]")
            res['arch'] = etree.tostring(doc)
        return res

    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    def _set_taxes(self):
        """ Used in on_change to set taxes """
        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            taxes = self.product_id.taxes_id or self.account_id.tax_ids
        else:
            taxes = self.product_id.supplier_taxes_id or self.account_id.tax_ids
        self.invoice_line_tax_ids = self.invoice_id.fiscal_position_id.map_tax(taxes)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.company_id
        currency = self.invoice_id.currency_id
        type = self.invoice_id.type

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uos_id'] = []
        else:
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id

            self.name = product.partner_ref
            account = self.get_invoice_line_account(type, product, fpos, company)
            self.account_id = account.id
            self._set_taxes()

            if type in ('in_invoice', 'in_refund'):
                self.price_unit = self.price_unit or product.standard_price
                if product.description_purchase:
                    self.name += '\n' + product.description_purchase
            else:
                self.price_unit = product.lst_price
                if product.description_sale:
                    self.name += '\n' + product.description_sale

            if not self.uos_id or product.uom_id.category_id.id != self.uos_id.category_id.id:
                self.uos_id = product.uom_id.id
            domain['uos_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:
                if company.currency_id != currency:
                    if type in ('in_invoice', 'in_refund'):
                        self.price_unit = product.standard_price
                    self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.date_invoice)).rate

                if self.uos_id and self.uos_id.id != product.uom_id.id:
                    self.price_unit = self.env['product.uom']._compute_price(
                        product.uom_id.id, self.price_unit, self.uos_id.id)
        return {'domain': domain}

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if not self.account_id:
            return
        if not self.product_id:
            fpos = self.invoice_id.fiscal_position_id
            self.invoice_line_tax_ids = fpos.map_tax(self.account_id.tax_ids).ids
        else:
            self._set_taxes()

    @api.onchange('uos_id')
    def _onchange_uos_id(self):
        warning = {}
        result = {}
        self._onchange_product_id()
        if not self.uos_id:
            self.price_unit = 0.0
        if self.product_id and self.uos_id:
            if self.product_id.uom_id.category_id.id != self.uos_id.category_id.id:
                warning = {
                    'title': _('Warning!'),
                    'message': _('The selected unit of measure is not compatible with the unit of measure of the product.'),
                }
                self.uos_id = self.product_id.uom_id.id
        if warning:
            result['warning'] = warning
        return result


class AccountInvoiceTax(models.Model):
    _name = "account.invoice.tax"
    _description = "Invoice Tax"
    _order = 'sequence'

    invoice_id = fields.Many2one('account.invoice', string='Invoice', ondelete='cascade', index=True)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax')
    account_id = fields.Many2one('account.account', string='Tax Account', required=True, domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Monetary()
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, readonly=True)


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _description = "Payment Term"
    _order = "name"

    name = fields.Char(string='Payment Term', translate=True, required=True)
    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the payment term without removing it.")
    note = fields.Text(string='Description', translate=True)
    line_ids = fields.One2many('account.payment.term.line', 'payment_id', string='Terms', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    @api.constrains('line_ids')
    @api.one
    def _check_lines(self):
        if self.line_ids and self.line_ids[-1].value != 'balance':
            raise UserError("A Payment Term should have its last line of type Balance")

    @api.one
    def compute(self, value, date_ref=False):
        date_ref = date_ref or datetime.now().strftime('%Y-%m-%d')
        amount = value
        result = []
        prec = self.company_id.currency_id.decimal_places
        for line in self.line_ids:
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'percent':
                amt = round(value * (line.value_amount / 100.0), prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result.append((next_date.strftime('%Y-%m-%d'), amt))
                amount -= amt

        amount = reduce(lambda x, y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))
        return result


class AccountPaymentTermLine(models.Model):
    _name = "account.payment.term.line"
    _description = "Payment Term Line"
    _order = "days"

    value = fields.Selection([
            ('balance', 'Balance'),
            ('percent', 'Percent'),
            ('fixed', 'Fixed Amount')
        ], string='Computation', required=True, default='balance',
        help="Select here the kind of valuation related to this payment term line.")
    value_amount = fields.Float(string='Amount To Pay', digits=dp.get_precision('Payment Term'), help="For percent enter a ratio between 0-100.")
    days = fields.Integer(string='Number of Days', required=True, default=30, help="Number of days to add before computing the day of the month.")
    days2 = fields.Integer(string='Day of the Month', required=True, default='0',
        help="Day of the month \n\n Set : \n1)-1 for the last day of the current month. \n2) 0 for net days\n3) A positive number for the specific day of the next month.\n\nExample : if Date=15/01, Number of Days=22, Day of Month=-1, then the due date is 28/02.")
    payment_id = fields.Many2one('account.payment.term', string='Payment Term', required=True, index=True, ondelete='cascade')

    @api.one
    @api.constrains('value', 'value_amount')
    def _check_percent(self):
        if self.value == 'percent' and (self.value_amount < 0.0 or self.value_amount > 100.0):
            raise UserError(_('Percentages for Payment Term Line must be between 0 and 100.'))


class MailComposeMessage(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.write({'sent': True})
            invoice.message_post(body=_("Invoice sent"))
        return super(MailComposeMessage, self).send_mail()
