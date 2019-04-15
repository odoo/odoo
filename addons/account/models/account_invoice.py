# -*- coding: utf-8 -*-

import json
import re
import uuid
from functools import partial

from lxml import etree

from odoo import api, exceptions, fields, models, _
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning

from odoo.addons import decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

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
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class AccountInvoice(models.Model):
    _name = "account.invoice"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Invoice"
    _order = "date_invoice desc, number desc, id desc"


    def _get_default_incoterm(self):
        return self.env.user.company_id.incoterm_id

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id
            amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
            amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        for inv in self:
            if float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1:
                raise Warning(_('You cannot validate an invoice with a negative total amount. You should create a credit note instead.'))

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        journal_with_currency = False
        if self._context.get('default_currency_id'):
            currency_clause = [('currency_id', '=', self._context.get('default_currency_id'))]
            journal_with_currency = self.env['account.journal'].search(domain + currency_clause, limit=1)
        return journal_with_currency or self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id

    def _default_comment(self):
        invoice_type = self.env.context.get('type', 'out_invoice')
        if invoice_type == 'out_invoice' and self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
            return self.env.user.company_id.invoice_terms

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self.sudo().move_id.line_ids:
            if line.account_id == self.account_id:
                residual_company_signed += line.amount_residual
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = line.currency_id or line.company_id.currency_id
                    residual += from_currency._convert(line.amount_residual, self.currency_id, line.company_id, line.date or fields.Date.today())
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if self.move_id and float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False

    @api.multi
    def _get_domain_edition_mode_available(self):
        self.ensure_one()
        domain = self.env['account.move.line']._get_domain_for_edition_mode()
        domain += ['|',('move_id.partner_id', '=?', self.partner_id.id),('move_id.partner_id', '=', False)]
        if self.type in ('out_invoice', 'in_refund'):
            domain.append(('balance', '=', -self.residual))
        else:
            domain.append(('balance', '=', self.residual))
        return domain

    @api.multi
    def _get_edition_mode_available(self):
        for r in self:
            domain = r._get_domain_edition_mode_available()
            domain2 = [('state', '=', 'open'),('residual', '=', r.residual),('type', '=', r.type)]
            r.edition_mode_available = (0 < self.env['account.move.line'].search_count(domain) < 5) and self.env['account.invoice'].search_count(domain2) < 5 and r.state == 'open'

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      '|',
                        '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                        '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), self.currency_id, self.company_id, line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    if line.ref :
                        title = '%s : %s' % (line.move_id.name, line.ref)
                    else:
                        title = line.move_id.name
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'title': title,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.model
    def _get_payments_vals(self):
        if not self.payment_move_line_ids:
            return []
        payment_vals = []
        currency_id = self.currency_id
        for payment in self.payment_move_line_ids:
            payment_currency_id = False
            if self.type in ('out_invoice', 'in_refund'):
                amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                amount_currency = sum(
                    [p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                if payment.matched_debit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                               payment.matched_debit_ids]) and payment.matched_debit_ids[
                                              0].currency_id or False
            elif self.type in ('in_invoice', 'out_refund'):
                amount = sum(
                    [p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if
                                       p.credit_move_id in self.move_id.line_ids])
                if payment.matched_credit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                               payment.matched_credit_ids]) and payment.matched_credit_ids[
                                              0].currency_id or False
            # get the payment value in invoice currency
            if payment_currency_id and payment_currency_id == self.currency_id:
                amount_to_show = amount_currency
            else:
                currency = payment.company_id.currency_id
                amount_to_show = currency._convert(amount, self.currency_id, payment.company_id, self.date or fields.Date.today())
            if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                continue
            payment_ref = payment.move_id.name
            if payment.move_id.ref:
                payment_ref += ' (' + payment.move_id.ref + ')'
            payment_vals.append({
                'name': payment.name,
                'journal_name': payment.journal_id.name,
                'amount': amount_to_show,
                'currency': currency_id.symbol,
                'digits': [69, currency_id.decimal_places],
                'position': currency_id.position,
                'date': payment.date,
                'payment_id': payment.id,
                'account_payment_id': payment.payment_id.id,
                'invoice_id': payment.invoice_id.id,
                'move_id': payment.move_id.id,
                'ref': payment_ref,
            })
        return payment_vals

    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': self._get_payments_vals()}
            self.payments_widget = json.dumps(info, default=date_utils.json_default)

    @api.one
    @api.depends('move_id.line_ids.amount_residual')
    def _compute_payments(self):
        payment_lines = set()
        for line in self.move_id.line_ids.filtered(lambda l: l.account_id.id == self.account_id.id):
            payment_lines.update(line.mapped('matched_credit_ids.credit_move_id.id'))
            payment_lines.update(line.mapped('matched_debit_ids.debit_move_id.id'))
        self.payment_move_line_ids = self.env['account.move.line'].browse(list(payment_lines)).sorted()

    name = fields.Char(string='Reference/Description', index=True,
        readonly=True, states={'draft': [('readonly', False)]}, copy=False, help='The name that will be used on account move lines')

    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.",
        readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Vendor Bill'),
            ('out_refund','Customer Credit Note'),
            ('in_refund','Vendor Credit Note'),
        ], readonly=True, states={'draft': [('readonly', False)]}, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        tracking=True)

    refund_invoice_id = fields.Many2one('account.invoice', string="Invoice for which this invoice is the credit note")
    number = fields.Char(related='move_id.name', store=True, readonly=True, copy=False)
    move_name = fields.Char(string='Journal Entry Name', readonly=False,
        default=False, copy=False,
        help="Technical field holding the number given to the invoice, automatically set when the invoice is validated then stored to set the same number again if the invoice is cancelled, set to draft and re-validated.")
    reference = fields.Char(string='Payment Ref.', copy=False, readonly=True, states={'draft': [('readonly', False)]},
        help='The payment communication that will be automatically populated once the invoice validation. You can also write a free communication.')
    comment = fields.Text('Additional Information', readonly=True, states={'draft': [('readonly', False)]}, default=_default_comment)

    state = fields.Selection([
            ('draft','Draft'),
            ('open', 'Open'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        tracking=True, copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
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
             "of accounting entries. The Payment terms may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the Payment terms and the due date empty, it "
             "means direct payment.")
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True,
        readonly=True, states={'draft': [('readonly', False)]},
        tracking=True, help="You can find a contact by its Name, TIN, Email or Internal Reference.")
    vendor_bill_id = fields.Many2one('account.invoice', string='Vendor Bill',
        help="Auto-complete from a past bill.")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term',
        readonly=True, states={'draft': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment terms and the due date empty, it means direct payment. "
             "The payment terms may compute several due dates, for example 50% now, 50% in one month.")
    date = fields.Date(string='Accounting Date',
        copy=False,
        help="Keep empty to use the invoice date.",
        readonly=True, states={'draft': [('readonly', False)]})

    account_id = fields.Many2one('account.account', string='Account',
        readonly=True, states={'draft': [('readonly', False)]},
        domain=[('deprecated', '=', False)], help="The partner account used for this invoice.")
    invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', oldname='invoice_line',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    tax_line_ids = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines', oldname='tax_line',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    refund_invoice_ids = fields.One2many('account.invoice', 'refund_invoice_id', string='Refund Invoices', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Journal Items.")

    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_untaxed = fields.Monetary(string='Untaxed Amount',
        store=True, readonly=True, compute='_compute_amount', tracking=True)
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount in Company Currency', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount')
    amount_tax = fields.Monetary(string='Tax',
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    amount_total_signed = fields.Monetary(string='Total in Invoice Currency', currency_field='currency_id',
        store=True, readonly=True, compute='_compute_amount',
        help="Total amount in the currency of the invoice, negative for credit notes.")
    amount_total_company_signed = fields.Monetary(string='Total in Company Currency', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount',
        help="Total amount in the currency of the company, negative for credit notes.")
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, tracking=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice'))

    reconciled = fields.Boolean(string='Paid/Reconciled', store=True, readonly=True, compute='_compute_residual',
        help="It indicates that the invoice has been paid and the journal entry of the invoice has been reconciled with one or several journal entries of payment.")
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
        readonly=True, states={'draft': [('readonly', False)]}) #Default value computed in default_get for out_invoices

    residual = fields.Monetary(string='Amount Due',
        compute='_compute_residual', store=True, help="Remaining amount due.")
    residual_signed = fields.Monetary(string='Amount Due in Invoice Currency', currency_field='currency_id',
        compute='_compute_residual', store=True, help="Remaining amount due in the currency of the invoice.")
    residual_company_signed = fields.Monetary(string='Amount Due in Company Currency', currency_field='company_currency_id',
        compute='_compute_residual', store=True, help="Remaining amount due in the currency of the company.")
    payment_ids = fields.Many2many('account.payment', 'account_invoice_payment_rel', 'invoice_id', 'payment_id', string="Payments", copy=False, readonly=True)
    payment_move_line_ids = fields.Many2many('account.move.line', string='Payment Move Lines', compute='_compute_payments', store=True)
    user_id = fields.Many2one('res.users', string='Salesperson', tracking=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user, copy=False)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
        readonly=True, states={'draft': [('readonly', False)]})
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity', compute_sudo=True,
        related='partner_id.commercial_partner_id', store=True, readonly=True,
        help="The commercial entity that will be used on Journal Entries for this invoice")

    edition_mode_available = fields.Boolean(compute='_get_edition_mode_available', groups='account.group_account_invoice')
    outstanding_credits_debits_widget = fields.Text(compute='_get_outstanding_info_JSON', groups="account.group_account_invoice")
    payments_widget = fields.Text(compute='_get_payment_info_JSON', groups="account.group_account_invoice")
    has_outstanding = fields.Boolean(compute='_get_outstanding_info_JSON', groups="account.group_account_invoice")
    cash_rounding_id = fields.Many2one('account.cash.rounding', string='Cash Rounding Method',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Defines the smallest coinage of the currency that can be used to pay by cash.')
    refund_tax_mismatch = fields.Boolean(string="Refund Tax Mismatch", compute='_compute_refund_tax_mismatch', help="For refund invoices, true if the total tax amount of the refund is different from the one of the invoice it was created for (this can occur in case of manual adjustment of invoice taxes).")

    #fields use to set the sequence, on the first invoice of the journal
    sequence_number_next = fields.Char(string='Next Number', compute="_get_sequence_number_next", inverse="_set_sequence_next")
    sequence_number_next_prefix = fields.Char(string='Next Number Prefix', compute="_get_sequence_prefix")
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterm',
        default=_get_default_incoterm,
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

    #fields related to vendor bills automated creation by email
    source_email = fields.Char(string='Source Email', tracking=True)
    vendor_display_name = fields.Char(compute='_get_vendor_display_info', store=True)  # store=True to enable sorting on that column
    invoice_icon = fields.Char(compute='_get_vendor_display_info', store=False)

    _sql_constraints = [
        ('number_uniq', 'unique(number, company_id, journal_id, type)', 'Invoice Number must be unique per Company!'),
    ]

    @api.depends('partner_id', 'source_email')
    def _get_vendor_display_info(self):
        for invoice in self:
            vendor_display_name = invoice.partner_id.name
            invoice.invoice_icon = ''
            if not vendor_display_name:
                if invoice.source_email:
                    vendor_display_name = _('From: ') + invoice.source_email
                    invoice.invoice_icon = '@'
                else:
                    vendor_display_name = ('Created by: ') + invoice.create_uid.name
                    invoice.invoice_icon = '#'
            invoice.vendor_display_name = vendor_display_name

    @api.multi
    def _get_computed_reference(self):
        self.ensure_one()
        if self.company_id.invoice_reference_type == 'invoice_number':
            seq_suffix = self.journal_id.sequence_id.suffix or ''
            regex_number = '.*?([0-9]+)%s$' % seq_suffix
            exact_match = re.match(regex_number, self.number)
            if exact_match:
                identification_number = int(exact_match.group(1))
            else:
                ran_num = str(uuid.uuid4().int)
                identification_number = int(ran_num[:5] + ran_num[-5:])
            prefix = self.number
        else:
            #self.company_id.invoice_reference_type == 'partner'
            identification_number = self.partner_id.id
            prefix = 'CUST'
        return '%s/%s' % (prefix, str(identification_number % 97).rjust(2, '0'))

    # Load all Vendor Bill lines
    @api.onchange('vendor_bill_id')
    def _onchange_vendor_bill(self):
        if not self.vendor_bill_id:
            return {}
        self.currency_id = self.vendor_bill_id.currency_id
        new_lines = self.env['account.invoice.line']
        for line in self.vendor_bill_id.invoice_line_ids:
            new_lines += new_lines.new(line._prepare_invoice_line())
        self.invoice_line_ids += new_lines
        self.payment_term_id = self.vendor_bill_id.payment_term_id
        self.vendor_bill_id = False
        return {}

    def _get_seq_number_next_stuff(self):
        self.ensure_one()
        journal_sequence = self.journal_id.sequence_id
        if self.journal_id.refund_sequence:
            domain = [('type', '=', self.type)]
            journal_sequence = self.type in ['in_refund', 'out_refund'] and self.journal_id.refund_sequence_id or self.journal_id.sequence_id
        elif self.type in ['in_invoice', 'in_refund']:
            domain = [('type', 'in', ['in_invoice', 'in_refund'])]
        else:
            domain = [('type', 'in', ['out_invoice', 'out_refund'])]
        if self.id:
            domain += [('id', '<>', self.id)]
        domain += [('journal_id', '=', self.journal_id.id), ('state', 'not in', ['draft', 'cancel'])]
        return journal_sequence, domain

    def _compute_access_url(self):
        super(AccountInvoice, self)._compute_access_url()
        for invoice in self:
            invoice.access_url = '/my/invoices/%s' % (invoice.id)

    @api.depends('refund_invoice_id.tax_line_ids', 'tax_line_ids')
    def _compute_refund_tax_mismatch(self):
        for record in self.filtered(lambda x: x.refund_invoice_id):
            invoice_tax_sum = sum(record.refund_invoice_id.mapped('tax_line_ids.amount'))
            # Unlikely to happen, but it is possible to create a refund in another currency, so we convert the sum
            invoice_tax_sum_converted = record.refund_invoice_id.currency_id._convert(invoice_tax_sum, record.currency_id, record.company_id, record.date or fields.Date.today())
            refund_tax_sum = sum(record.mapped('tax_line_ids.amount'))
            record.refund_tax_mismatch = record.currency_id.compare_amounts(invoice_tax_sum_converted, refund_tax_sum) != 0

    @api.depends('state', 'journal_id', 'date_invoice')
    def _get_sequence_prefix(self):
        """ computes the prefix of the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        if not self.env.user._is_system():
            for invoice in self:
                invoice.sequence_number_next_prefix = False
                invoice.sequence_number_next = ''
            return
        for invoice in self:
            journal_sequence, domain = invoice._get_seq_number_next_stuff()
            if (invoice.state == 'draft') and not self.search(domain, limit=1):
                prefix, dummy = journal_sequence.with_context(ir_sequence_date=invoice.date_invoice,
                                                              ir_sequence_date_range=invoice.date_invoice)._get_prefix_suffix()
                invoice.sequence_number_next_prefix = prefix
            else:
                invoice.sequence_number_next_prefix = False

    @api.depends('state', 'journal_id')
    def _get_sequence_number_next(self):
        """ computes the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        for invoice in self:
            journal_sequence, domain = invoice._get_seq_number_next_stuff()
            if (invoice.state == 'draft') and not self.search(domain, limit=1):
                number_next = journal_sequence._get_current_sequence().number_next_actual
                invoice.sequence_number_next = '%%0%sd' % journal_sequence.padding % number_next
            else:
                invoice.sequence_number_next = ''

    @api.multi
    def _set_sequence_next(self):
        ''' Set the number_next on the sequence related to the invoice/bill/refund'''
        self.ensure_one()
        journal_sequence, domain = self._get_seq_number_next_stuff()
        if not self.env.user._is_admin() or not self.sequence_number_next or self.search_count(domain):
            return
        nxt = re.sub("[^0-9]", '', self.sequence_number_next)
        result = re.match("(0*)([0-9]+)", nxt)
        if result and journal_sequence:
            # use _get_current_sequence to manage the date range sequences
            sequence = journal_sequence._get_current_sequence()
            sequence.number_next = int(result.group(2))

    @api.multi
    def _get_report_base_filename(self):
        self.ensure_one()
        return  self.type == 'out_invoice' and self.state == 'draft' and _('Draft Invoice') or \
                self.type == 'out_invoice' and self.state in ('open','in_payment','paid') and _('Invoice - %s') % (self.number) or \
                self.type == 'out_refund' and self.state == 'draft' and _('Credit Note') or \
                self.type == 'out_refund' and _('Credit Note - %s') % (self.number) or \
                self.type == 'in_invoice' and self.state == 'draft' and _('Vendor Bill') or \
                self.type == 'in_invoice' and self.state in ('open','in_payment','paid') and _('Vendor Bill - %s') % (self.number) or \
                self.type == 'in_refund' and self.state == 'draft' and _('Vendor Credit Note') or \
                self.type == 'in_refund' and _('Vendor Credit Note - %s') % (self.number)

    @api.model
    def create(self, vals):
        if not vals.get('journal_id') and vals.get('type'):
            vals['journal_id'] = self.with_context(type=vals.get('type'))._default_journal().id

        onchanges = {
            '_onchange_partner_id': ['account_id', 'payment_term_id', 'fiscal_position_id', 'partner_bank_id'],
            '_onchange_journal_id': ['currency_id'],
        }
        for onchange_method, changed_fields in onchanges.items():
            if any(f not in vals for f in changed_fields):
                invoice = self.new(vals)
                getattr(invoice, onchange_method)()
                for field in changed_fields:
                    if field not in vals and invoice[field]:
                        vals[field] = invoice._fields[field].convert_to_write(invoice[field], invoice)

        invoice = super(AccountInvoice, self.with_context(mail_create_nolog=True)).create(vals)

        if any(line.invoice_line_tax_ids for line in invoice.invoice_line_ids) and not invoice.tax_line_ids:
            invoice.compute_taxes()

        return invoice

    @api.constrains('partner_id', 'partner_bank_id')
    def validate_partner_bank_id(self):
        for record in self:
            if record.partner_bank_id:
                if record.type in ('in_invoice', 'out_refund') and record.partner_bank_id.partner_id != record.partner_id.commercial_partner_id:
                    raise ValidationError(_("Commercial partner and vendor account owners must be identical."))
                elif record.type in ('out_invoice', 'in_refund') and not record.company_id in record.partner_bank_id.partner_id.ref_company_ids:
                    raise ValidationError(_("The account selected for payment does not belong to the same company as this invoice."))

    @api.multi
    def _write(self, vals):
        pre_not_reconciled = self.filtered(lambda invoice: not invoice.reconciled)
        pre_reconciled = self - pre_not_reconciled
        res = super(AccountInvoice, self)._write(vals)
        reconciled = self.filtered(lambda invoice: invoice.reconciled)
        not_reconciled = self - reconciled
        (reconciled & pre_reconciled).filtered(lambda invoice: invoice.state == 'open').action_invoice_paid()
        (not_reconciled & pre_not_reconciled).filtered(lambda invoice: invoice.state in ('in_payment', 'paid')).action_invoice_re_open()
        return res

    @api.model
    def default_get(self,default_fields):
        """ Compute default partner_bank_id field for 'out_invoice' type,
        using the default values computed for the other fields.
        """
        res = super(AccountInvoice, self).default_get(default_fields)

        if res.get('type', False) not in ('out_invoice', 'in_refund') or not 'company_id' in res:
            return res

        partner_bank_result = self._get_partner_bank_id(res['company_id'])
        if partner_bank_result:
            res['partner_bank_id'] = partner_bank_result.id
        return res

    def _get_partner_bank_id(self, company_id):
        company = self.env['res.company'].browse(company_id)
        if company.partner_id:
            return self.env['res.partner.bank'].search([('partner_id', '=', company.partner_id.id)], limit=1)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        def get_view_id(xid, name):
            try:
                return self.env.ref('account.' + xid)
            except ValueError:
                view = self.env['ir.ui.view'].search([('name', '=', name)], limit=1)
                if not view:
                    return False
                return view.id

        context = self._context
        supplier_form_view_id = get_view_id('invoice_supplier_form', 'account.invoice.supplier.form').id
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner = self.env['res.partner'].browse(context['active_ids'])[0]
            if not view_type:
                view_id = get_view_id('invoice_tree', 'account.invoice.tree')
                view_type = 'tree'
            elif view_type == 'form':
                if partner.supplier and not partner.customer:
                    view_id = supplier_form_view_id
                elif partner.customer and not partner.supplier:
                    view_id = get_view_id('invoice_form', 'account.invoice.form').id

        return super(AccountInvoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.filtered(lambda inv: not inv.sent).write({'sent': True})
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)

    @api.multi
    def action_reconcile_to_check(self, params):
        self.ensure_one()
        domain = self._get_domain_edition_mode_available()
        ids = self.env['account.move.line'].search(domain).mapped('statement_line_id').ids
        action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
        action_context.update({'edition_mode': True})
        action_context.update({'statement_line_ids': ids})
        action_context.update({'partner_id': self.partner_id.id})
        action_context.update({'partner_name': self.partner_id.name})
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': action_context,
        }

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_invoice_as_sent'):
            self.filtered(lambda inv: not inv.sent).write({'sent': True})
            self.env.user.company_id.set_onboarding_step_done('account_onboarding_sample_invoice_state')
        return super(AccountInvoice, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new(), called by the mailgateway through message_process,
            to complete values for vendor bills created by mails.
        """
        # Split `From` and `CC` email address from received email to look for related partners to subscribe on the invoice
        subscribed_emails = email_split((msg_dict.get('from') or '') + ',' + (msg_dict.get('cc') or ''))
        subscribed_partner_ids = [pid for pid in self._find_partner_from_emails(subscribed_emails) if pid]

        # Detection of the partner_id of the invoice:
        # 1) check if the email_from correspond to a supplier
        email_from = msg_dict.get('from') or ''
        email_from = email_escape_char(email_split(email_from)[0])
        partner_id = self._search_on_partner(email_from, extra_domain=[('supplier', '=', True)])

        # 2) otherwise, if the email sender is from odoo internal users then it is likely that the vendor sent the bill
        # by mail to the internal user who, inturn, forwarded that email to the alias to automatically generate the bill
        # on behalf of the vendor.
        if not partner_id:
            user_partner_id = self._search_on_user(email_from)
            if user_partner_id and user_partner_id in self.env.ref('base.group_user').users.mapped('partner_id').ids:
                # In this case, we will look for the vendor's email address in email's body and assume if will come first
                email_addresses = email_re.findall(msg_dict.get('body'))
                if email_addresses:
                    partner_ids = [pid for pid in self._find_partner_from_emails([email_addresses[0]], force_create=False) if pid]
                    partner_id = partner_ids and partner_ids[0]
            # otherwise, there's no fallback on the partner_id found for the regular author of the mail.message as we want
            # the partner_id to stay empty

        # If the partner_id can be found, subscribe it to the bill, otherwise it's left empty to be manually filled
        if partner_id:
            subscribed_partner_ids.append(partner_id)

        # Find the right purchase journal based on the "TO" email address
        destination_emails = email_split((msg_dict.get('to') or '') + ',' + (msg_dict.get('cc') or ''))
        alias_names = [mail_to.split('@')[0] for mail_to in destination_emails]
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'), ('alias_name', 'in', alias_names)
        ], limit=1)

        # Create the message and the bill.
        values = dict(custom_values or {}, partner_id=partner_id, source_email=email_from)
        if journal:
            values['journal_id'] = journal.id
        # Passing `type` in context so that _default_journal(...) can correctly set journal for new vendor bill
        invoice = super(AccountInvoice, self.with_context(type=values.get('type'))).message_new(msg_dict, values)

        # Subscribe people on the newly created bill
        if subscribed_partner_ids:
            invoice.message_subscribe(subscribed_partner_ids)
        return invoice

    @api.model
    def complete_empty_list_help(self):
        # add help message about email alias in vendor bills empty lists
        Journal = self.env['account.journal']
        journals = Journal.browse(self._context.get('default_journal_id')) or Journal.search([('type', '=', 'purchase')])

        if journals:
            links = ''
            alias_count = 0
            for journal in journals.filtered(lambda j: j.alias_domain and j.alias_id.alias_name):
                email = format(journal.alias_id.alias_name) + "@" + format(journal.alias_domain)
                links += "<a id='o_mail_test' href='mailto:{}'>{}</a>".format(email, email) + ", "
                alias_count += 1
            if links and alias_count == 1:
                help_message = _('Or share the email %s to your vendors: bills will be created automatically upon mail reception.') % (links[:-2])
            elif links:
                help_message = _('Or share the emails %s to your vendors: bills will be created automatically upon mail reception.') % (links[:-2])
            else:
                help_message = _('''Or set an <a data-oe-id=%s data-oe-model="account.journal" href=#id=%s&model=account.journal>email alias</a> '''
                                              '''to allow draft vendor bills to be created upon reception of an email.''') % (journals[0].id, journals[0].id)
        else:
            help_message = _('<p>You can control the invoice from your vendor based on what you purchased or received.</p>')
        return help_message

    @api.multi
    def compute_taxes(self):
        """Function used in other module to compute the taxes on a fresh invoice created (onchanges did not applied)"""
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            # Delete non-manual tax lines
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            if self._cr.rowcount:
                self.invalidate_cache()

            # Generate one tax line per tax, however many invoice lines it's applied to
            tax_grouped = invoice.get_taxes_values()

            # Create new tax lines
            for tax in tax_grouped.values():
                account_invoice_tax.create(tax)

        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line_ids': []})

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should create a credit note instead.'))
            elif invoice.move_name:
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(AccountInvoice, self).unlink()

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.filtered('manual')
        for tax in taxes_grouped.values():
            # ATTENTION: due to this, fields in tax have to be in the view (possibly invisible), as they won't be saved otherwise (when hitting "save")
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        warning = {}
        domain = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        type = self.type
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('in_invoice', 'in_refund'):
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id
            else:
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id

            delivery_partner_id = self.get_delivery_partner_id()
            fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id, delivery_id=delivery_partner_id)

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                    }
                if p.invoice_warn == 'block':
                    self.partner_id = False

        self.account_id = account_id
        self.payment_term_id = payment_term_id
        self.date_due = False
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}

        res = {}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.multi
    def get_delivery_partner_id(self):
        self.ensure_one()
        return self.partner_id.address_get(['delivery'])['delivery']

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id and not self._context.get('default_currency_id'):
            self.currency_id = self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if self.payment_term_id:
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_invoice)
            self.date_due = max(line[0] for line in pterm_list)
        elif self.date_due and (date_invoice > self.date_due):
            self.date_due = date_invoice

    @api.onchange('cash_rounding_id', 'invoice_line_ids', 'tax_line_ids')
    def _onchange_cash_rounding(self):
        # Drop previous cash rounding lines
        lines_to_remove = self.invoice_line_ids.filtered(lambda l: l.is_rounding_line)
        if lines_to_remove:
            self.invoice_line_ids -= lines_to_remove

        # Clear previous rounded amounts
        for tax_line in self.tax_line_ids:
            if tax_line.amount_rounding != 0.0:
                tax_line.amount_rounding = 0.0

        if self.cash_rounding_id and self.type in ('out_invoice', 'out_refund'):
            rounding_amount = self.cash_rounding_id.compute_difference(self.currency_id, self.amount_total)
            if not self.currency_id.is_zero(rounding_amount):
                if self.cash_rounding_id.strategy == 'biggest_tax':
                    # Search for the biggest tax line and add the rounding amount to it.
                    # If no tax found, an error will be raised by the _check_cash_rounding method.
                    if not self.tax_line_ids:
                        return
                    biggest_tax_line = None
                    for tax_line in self.tax_line_ids:
                        if not biggest_tax_line or tax_line.amount > biggest_tax_line.amount:
                            biggest_tax_line = tax_line
                    biggest_tax_line.amount_rounding += rounding_amount
                elif self.cash_rounding_id.strategy == 'add_invoice_line':
                    # Create a new invoice line to perform the rounding
                    rounding_line = self.env['account.invoice.line'].new({
                        'name': self.cash_rounding_id.name,
                        'invoice_id': self.id,
                        'account_id': self.cash_rounding_id.account_id.id,
                        'price_unit': rounding_amount,
                        'quantity': 1,
                        'is_rounding_line': True,
                        'sequence': 9999  # always last line
                    })

                    # To be able to call this onchange manually from the tests,
                    # ensure the inverse field is updated on account.invoice.
                    if not rounding_line in self.invoice_line_ids:
                        self.invoice_line_ids += rounding_line

    @api.multi
    def action_invoice_draft(self):
        if self.filtered(lambda inv: inv.state != 'cancel'):
            raise UserError(_("Invoice must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        self.write({'state': 'draft', 'date': False})
        # Delete former printed invoice
        try:
            report_invoice = self.env['ir.actions.report']._get_report_from_name('account.report_invoice')
        except IndexError:
            report_invoice = False
        if report_invoice and report_invoice.attachment:
            for invoice in self:
                with invoice.env.do_in_draft():
                    invoice.number, invoice.state = invoice.move_name, 'open'
                    attachment = self.env.ref('account.account_invoices').retrieve_attachment(invoice)
                if attachment:
                    attachment.unlink()
        return True

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: not inv.partner_id):
            raise UserError(_("The field Vendor is required, please complete it to validate the Vendor Bill."))
        if to_open_invoices.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to validate it."))
        if to_open_invoices.filtered(lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
            raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
        if to_open_invoices.filtered(lambda inv: not inv.account_id):
            raise UserError(_('No account was found to create the invoice, be sure you have installed a chart of account.'))
        to_open_invoices.action_date_assign()
        to_open_invoices.invoice_validate()
        return to_open_invoices.action_move_create()

    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        if to_pay_invoices.filtered(lambda inv: inv.state not in ('open', 'in_payment')):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))

        for invoice in to_pay_invoices:
            if any([move.journal_id.post_at_bank_rec and move.state == 'draft' for move in invoice.payment_move_line_ids.mapped('move_id')]):
                invoice.write({'state': 'in_payment'})
            else:
                invoice.write({'state': 'paid'})

    @api.multi
    def action_invoice_re_open(self):
        if self.filtered(lambda inv: inv.state not in ('in_payment', 'paid')):
            raise UserError(_('Invoice must be paid in order to set it to register payment.'))
        return self.write({'state': 'open'})

    @api.multi
    def action_invoice_cancel(self):
        return self.filtered(lambda inv: inv.state != 'cancel').action_cancel()

    @api.multi
    def _notify_get_groups(self, message, groups):
        """ Give access button to users and portal customer as portal is integrated
        in account. Customer and portal group have probably no right to see
        the document so they don't have the access button. """
        groups = super(AccountInvoice, self)._notify_get_groups(message, groups)

        if self.state not in ('draft', 'cancel'):
            for group_name, group_method, group_data in groups:
                if group_name in ('customer', 'portal'):
                    continue
                group_data['has_button_access'] = True

        return groups

    @api.multi
    def get_formview_id(self, access_uid=None):
        """ Update form view id of action to open the invoice """
        if self.type in ('in_invoice', 'in_refund'):
            return self.env.ref('account.invoice_supplier_form').id
        else:
            return self.env.ref('account.invoice_form').id

    def _prepare_tax_line_vals(self, line, tax, tax_ids):
        ''' Prepare values to create an account.invoice.tax line.
        :param line:    An account.invoice.line record.
        :param tax:     Tax values outputted by compute_all() in account.tax.
        :param taxes:   A list of account.tax ids affecting the tax base amount.
        :return:        The account.invoice.tax values to create a new record.
        '''
        vals = {
            'invoice_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
            'account_id': tax['account_id'] or line.account_id.id,
            'analytic_tag_ids': tax['analytic'] and line.analytic_tag_ids.ids or False,
            'tax_ids': tax_ids and [(6, None, tax_ids)] or False,
            'tax_repartition_line_id': tax.get('tax_repartition_line_id'), # For base amount, we let this field empty
        }

        # If the taxes generate moves on the same financial account as the invoice line,
        # propagate the analytic account from the invoice line to the tax line.
        # This is necessary in situations were (part of) the taxes cannot be reclaimed,
        # to ensure the tax move is allocated to the proper analytic account.
        if not vals.get('account_analytic_id') and line.account_analytic_id and vals['account_id'] == line.account_id.id:
            vals['account_analytic_id'] = line.account_analytic_id.id
        return vals

    @api.multi
    def get_taxes_values(self, tax_group_fields=False):
        def is_tax_affecting_base_amount(tax):
            return (tax.amount_type not in ('group', 'division') and tax.include_base_amount and tax.price_include)\
                   or (tax.amount_type == 'division' and tax.include_base_amount and not tax.price_include)
        # Avoid redundant browsing.
        tax_map = dict((t.id, t) for t in self.invoice_line_ids.mapped('invoice_line_tax_ids'))
        default_tax_group_fields = set(['amount', 'base'])
        if tax_group_fields:
            default_tax_group_fields |= set(tax_group_fields)
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue

            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id, is_refund=self.type in ('in_refund', 'out_refund'))['taxes']

            affecting_base_tax_ids = []
            for tax_vals in taxes:
                # Retrieve the tax record (not in tax_vals when dealing with group of taxes).
                if tax_map.get(tax_vals['id']):
                    tax = tax_map[tax_vals['id']]
                else:
                    tax = tax_map[tax_vals['id']] = self.env['account.tax'].browse(tax_vals['id'])

                val = self._prepare_tax_line_vals(line, tax_vals, affecting_base_tax_ids)
                key = tax.get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['base'] = round_curr(val['base'])
                else:
                    for field in default_tax_group_fields:
                        tax_grouped[key][field] += round_curr(val.get(field)) or 0

                if tax.amount_type == "group":
                    affecting_base_tax_ids += tax.children_tax_ids.filtered(lambda t: is_tax_affecting_base_amount(t)).ids
                elif is_tax_affecting_base_amount(tax):
                    affecting_base_tax_ids.append(tax.id)

        return tax_grouped

    @api.multi
    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        """ Reconcile payable/receivable lines from the invoice with payment_line """
        line_to_reconcile = self.env['account.move.line']
        for inv in self:
            line_to_reconcile += inv.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        return (line_to_reconcile + payment_line).reconcile(writeoff_acc_id, writeoff_journal_id)

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
            amount_currency = self.company_id.currency_id._convert(credit_aml.balance, self.currency_id, self.company_id, credit_aml.date or fields.Date.today())
            credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                'amount_currency': amount_currency,
                'currency_id': self.currency_id.id})
        if credit_aml.payment_id:
            credit_aml.payment_id.write({'invoice_ids': [(4, self.id, None)]})
        return self.register_payment(credit_aml)

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
                currency = self.currency_id
                date = self._get_currency_rate_date() or fields.Date.context_today(self)
                if not (line.get('currency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = currency.round(line['price'])
                    line['price'] = currency._convert(line['price'], company_currency, self.company_id, date)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
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
            if not line.account_id:
                continue
            if line.quantity==0:
                continue

            taxes_to_flatten = line.invoice_line_tax_ids
            flattened_taxes = self.env['account.tax']
            while taxes_to_flatten:
                tax = taxes_to_flatten[0]
                taxes_to_flatten -= tax
                flattened_taxes += tax
                taxes_to_flatten += tax.children_tax_ids

            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

            tax_repartition_field_name = 'invoice_repartition_line_ids' if line.invoice_type in ('in_invoice', 'out_invoice') else 'refund_repartition_line_ids'
            tag_ids = flattened_taxes.mapped(tax_repartition_field_name).filtered(lambda x: x.repartition_type == 'base').mapped('tag_ids.id')
            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': line.price_subtotal,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'analytic_tag_ids': analytic_tag_ids,
                'tax_ids': [(6, 0, flattened_taxes.ids)],
                'invoice_id': self.id,
                'tag_ids': [(6, 0, tag_ids)],
            }
            res.append(move_line_dict)
        return res

    def tax_line_move_line_get(self):
        self.ensure_one()

        res = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            if tax_line.amount_total:
                analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in tax_line.analytic_tag_ids]
                res.append({
                    'invoice_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount_total,
                    'quantity': 1,
                    'price': tax_line.amount_total,
                    'account_id': tax_line.account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'analytic_tag_ids': analytic_tag_ids,
                    'invoice_id': self.id,
                    'tax_ids': tax_line.tax_ids and [(6, 0, tax_line.tax_ids.ids)] or False, # We don't pass an empty recordset here, as it would reset the tax_exibility of the line, due to the condition in account.move.line's create
                    'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
                    'tag_ids': [(6, 0, tax_line.tax_repartition_line_id.tag_ids.ids)],
                })
        return res

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        return "%s-%s-%s-%s-%s-%s-%s" % (
            invoice_line['account_id'],
            invoice_line.get('tax_ids', 'False'),
            invoice_line.get('tax_line_id', 'False'),
            invoice_line.get('product_id', 'False'),
            invoice_line.get('analytic_account_id', 'False'),
            invoice_line.get('date_maturity', 'False'),
            invoice_line.get('analytic_tag_ids', 'False'),
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
                    line2[tmp]['amount_currency'] += l['amount_currency']
                    line2[tmp]['analytic_line_ids'] += l['analytic_line_ids']
                    qty = l.get('quantity')
                    if qty:
                        line2[tmp]['quantity'] = line2[tmp].get('quantity', 0.0) + qty
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
            if not inv.invoice_line_ids.filtered(lambda line: line.account_id):
                raise UserError(_('Please add at least one invoice line.'))
            if inv.move_id:
                continue
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)

            name = inv.name or ''
            if inv.payment_term_id:
                totlines = inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)
                res_amount_currency = total_currency
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency._convert(t[1], inv.currency_id, inv.company_id, inv._get_currency_rate_date() or fields.Date.today())
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
                        'invoice_id': inv.id
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
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_ref = inv.reference
            if inv.origin:
                if move_ref:
                    move_ref += ' (%s)' % inv.origin
                else:
                    move_ref = inv.origin
            move_vals = {
                'ref': move_ref,
                'line_ids': line,
                'journal_id': inv.journal_id.id,
                'date': date,
                'narration': inv.comment,
                'name': inv.number,
            }
            move = account_move.create(move_vals)
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.write(vals)
        return True

    @api.constrains('cash_rounding_id', 'tax_line_ids')
    def _check_cash_rounding(self):
        for inv in self:
            if inv.cash_rounding_id:
                rounding_amount = inv.cash_rounding_id.compute_difference(inv.currency_id, inv.amount_total)
                if rounding_amount != 0.0:
                    raise UserError(_('The cash rounding cannot be computed because the difference must '
                                      'be added on the biggest tax found and no tax are specified.\n'
                                      'Please set up a tax or change the cash rounding method.'))

    @api.multi
    def _check_duplicate_supplier_reference(self):
        for invoice in self:
            # refuse to validate a vendor bill/credit note if there already exists one with the same reference for the same partner,
            # because it's probably a double encoding of the same bill/credit note
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note."))

    @api.multi
    def invoice_validate(self):
        for invoice in self.filtered(lambda invoice: invoice.partner_id not in invoice.message_partner_ids):
            invoice.message_subscribe([invoice.partner_id.id])

        for invoice in self:
            vals = {'state': 'open'}
            if not invoice.date_invoice:
                vals['date_invoice'] = fields.Date.context_today(self)
            if not invoice.date_due:
                vals['date_due'] = vals.get('date_invoice', invoice.date_invoice)

            if (invoice.move_name and invoice.move_name != '/'):
                new_name = invoice.move_name
            else:
                new_name = False
                journal = invoice.journal_id
                if journal.sequence_id:
                    # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                    sequence = journal.sequence_id
                    if invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                        if not journal.refund_sequence_id:
                            raise UserError(_('Please define a sequence for the credit notes'))
                        sequence = journal.refund_sequence_id

                    new_name = sequence.with_context(ir_sequence_date=invoice.date or invoice.date_invoice).next_by_id()
                else:
                    raise UserError(_('Please define a sequence on the journal.'))
            #give the invoice its number directly as it's needed in _get_computed_reference()
            invoice.number = new_name

            # Auto-compute reference, if not already existing and if configured on company
            if not invoice.reference and invoice.type == 'out_invoice':
                vals['reference'] = invoice._get_computed_reference()

            invoice.write(vals)

        self._check_duplicate_supplier_reference()
        return True

    @api.model
    def line_get_convert(self, line, part):
        return self.env['product.product']._convert_prepared_anglosaxon_line(line, part)

    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            #unreconcile all journal items of the invoice, since the cancellation will unlink them anyway
            inv.move_id.line_ids.filtered(lambda x: x.account_id.reconcile).remove_move_reconcile()

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
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.number or TYPES[inv.type], inv.name or '')))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        invoice_ids = []
        if name:
            invoice_ids = self._search([('number', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not invoice_ids:
            invoice_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(invoice_ids).name_get()

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'analytic_tag_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    def _get_refund_common_fields(self):
        return ['partner_id', 'payment_term_id', 'account_id', 'currency_id', 'journal_id']

    @api.model
    def _get_refund_prepare_fields(self):
        return ['name', 'reference', 'comment', 'date_due']

    @api.model
    def _get_refund_modify_read_fields(self):
        read_fields = ['type', 'number', 'invoice_line_ids', 'tax_line_ids',
                       'date']
        return self._get_refund_common_fields() + self._get_refund_prepare_fields() + read_fields

    @api.model
    def _get_refund_copy_fields(self):
        copy_fields = ['company_id', 'user_id', 'fiscal_position_id']
        return self._get_refund_common_fields() + self._get_refund_prepare_fields() + copy_fields

    def _get_currency_rate_date(self):
        return self.date or self.date_invoice

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new credit note from the invoice.
            This method may be overridden to implement custom
            credit note generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice as credit note
            :param string date_invoice: credit note creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the credit note from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the credit note
        """
        values = {}
        for field in self._get_refund_copy_fields():
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

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
        values['payment_term_id'] = False
        values['refund_invoice_id'] = invoice.id

        if values['type'] == 'in_refund':
            partner_bank_result = self._get_partner_bank_id(values['company_id'])
            if partner_bank_result:
                values['partner_bank_id'] = partner_bank_result.id

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
            refund_invoice = self.create(values)
            if invoice.type == 'out_invoice':
                message = _("This customer invoice credit note has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s") % (invoice.id, invoice.number, description)
            else:
                message = _("This vendor bill credit note has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s") % (invoice.id, invoice.number, description)

            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices

    def _prepare_payment_vals(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None, communication=None):
        payment_type = self.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        if payment_type == 'inbound':
            payment_method = self.env.ref('account.account_payment_method_manual_in')
            journal_payment_methods = pay_journal.inbound_payment_method_ids
        else:
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            journal_payment_methods = pay_journal.outbound_payment_method_ids

        if not communication:
            communication = self.type in ('in_invoice', 'in_refund') and self.reference or self.number
            if self.origin:
                communication = '%s (%s)' % (communication, self.origin)

        payment_vals = {
            'invoice_ids': [(6, 0, self.ids)],
            'amount': pay_amount or self.residual,
            'payment_date': date or fields.Date.context_today(self),
            'communication': communication,
            'partner_id': self.partner_id.id,
            'partner_type': self.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
            'journal_id': pay_journal.id,
            'payment_type': payment_type,
            'payment_method_id': payment_method.id,
            'payment_difference_handling': writeoff_acc and 'reconcile' or 'open',
            'writeoff_account_id': writeoff_acc and writeoff_acc.id or False,
        }
        return payment_vals

    @api.multi
    def pay_and_reconcile(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None):
        """ Create and post an account.payment for the invoice self, which creates a journal entry that reconciles the invoice.

            :param pay_journal: journal in which the payment entry will be created
            :param pay_amount: amount of the payment to register, defaults to the residual of the invoice
            :param date: payment date, defaults to fields.Date.context_today(self)
            :param writeoff_acc: account in which to create a writeoff if pay_amount < self.residual, so that the invoice is fully paid
        """
        if isinstance(pay_journal, int):
            pay_journal = self.env['account.journal'].browse([pay_journal])
        assert len(self) == 1, "Can only pay one invoice at a time."

        payment_vals = self._prepare_payment_vals(pay_journal, pay_amount=pay_amount, date=date, writeoff_acc=writeoff_acc)
        payment = self.env['account.payment'].create(payment_vals)
        payment.post()

        return True

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'paid' and self.type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.mt_invoice_paid')
        elif 'state' in init_values and self.state == 'open' and self.type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.mt_invoice_validated')
        elif 'state' in init_values and self.state == 'draft' and self.type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.mt_invoice_created')
        return super(AccountInvoice, self)._track_subtype(init_values)

    def _amount_by_group(self):
        for invoice in self:
            currency = invoice.currency_id or invoice.company_id.currency_id
            fmt = partial(formatLang, invoice.with_context(lang=invoice.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in invoice.tax_line_ids:
                tax = line.tax_id
                group_key = (tax.tax_group_id, tax.amount_type, tax.amount)
                res.setdefault(group_key, {'base': 0.0, 'amount': 0.0})
                res[group_key]['amount'] += line.amount_total
                res[group_key]['base'] += line.base
            res = sorted(res.items(), key=lambda l: l[0][0].sequence)
            invoice.amount_by_group = [(
                r[0][0].name, r[1]['amount'], r[1]['base'],
                fmt(r[1]['amount']), fmt(r[1]['base']),
                len(res),
            ) for r in res]

    @api.multi
    def preview_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _get_intrastat_country_id(self):
        return self.partner_id.country_id.id

class AccountInvoiceLine(models.Model):
    _name = "account.invoice.line"
    _description = "Invoice Line"
    _order = "invoice_id,sequence,id"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice', 'invoice_id.date')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id, is_refund=self.invoice_id.type in ('in_refund', 'out_refund'))
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            currency = self.invoice_id.currency_id
            date = self.invoice_id._get_currency_rate_date()
            price_subtotal_signed = currency._convert(price_subtotal_signed, self.invoice_id.company_id.currency_id, self.company_id or self.env.user.company_id, date or fields.Date.today())
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign

    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            if self._context.get('type') in ('out_invoice', 'in_refund'):
                return journal.default_credit_account_id.id
            return journal.default_debit_account_id.id

    def _get_price_tax(self):
        for l in self:
            l.price_tax = l.price_total - l.price_subtotal

    name = fields.Text(string='Description', required=True)
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.")
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
        ondelete='cascade', index=True)
    invoice_type = fields.Selection(related='invoice_id.type', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
        ondelete='set null', index=True, oldname='uos_id')
    product_id = fields.Many2one('product.product', string='Product',
        ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)],
        default=_default_account,
        help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Monetary(string='Amount (without Taxes)',
        store=True, readonly=True, compute='_compute_price', help="Total amount without taxes")
    price_total = fields.Monetary(string='Amount (with Taxes)',
        store=True, readonly=True, compute='_compute_price', help="Total amount with taxes")
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit note.")
    price_tax = fields.Monetary(string='Tax Amount', compute='_get_price_tax', store=False)
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'),
        default=0.0)
    invoice_line_tax_ids = fields.Many2many('account.tax',
        'account_invoice_line_tax', 'invoice_line_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)], oldname='invoice_line_tax_id')
    account_analytic_id = fields.Many2one('account.analytic.account',
        string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    company_id = fields.Many2one('res.company', string='Company',
        related='invoice_id.company_id', store=True, readonly=True, related_sudo=False)
    partner_id = fields.Many2one('res.partner', string='Partner',
        related='invoice_id.partner_id', store=True, readonly=True, related_sudo=False)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, related_sudo=False, readonly=False)
    company_currency_id = fields.Many2one('res.currency', related='invoice_id.company_currency_id', readonly=True, related_sudo=False)
    is_rounding_line = fields.Boolean(string='Rounding Line', help='Is a rounding line in case of cash rounding.')

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountInvoiceLine, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('type'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='product_id']"):
                if self._context['type'] in ('in_invoice', 'in_refund'):
                    # Hack to fix the stable version 8.0 -> saas-12
                    # purchase_ok will be moved from purchase to product in master #13271
                    if 'purchase_ok' in self.env['product.template']._fields:
                        node.set('domain', "[('purchase_ok', '=', True)]")
                else:
                    node.set('domain', "[('sale_ok', '=', True)]")
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    def _set_currency(self):
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        if company and currency:
            if company.currency_id != currency:
                self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.invoice_id.date_invoice)).rate

    def _set_taxes(self):
        """ Used in on_change to set taxes and price"""
        self.ensure_one()
        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            taxes = self.product_id.taxes_id or self.account_id.tax_ids or self.invoice_id.company_id.account_sale_tax_id
        else:
            taxes = self.product_id.supplier_taxes_id or self.account_id.tax_ids or self.invoice_id.company_id.account_purchase_tax_id

        # Keep only taxes of the company
        company_id = self.company_id or self.env.user.company_id
        taxes = taxes.filtered(lambda r: r.company_id == company_id)

        self.invoice_line_tax_ids = fp_taxes = self.invoice_id.fiscal_position_id.map_tax(taxes, self.product_id, self.invoice_id.partner_id)

        fix_price = self.env['account.tax']._fix_tax_included_price
        if self.invoice_id.type in ('in_invoice', 'in_refund'):
            prec = self.env['decimal.precision'].precision_get('Product Price')
            if not self.price_unit or float_compare(self.price_unit, self.product_id.standard_price, precision_digits=prec) == 0:
                self.price_unit = fix_price(self.product_id.standard_price, taxes, fp_taxes)
                self._set_currency()
        else:
            self.price_unit = fix_price(self.product_id.lst_price, taxes, fp_taxes)
            self._set_currency()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        type = self.invoice_id.type

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner.'),
                }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            self_lang = self
            if part.lang:
                self_lang = self.with_context(lang=part.lang)

            product = self_lang.product_id
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()

            product_name = self_lang._get_invoice_line_name_from_product()
            if product_name != None:
                self.name = product_name

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}

    def _get_invoice_line_name_from_product(self):
        """ Returns the automatic name to give to the invoice line depending on
        the product it is linked to.
        """
        self.ensure_one()
        if not self.product_id:
            return ''
        invoice_type = self.invoice_id.type
        rslt = self.product_id.partner_ref
        if invoice_type in ('in_invoice', 'in_refund'):
            if self.product_id.description_purchase:
                rslt += '\n' + self.product_id.description_purchase
        else:
            if self.product_id.description_sale:
                rslt += '\n' + self.product_id.description_sale

        return rslt

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if not self.account_id:
            return
        if not self.product_id:
            fpos = self.invoice_id.fiscal_position_id
            default_tax = self.invoice_id.type in ('out_invoice', 'out_refund') and self.invoice_id.company_id.account_sale_tax_id or self.invoice_id.company_id.account_purchase_tax_id
            self.invoice_line_tax_ids = fpos.map_tax(self.account_id.tax_ids or default_tax, partner=self.partner_id).ids
        elif not self.price_unit:
            self._set_taxes()


    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        warning = {}
        result = {}
        if not self.uom_id:
            self.price_unit = 0.0

        if self.product_id and self.uom_id:
            if self.invoice_id.type in ('in_invoice', 'in_refund'):
                price_unit = self.product_id.standard_price
            else:
                price_unit = self.product_id.lst_price
            self.price_unit = self.product_id.uom_id._compute_price(price_unit, self.uom_id)
            self._set_currency()

            if self.product_id.uom_id.category_id.id != self.uom_id.category_id.id:
                warning = {
                    'title': _('Warning!'),
                    'message': _('The selected unit of measure has to be in the same category as the product unit of measure.'),
                }
                self.uom_id = self.product_id.uom_id.id
        if warning:
            result['warning'] = warning
        return result

    def _set_additional_fields(self, invoice):
        """ Some modules, such as Purchase, provide a feature to add automatically pre-filled
            invoice lines. However, these modules might not be aware of extra fields which are
            added by extensions of the accounting module.
            This method is intended to be overridden by these extensions, so that any new field can
            easily be auto-filled as well.
            :param invoice : account.invoice corresponding record
            :rtype line : account.invoice.line record
        """
        pass

    @api.multi
    def unlink(self):
        if self.filtered(lambda r: r.invoice_id and r.invoice_id.state != 'draft'):
            raise UserError(_('You can only delete an invoice line if the invoice is in draft state.'))
        return super(AccountInvoiceLine, self).unlink()

    def _prepare_invoice_line(self):
        data = {
            'name': self.name,
            'origin': self.origin,
            'uom_id': self.uom_id.id,
            'product_id': self.product_id.id,
            'account_id': self.account_id.id,
            'price_unit': self.price_unit,
            'quantity': self.quantity,
            'discount': self.discount,
            'account_analytic_id': self.account_analytic_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'invoice_line_tax_ids': self.invoice_line_tax_ids.ids
        }
        return data

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('display_type', self.default_get(['display_type'])['display_type']):
                vals.update(price_unit=0, account_id=False, quantity=0)
        return super(AccountInvoiceLine, self).create(vals_list)

    @api.multi
    def write(self, values):
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError("You cannot change the type of an invoice line. Instead you should delete the current line and create a new line of the proper type.")
        return super(AccountInvoiceLine, self).write(values)

    _sql_constraints = [
        ('accountable_required_fields',
            "CHECK(display_type IS NOT NULL OR account_id IS NOT NULL)",
            "Missing required account on accountable invoice line."),

        ('non_accountable_fields_null',
            "CHECK(display_type IS NULL OR (price_unit = 0 AND account_id IS NULL and quantity = 0))",
            "Forbidden unit price, account and quantity on non-accountable invoice line"),
    ]


class AccountInvoiceTax(models.Model):
    _name = "account.invoice.tax"
    _description = "Invoice Tax"
    _order = 'sequence, id desc'

    def _prepare_invoice_tax_val(self):
        self.ensure_one()
        return {
            'tax_id': self.tax_id.id,
            'account_id': self.account_id.id,
            'account_analytic_id': self.account_analytic_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids or False,
        }

    invoice_id = fields.Many2one('account.invoice', string='Invoice', ondelete='cascade', index=True)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict')
    tax_repartition_line_id = fields.Many2one(string="Originating Repartition Line", comodel_name='account.tax.repartition.line')
    account_id = fields.Many2one('account.account', string='Tax Account', required=True, domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    amount = fields.Monetary('Tax Amount')
    amount_rounding = fields.Monetary('Amount Delta')
    amount_total = fields.Monetary(string="Amount Total", compute='_compute_amount_total')
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, readonly=True)
    base = fields.Monetary(string='Base')
    tax_ids = fields.Many2many('account.tax', string='Affecting Base Taxes',
        help='Taxes affecting the tax base amount applied before this one.')

    @api.depends('amount', 'amount_rounding')
    def _compute_amount_total(self):
        for tax_line in self:
            tax_line.amount_total = tax_line.amount + tax_line.amount_rounding
