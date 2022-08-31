# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from collections import defaultdict
from datetime import date, timedelta
from itertools import groupby
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import json
import re

#forbidden fields
INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')


def calc_check_digits(number):
    """Calculate the extra digits that should be appended to the number to make it a valid number.
    Source: python-stdnum iso7064.mod_97_10.calc_check_digits
    """
    number_base10 = ''.join(str(int(x, 36)) for x in number)
    checksum = int(number_base10) % 97
    return '%02d' % ((98 - 100 * checksum) % 97)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Journal Entries"
    _order = 'date desc, name desc, id desc'
    _mail_post_access = 'read'

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        move_type = self._context.get('default_type', 'entry')
        journal_type = 'general'
        if move_type in self.get_sale_types(include_receipts=True):
            journal_type = 'sale'
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_type = 'purchase'

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self._context['default_journal_id'])

            if move_type != 'entry' and journal.type != journal_type:
                raise UserError(_("Cannot create an invoice of type %s with a journal having %s as type.") % (move_type, journal.type))
        else:
            company_id = self._context.get('force_company', self._context.get('default_company_id', self.env.company.id))
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]

            journal = None
            if self._context.get('default_currency_id'):
                currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)

            if not journal:
                error_msg = _('Please define an accounting miscellaneous journal in your company')
                if journal_type == 'sale':
                    error_msg = _('Please define an accounting sale journal in your company')
                elif journal_type == 'purchase':
                    error_msg = _('Please define an accounting purchase journal in your company')
                raise UserError(error_msg)
        return journal

    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.context_today(self) if self._context.get('default_type', 'entry') in self.get_purchase_types(include_receipts=True) else False

    @api.model
    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        journal = self._get_default_journal()
        return journal.currency_id or journal.company_id.currency_id

    @api.model
    def _get_default_invoice_incoterm(self):
        ''' Get the default incoterm for invoice. '''
        return self.env.company.incoterm_id

    # ==== Business fields ====
    name = fields.Char(string='Number', required=True, readonly=True, copy=False, default='/')
    date = fields.Date(string='Date', required=True, index=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today)
    ref = fields.Char(string='Reference', copy=False)
    narration = fields.Text(string='Terms and Conditions')
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled')
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    type = fields.Selection(selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ], string='Type', required=True, store=True, index=True, readonly=True, tracking=True,
        default="entry", change_default=True)
    type_name = fields.Char('Type Name', compute='_compute_type_name')
    to_check = fields.Boolean(string='To Check', default=False,
        help='If this checkbox is ticked, it means that the user was not sure of all the related informations at the time of the creation of the move and that the move needs to be checked again.')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]",
        default=_get_default_journal)
    user_id = fields.Many2one(related='invoice_user_id', string='User')
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 store=True, readonly=True,
                                 compute='_compute_company_id')
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
        related='company_id.currency_id')
    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
        states={'draft': [('readonly', False)]},
        string='Currency',
        default=_get_default_currency)
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items', copy=True, readonly=True,
        states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
        states={'draft': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        string='Partner', change_default=True, ondelete="restrict")
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity', store=True, readonly=True,
        compute='_compute_commercial_partner_id', ondelete="restrict")

    # === Amount fields ===
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, tracking=True,
        compute='_compute_amount')
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True,
        compute='_compute_amount')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
        compute='_compute_amount',
        inverse='_inverse_amount_total')
    amount_residual = fields.Monetary(string='Amount Due', store=True,
        compute='_compute_amount')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_tax_signed = fields.Monetary(string='Tax Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_total_signed = fields.Monetary(string='Total Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_residual_signed = fields.Monetary(string='Amount Due Signed', store=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_by_group = fields.Binary(string="Tax amount by group",
        compute='_compute_invoice_taxes_by_group')

    # ==== Cash basis feature fields ====
    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation. "
             "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")

    # ==== Auto-post feature fields ====
    auto_post = fields.Boolean(string='Post Automatically', default=False,
        help='If this checkbox is ticked, this entry will be automatically posted at its date.')

    # ==== Reverse feature fields ====
    reversed_entry_id = fields.Many2one('account.move', string="Reversal of", readonly=True, copy=False)
    reversal_move_id = fields.One2many('account.move', 'reversed_entry_id')

    # =========================================================
    # Invoice related fields
    # =========================================================

    # ==== Business fields ====
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]", ondelete="restrict",
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. "
             "The default value comes from the customer.")
    invoice_user_id = fields.Many2one('res.users', copy=False, tracking=True,
        string='Salesperson',
        default=lambda self: self.env.user)
    user_id = fields.Many2one(string='User', related='invoice_user_id',
        help='Technical field used to fit the generic behavior in mail templates.')
    invoice_payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid')],
        string='Payment', store=True, readonly=True, copy=False, tracking=True,
        compute='_compute_amount')
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)]},
        default=_get_default_invoice_date)
    invoice_date_due = fields.Date(string='Due Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)]})
    invoice_payment_ref = fields.Char(string='Payment Reference', index=True, copy=False,
        help="The payment reference to set on journal items.")
    invoice_sent = fields.Boolean(readonly=True, default=False, copy=False,
        help="It indicates that the invoice has been sent.")
    invoice_origin = fields.Char(string='Origin', readonly=True, tracking=True,
        help="The document(s) that generated the invoice.")
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        readonly=True, states={'draft': [('readonly', False)]})
    # /!\ invoice_line_ids is just a subset of line_ids.
    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines',
        copy=False, readonly=True,
        domain=[('exclude_from_invoice_tab', '=', False)],
        states={'draft': [('readonly', False)]})
    invoice_partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
        compute="_compute_invoice_partner_bank_id", store=True, readonly=False,
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    invoice_incoterm_id = fields.Many2one('account.incoterms', string='Incoterm',
        default=_get_default_invoice_incoterm,
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

    # ==== Payment widget fields ====
    invoice_outstanding_credits_debits_widget = fields.Text(groups="account.group_account_invoice",
        compute='_compute_payments_widget_to_reconcile_info')
    invoice_payments_widget = fields.Text(groups="account.group_account_invoice",
        compute='_compute_payments_widget_reconciled_info')
    invoice_has_outstanding = fields.Boolean(groups="account.group_account_invoice",
        compute='_compute_payments_widget_to_reconcile_info')

    # ==== Vendor bill fields ====
    invoice_vendor_bill_id = fields.Many2one('account.move', store=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        string='Vendor Bill',
        help="Auto-complete from a past bill.")
    invoice_source_email = fields.Char(string='Source Email', tracking=True)
    invoice_partner_display_name = fields.Char(compute='_compute_invoice_partner_display_info', store=True)
    invoice_partner_icon = fields.Char(compute='_compute_invoice_partner_display_info', store=False, compute_sudo=True)

    # ==== Cash rounding fields ====
    invoice_cash_rounding_id = fields.Many2one('account.cash.rounding', string='Cash Rounding Method',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Defines the smallest coinage of the currency that can be used to pay by cash.')

    # ==== Fields to set the sequence, on the first invoice of the journal ====
    invoice_sequence_number_next = fields.Char(string='Next Number',
        compute='_compute_invoice_sequence_number_next',
        inverse='_inverse_invoice_sequence_number_next')
    invoice_sequence_number_next_prefix = fields.Char(string='Next Number Prefix',
        compute="_compute_invoice_sequence_number_next")

    # ==== Display purpose fields ====
    invoice_filter_type_domain = fields.Char(compute='_compute_invoice_filter_type_domain',
        help="Technical field used to have a dynamic domain on journal / taxes in the form view.")
    bank_partner_id = fields.Many2one('res.partner', help='Technical field to get the domain on the bank', compute='_compute_bank_partner_id')
    invoice_has_matching_suspense_amount = fields.Boolean(compute='_compute_has_matching_suspense_amount',
        groups='account.group_account_invoice',
        help="Technical field used to display an alert on invoices if there is at least a matching amount in any supsense account.")
    tax_lock_date_message = fields.Char(
        compute='_compute_tax_lock_date_message',
        help="Technical field used to display a message when the invoice's accounting date is prior of the tax lock date.")
    # Technical field to hide Reconciled Entries stat button
    has_reconciled_entries = fields.Boolean(compute="_compute_has_reconciled_entries")
    # ==== Hash Fields ====
    restrict_mode_hash_table = fields.Boolean(related='journal_id.restrict_mode_hash_table')
    secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False)
    inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True)

    @api.model
    def _field_will_change(self, record, vals, field_name):
        if field_name not in vals:
            return False
        field = record._fields[field_name]
        if field.type == 'many2one':
            return record[field_name].id != vals[field_name]
        if field.type == 'many2many':
            current_ids = set(record[field_name].ids)
            after_write_ids = set(record.new({field_name: vals[field_name]})[field_name].ids)
            return current_ids != after_write_ids
        if field.type == 'one2many':
            return True
        if field.type == 'monetary' and record[field.currency_field]:
            return not record[field.currency_field].is_zero(record[field_name] - vals[field_name])
        if field.type == 'float':
            record_value = field.convert_to_cache(record[field_name], record)
            to_write_value = field.convert_to_cache(vals[field_name], record)
            return record_value != to_write_value
        return record[field_name] != vals[field_name]

    @api.model
    def _cleanup_write_orm_values(self, record, vals):
        cleaned_vals = dict(vals)
        for field_name, value in vals.items():
            if not self._field_will_change(record, vals, field_name):
                del cleaned_vals[field_name]
        return cleaned_vals

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('invoice_date')
    def _onchange_invoice_date(self):
        if self.invoice_date:
            if not self.invoice_payment_term_id and (not self.invoice_date_due or self.invoice_date_due < self.invoice_date):
                self.invoice_date_due = self.invoice_date
            self.date = self.invoice_date
            self._onchange_currency()

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id and self.journal_id.currency_id:
            new_currency = self.journal_id.currency_id
            if new_currency != self.currency_id:
                self.currency_id = new_currency
                self._onchange_currency()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self = self.with_context(force_company=self.journal_id.company_id.id)

        warning = {}
        if self.partner_id:
            rec_account = self.partner_id.property_account_receivable_id
            pay_account = self.partner_id.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            p = self.partner_id
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
                    return {'warning': warning}

        if self.is_sale_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_payment_term_id or self.invoice_payment_term_id
            new_term_account = self.partner_id.commercial_partner_id.property_account_receivable_id
            self.narration = self.company_id.with_context(lang=self.partner_id.lang).invoice_terms
        elif self.is_purchase_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_supplier_payment_term_id or self.invoice_payment_term_id
            new_term_account = self.partner_id.commercial_partner_id.property_account_payable_id
        else:
            new_term_account = None

        for line in self.line_ids:
            line.partner_id = self.partner_id.commercial_partner_id

            if new_term_account and line.account_id.user_type_id.type in ('receivable', 'payable'):
                line.account_id = new_term_account

        self._compute_bank_partner_id()

        # Find the new fiscal position.
        delivery_partner_id = self._get_invoice_delivery_partner_id()
        new_fiscal_position_id = self.env['account.fiscal.position'].with_context(force_company=self.company_id.id).get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)
        self.fiscal_position_id = self.env['account.fiscal.position'].browse(new_fiscal_position_id)
        self._recompute_dynamic_lines()
        if warning:
            return {'warning': warning}

    @api.onchange('date', 'currency_id')
    def _onchange_currency(self):
        if not self.currency_id:
            return
        if self.is_invoice(include_receipts=True):
            company_currency = self.company_id.currency_id
            has_foreign_currency = self.currency_id and self.currency_id != company_currency

            for line in self._get_lines_onchange_currency():
                new_currency = has_foreign_currency and self.currency_id
                line.currency_id = new_currency
                line._onchange_currency()
        else:
            self.line_ids._onchange_currency()

        self._recompute_dynamic_lines(recompute_tax_base_amount=True)

    @api.onchange('invoice_payment_ref')
    def _onchange_invoice_payment_ref(self):
        for line in self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
            line.name = self.invoice_payment_ref

    @api.onchange('invoice_vendor_bill_id')
    def _onchange_invoice_vendor_bill(self):
        if self.invoice_vendor_bill_id:
            # Copy invoice lines.
            for line in self.invoice_vendor_bill_id.invoice_line_ids:
                copied_vals = line.copy_data()[0]
                copied_vals['move_id'] = self.id
                new_line = self.env['account.move.line'].new(copied_vals)
                new_line.recompute_tax_line = True

            # Copy payment terms.
            self.invoice_payment_term_id = self.invoice_vendor_bill_id.invoice_payment_term_id

            # Copy currency.
            if self.currency_id != self.invoice_vendor_bill_id.currency_id:
                self.currency_id = self.invoice_vendor_bill_id.currency_id

            # Reset
            self.invoice_vendor_bill_id = False
            self._recompute_dynamic_lines()

    @api.onchange('type')
    def _onchange_type(self):
        ''' Onchange made to filter the partners depending of the type. '''
        if self.is_sale_document(include_receipts=True):
            if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
                self.narration = self.company_id.invoice_terms or self.env.company.invoice_terms

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        current_invoice_lines = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
        others_lines = self.line_ids - current_invoice_lines
        if others_lines and current_invoice_lines - self.invoice_line_ids:
            others_lines[0].recompute_tax_line = True
        self.line_ids = others_lines + self.invoice_line_ids
        self._onchange_recompute_dynamic_lines()

    @api.onchange('line_ids', 'invoice_payment_term_id', 'invoice_date_due', 'invoice_cash_rounding_id', 'invoice_vendor_bill_id')
    def _onchange_recompute_dynamic_lines(self):
        self._recompute_dynamic_lines()

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        ''' Create the dictionary based on a tax line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_base_line'.
        :param tax_line:    An account.move.line being a tax line (with 'tax_repartition_line_id' set then).
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        return {
            'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
            'account_id': tax_line.account_id.id,
            'currency_id': tax_line.currency_id.id,
            'analytic_tag_ids': [(6, 0, tax_line.tax_line_id.analytic and tax_line.analytic_tag_ids.ids or [])],
            'analytic_account_id': tax_line.tax_line_id.analytic and tax_line.analytic_account_id.id,
            'tax_ids': [(6, 0, tax_line.tax_ids.ids)],
            'tag_ids': [(6, 0, tax_line.tag_ids.ids)],
            'partner_id': tax_line.partner_id.id,
        }

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        ''' Create the dictionary based on a base line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_tax_line'.
        :param base_line:   An account.move.line being a base line (that could contains something in 'tax_ids').
        :param tax_vals:    An element of compute_all(...)['taxes'].
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
        account = base_line._get_default_tax_account(tax_repartition_line) or base_line.account_id
        return {
            'tax_repartition_line_id': tax_vals['tax_repartition_line_id'],
            'account_id': account.id,
            'currency_id': base_line.currency_id.id,
            'analytic_tag_ids': [(6, 0, tax_vals['analytic'] and base_line.analytic_tag_ids.ids or [])],
            'analytic_account_id': tax_vals['analytic'] and base_line.analytic_account_id.id,
            'tax_ids': [(6, 0, tax_vals['tax_ids'])],
            'tag_ids': [(6, 0, tax_vals['tag_ids'])],
            'partner_id': base_line.partner_id.id,
        }

    def _get_tax_force_sign(self):
        """ The sign must be forced to a negative sign in case the balance is on credit
            to avoid negatif taxes amount.
            Example - Customer Invoice :
            Fixed Tax  |  unit price  |   discount   |  amount_tax  | amount_total |
            -------------------------------------------------------------------------
                0.67   |      115      |     100%     |    - 0.67    |      0
            -------------------------------------------------------------------------"""
        self.ensure_one()
        return -1 if self.type in ('out_invoice', 'in_refund', 'out_receipt') else 1

    def _preprocess_taxes_map(self, taxes_map):
        """ Useful in case we want to pre-process taxes_map """
        return taxes_map

    def _recompute_tax_lines(self, recompute_tax_base_amount=False, tax_rep_lines_to_recompute=None):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                tax_type = 'sale' if move.type.startswith('out_') else 'purchase'
                is_refund = move.type in ('out_refund', 'in_refund')
            else:
                handle_price_include = False
                quantity = 1.0
                price_unit_wo_discount = base_line.amount_currency if base_line.currency_id else base_line.balance
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)

            balance_taxes_res = base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id or base_line.company_currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.flatten_taxes_hierarchy().mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = self._tax_tags_need_inversion(move, is_refund, tax_type)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict
            if not recompute_tax_base_amount:
                line.tax_exigible = tax_exigible

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            tax_line = taxes_map_entry['tax_line']

            # The tax line is no longer used in any base lines, drop it.
            if tax_line and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= tax_line
                continue

            currency_id = taxes_map_entry['grouping_dict']['currency_id']
            currency = self.env['res.currency'].browse(currency_id) if currency_id else False
            conversion_date = self.date or fields.Date.context_today(self)

            # Don't create tax lines with zero balance.
            if (currency or self.company_currency_id).is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            if currency:
                tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, conversion_date)
            else:
                tax_base_amount = taxes_map_entry['tax_base_amount']

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            if currency:
                amount_currency = taxes_map_entry['amount']
                balance = currency._convert(amount_currency, self.company_currency_id, self.company_id, conversion_date)
            else:
                amount_currency = 0.0
                balance = taxes_map_entry['amount']

            to_write_on_line = {
                'amount_currency': amount_currency,
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                if tax_rep_lines_to_recompute and taxes_map_entry['tax_line'].tax_repartition_line_id not in tax_rep_lines_to_recompute:
                    continue

                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)

                if tax_rep_lines_to_recompute and tax_repartition_line not in tax_rep_lines_to_recompute:
                    continue

                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_id.currency_id.id,
                    'quantity': 1.0,
                    'date_maturity': False,
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line']._onchange_amount_currency()
                taxes_map_entry['tax_line']._onchange_balance()

    def _tax_tags_need_inversion(self, move, is_refund, tax_type):
        """ Tells whether the tax tags need to be inverted for a given move.

        :param move: the move for which we want to check inversion
        :param is_refund: whether or not the operation we want the inversion value for is a refund
        :param tax_type: the tax type of the operation we want the inversion value for

        :return: True if the tags need to be inverted
        """
        if move.type == 'entry':
            return (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
        return False

    @api.model
    def _get_base_amount_to_display(self, base_amount, tax_rep_ln, parent_tax_group=None):
        """ The base amount returned for taxes by compute_all has is the balance
        of the base line. For inbound operations, positive sign is on credit, so
        we need to invert the sign of this amount before displaying it.
        """
        source_tax = parent_tax_group or tax_rep_ln.invoice_tax_id or tax_rep_ln.refund_tax_id
        if (tax_rep_ln.invoice_tax_id and source_tax.type_tax_use == 'sale') \
           or (tax_rep_ln.refund_tax_id and source_tax.type_tax_use == 'purchase'):
            return -base_amount
        return base_amount

    def update_lines_tax_exigibility(self):
        if all(account.user_type_id.type not in {'payable', 'receivable'} for account in self.mapped('line_ids.account_id')):
            self.line_ids.write({'tax_exigible': True})
        else:
            tax_lines_caba = self.line_ids.filtered(lambda x: x.tax_line_id.tax_exigibility == 'on_payment')
            base_lines_caba = self.line_ids.filtered(lambda x: any(tax.tax_exigibility == 'on_payment'
                                                                   or (tax.amount_type == 'group'
                                                                       and 'on_payment' in tax.mapped('children_tax_ids.tax_exigibility'))
                                                               for tax in x.tax_ids))
            caba_lines = tax_lines_caba + base_lines_caba
            caba_lines.write({'tax_exigible': False})
            (self.line_ids - caba_lines).write({'tax_exigible': True})

    def _recompute_cash_rounding_lines(self):
        ''' Handle the cash rounding feature on invoices.

        In some countries, the smallest coins do not exist. For example, in Switzerland, there is no coin for 0.01 CHF.
        For this reason, if invoices are paid in cash, you have to round their total amount to the smallest coin that
        exists in the currency. For the CHF, the smallest coin is 0.05 CHF.

        There are two strategies for the rounding:

        1) Add a line on the invoice for the rounding: The cash rounding line is added as a new invoice line.
        2) Add the rounding in the biggest tax amount: The cash rounding line is added as a new tax line on the tax
        having the biggest balance.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _compute_cash_rounding(self, total_balance, total_amount_currency):
            ''' Compute the amount differences due to the cash rounding.
            :param self:                    The current account.move record.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        The amount differences both in company's currency & invoice's currency.
            '''
            if self.currency_id == self.company_id.currency_id:
                diff_balance = self.invoice_cash_rounding_id.compute_difference(self.currency_id, total_balance)
                diff_amount_currency = 0.0
            else:
                diff_amount_currency = self.invoice_cash_rounding_id.compute_difference(self.currency_id, total_amount_currency)
                diff_balance = self.currency_id._convert(diff_amount_currency, self.company_id.currency_id, self.company_id, self.date)
            return diff_balance, diff_amount_currency

        def _apply_cash_rounding(self, diff_balance, diff_amount_currency, cash_rounding_line):
            ''' Apply the cash rounding.
            :param self:                    The current account.move record.
            :param diff_balance:            The computed balance to set on the new rounding line.
            :param diff_amount_currency:    The computed amount in invoice's currency to set on the new rounding line.
            :param cash_rounding_line:      The existing cash rounding line.
            :return:                        The newly created rounding line.
            '''
            rounding_line_vals = {
                'debit': diff_balance > 0.0 and diff_balance or 0.0,
                'credit': diff_balance < 0.0 and -diff_balance or 0.0,
                'quantity': 1.0,
                'amount_currency': diff_amount_currency,
                'partner_id': self.partner_id.id,
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'company_id': self.company_id.id,
                'company_currency_id': self.company_id.currency_id.id,
                'is_rounding_line': True,
                'sequence': 9999,
            }

            if self.invoice_cash_rounding_id.strategy == 'biggest_tax':
                biggest_tax_line = None
                for tax_line in self.line_ids.filtered('tax_repartition_line_id'):
                    if not biggest_tax_line or tax_line.price_subtotal > biggest_tax_line.price_subtotal:
                        biggest_tax_line = tax_line

                # No tax found.
                if not biggest_tax_line:
                    return

                rounding_line_vals.update({
                    'name': _('%s (rounding)') % biggest_tax_line.name,
                    'account_id': biggest_tax_line.account_id.id,
                    'tax_repartition_line_id': biggest_tax_line.tax_repartition_line_id.id,
                    'tag_ids': [(6, 0, biggest_tax_line.tag_ids.ids)],
                    'tax_exigible': biggest_tax_line.tax_exigible,
                    'exclude_from_invoice_tab': True,
                })

            elif self.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                if diff_balance > 0.0:
                    account_id = self.invoice_cash_rounding_id._get_loss_account_id().id
                else:
                    account_id = self.invoice_cash_rounding_id._get_profit_account_id().id
                rounding_line_vals.update({
                    'name': self.invoice_cash_rounding_id.name,
                    'account_id': account_id,
                })

            # Create or update the cash rounding line.
            if cash_rounding_line:
                cash_rounding_line.update({
                    'amount_currency': rounding_line_vals['amount_currency'],
                    'debit': rounding_line_vals['debit'],
                    'credit': rounding_line_vals['credit'],
                    'account_id': rounding_line_vals['account_id'],
                })
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                cash_rounding_line = create_method(rounding_line_vals)

            if in_draft_mode:
                cash_rounding_line._onchange_amount_currency()
                cash_rounding_line._onchange_balance()

        existing_cash_rounding_line = self.line_ids.filtered(lambda line: line.is_rounding_line)

        # The cash rounding has been removed.
        if not self.invoice_cash_rounding_id:
            self.line_ids -= existing_cash_rounding_line
            return

        # The cash rounding strategy has changed.
        if self.invoice_cash_rounding_id and existing_cash_rounding_line:
            strategy = self.invoice_cash_rounding_id.strategy
            old_strategy = 'biggest_tax' if existing_cash_rounding_line.tax_line_id else 'add_invoice_line'
            if strategy != old_strategy:
                self.line_ids -= existing_cash_rounding_line
                existing_cash_rounding_line = self.env['account.move.line']

        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        others_lines -= existing_cash_rounding_line
        total_balance = sum(others_lines.mapped('balance'))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        diff_balance, diff_amount_currency = _compute_cash_rounding(self, total_balance, total_amount_currency)

        # The invoice is already rounded.
        if self.currency_id.is_zero(diff_balance) and self.currency_id.is_zero(diff_amount_currency):
            self.line_ids -= existing_cash_rounding_line
            return

        _apply_cash_rounding(self, diff_balance, diff_amount_currency, existing_cash_rounding_line)

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_context(force_company=self.journal_id.company_id.id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id != self.company_id.currency_id:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
                else:
                    # Single-currency.
                    return [(b[0], b[1], 0.0) for b in to_compute]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.invoice_payment_ref or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate._onchange_amount_currency()
                    candidate._onchange_balance()
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.invoice_payment_ref = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' Recompute all lines that depend on others.

        For example, tax lines depends on base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend on base lines or tax lines depending on the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending on the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            expected_tax_rep_lines = set()
            current_tax_rep_lines = set()
            inv_recompute_all_taxes = recompute_all_taxes
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids._origin.flatten_taxes_hierarchy().filtered(
                        lambda tax: (
                                tax.amount_type == 'fixed' and not invoice.company_id.currency_id.is_zero(tax.amount)
                                or not float_is_zero(tax.amount, precision_digits=4)
                        )
                    )
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines

            # Compute taxes.
            if inv_recompute_all_taxes:
                invoice._recompute_tax_lines()
            elif recompute_tax_base_amount:
                invoice._recompute_tax_lines(recompute_tax_base_amount=True)
            elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel'):
                invoice._recompute_tax_lines(tax_rep_lines_to_recompute=delta_tax_rep_lines)

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()

                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            move.company_id = move.journal_id.company_id or move.company_id or self.env.company

    def _get_lines_onchange_currency(self):
        # Override needed for COGS
        return self.line_ids

    def onchange(self, values, field_name, field_onchange):
        # OVERRIDE
        # As the dynamic lines in this model are quite complex, we need to ensure some computations are done exactly
        # at the beginning / at the end of the onchange mechanism. So, the onchange recursivity is disabled.
        return super(AccountMove, self.with_context(recursive_onchanges=False)).onchange(values, field_name, field_onchange)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('type')
    def _compute_type_name(self):
        type_name_mapping = {k: v for k, v in
                             self._fields['type']._description_selection(self.env)}
        replacements = {'out_invoice': _('Invoice'), 'out_refund': _('Credit Note')}

        for record in self:
            name = type_name_mapping[record.type]
            record.type_name = replacements.get(record.type, name)

    @api.depends('type')
    def _compute_invoice_filter_type_domain(self):
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.invoice_filter_type_domain = 'sale'
            elif move.is_purchase_document(include_receipts=True):
                move.invoice_filter_type_domain = 'purchase'
            else:
                move.invoice_filter_type_domain = False

    @api.depends('partner_id')
    def _compute_commercial_partner_id(self):
        for move in self:
            move.commercial_partner_id = move.partner_id.commercial_partner_id

    @api.depends('bank_partner_id')
    def _compute_invoice_partner_bank_id(self):
        for move in self:
            filtered_bank_partner_id = move.bank_partner_id.bank_ids.filtered(lambda bank: bank.company_id is False or bank.company_id == move.company_id)
            move.invoice_partner_bank_id = filtered_bank_partner_id and filtered_bank_partner_id[0]

    @api.depends('commercial_partner_id', 'type')
    def _compute_bank_partner_id(self):
        for move in self:
            if move.is_outbound():
                move.bank_partner_id = move.commercial_partner_id
            else:
                move.bank_partner_id = move.company_id.partner_id

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state')
    def _compute_amount(self):
        invoice_ids = [move.id for move in self if move.id and move.is_invoice(include_receipts=True)]
        self.env['account.payment'].flush(['state'])
        if invoice_ids:
            self._cr.execute(
                '''
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                UNION
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                ''', [tuple(invoice_ids), tuple(invoice_ids)]
            )
            in_payment_set = set(res[0] for res in self._cr.fetchall())
        else:
            in_payment_set = {}

        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.type == 'entry' else -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
            is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual

            # Compute 'invoice_payment_state'.
            if move.type == 'entry':
                move.invoice_payment_state = False
            elif move.state == 'posted' and is_paid:
                if move.id in in_payment_set:
                    move.invoice_payment_state = 'in_payment'
                else:
                    move.invoice_payment_state = 'paid'
            else:
                move.invoice_payment_state = 'not_paid'

    def _inverse_amount_total(self):
        for move in self:
            if len(move.line_ids) != 2 or move.is_invoice(include_receipts=True):
                continue

            to_write = []

            if move.currency_id != move.company_id.currency_id:
                amount_currency = abs(move.amount_total)
                balance = move.currency_id._convert(amount_currency, move.company_currency_id, move.company_id, move.date)
            else:
                balance = abs(move.amount_total)
                amount_currency = 0.0

            for line in move.line_ids:
                if float_compare(abs(line.balance), balance, precision_rounding=move.currency_id.rounding) != 0:
                    to_write.append((1, line.id, {
                        'debit': line.balance > 0.0 and balance or 0.0,
                        'credit': line.balance < 0.0 and balance or 0.0,
                        'amount_currency': line.balance > 0.0 and amount_currency or -amount_currency,
                    }))

            move.write({'line_ids': to_write})

    def _get_domain_matching_suspense_moves(self):
        self.ensure_one()
        domain = self.env['account.move.line']._get_suspense_moves_domain()
        domain += ['|', ('partner_id', '=?', self.partner_id.id), ('partner_id', '=', False)]
        if self.is_inbound():
            domain.append(('balance', '=', -self.amount_residual))
        else:
            domain.append(('balance', '=', self.amount_residual))
        return domain

    def _compute_has_matching_suspense_amount(self):
        for r in self:
            res = False
            if r.state == 'posted' and r.is_invoice() and r.invoice_payment_state == 'not_paid':
                domain = r._get_domain_matching_suspense_moves()
                #there are more than one but less than 5 suspense moves matching the residual amount
                if (0 < self.env['account.move.line'].search_count(domain) < 5):
                    domain2 = [
                        ('invoice_payment_state', '=', 'not_paid'),
                        ('state', '=', 'posted'),
                        ('amount_residual', '=', r.amount_residual),
                        ('type', '=', r.type)]
                    #there are less than 5 other open invoices of the same type with the same residual
                    if self.env['account.move'].search_count(domain2) < 5:
                        res = True
            r.invoice_has_matching_suspense_amount = res

    @api.depends('partner_id', 'invoice_source_email')
    def _compute_invoice_partner_display_info(self):
        for move in self:
            vendor_display_name = move.partner_id.display_name
            if not vendor_display_name:
                if move.invoice_source_email:
                    vendor_display_name = _('From: ') + move.invoice_source_email
                    move.invoice_partner_icon = '@'
                else:
                    vendor_display_name = _('Created by: %s') % (move.sudo().create_uid.name or self.env.user.name)
                    move.invoice_partner_icon = '#'
            else:
                move.invoice_partner_icon = False
            move.invoice_partner_display_name = vendor_display_name

    @api.depends('state', 'journal_id', 'date', 'invoice_date')
    def _compute_invoice_sequence_number_next(self):
        """ computes the prefix of the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        # Check user group.
        system_user = self.env.is_system()
        if not system_user:
            self.invoice_sequence_number_next_prefix = False
            self.invoice_sequence_number_next = False
            return

        # Check moves being candidates to set a custom number next.
        moves = self.filtered(lambda move: move.is_invoice() and move.name == '/')
        if not moves:
            self.invoice_sequence_number_next_prefix = False
            self.invoice_sequence_number_next = False
            return

        treated = self.browse()
        for key, group in groupby(moves, key=lambda move: (move.journal_id, move._get_sequence())):
            journal, sequence = key
            domain = [('journal_id', '=', journal.id), ('state', '=', 'posted')]
            if self.ids:
                domain.append(('id', 'not in', self.ids))
            if journal.type == 'sale':
                domain.append(('type', 'in', ('out_invoice', 'out_refund')))
            elif journal.type == 'purchase':
                domain.append(('type', 'in', ('in_invoice', 'in_refund')))
            else:
                continue
            if self.search_count(domain):
                continue

            for move in group:
                sequence_date = move.date or move.invoice_date
                prefix, dummy = sequence._get_prefix_suffix(date=sequence_date, date_range=sequence_date)
                number_next = sequence._get_current_sequence(sequence_date=sequence_date).number_next_actual
                move.invoice_sequence_number_next_prefix = prefix
                move.invoice_sequence_number_next = '%%0%sd' % sequence.padding % number_next
                treated |= move
        remaining = (self - treated)
        remaining.invoice_sequence_number_next_prefix = False
        remaining.invoice_sequence_number_next = False

    def _inverse_invoice_sequence_number_next(self):
        ''' Set the number_next on the sequence related to the invoice/bill/refund'''
        # Check user group.
        if not self.env.is_admin():
            return

        # Set the next number in the sequence.
        for move in self:
            if not move.invoice_sequence_number_next:
                continue
            sequence = move._get_sequence()
            nxt = re.sub("[^0-9]", '', move.invoice_sequence_number_next)
            result = re.match("(0*)([0-9]+)", nxt)
            if result and sequence:
                sequence_date = move.date or move.invoice_date
                date_sequence = sequence._get_current_sequence(sequence_date=sequence_date)
                date_sequence.number_next_actual = int(result.group(2))

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' or move.invoice_payment_state != 'not_paid' or not move.is_invoice(include_receipts=True):
                continue
            pay_term_line_ids = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [('account_id', 'in', pay_term_line_ids.mapped('account_id').ids),
                      '|', ('parent_state', '=', 'posted'), '&', ('parent_state', '=', 'draft'), ('journal_id.post_at', '=', 'bank_rec'),
                      ('partner_id', '=', move.commercial_partner_id.id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]

            if move.is_inbound():
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'move_id': move.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = move.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == move.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), move.currency_id, move.company_id,
                                                           line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=move.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, move.currency_id.decimal_places],
                        'payment_date': fields.Date.to_string(line.date),
                    })
                info['title'] = type_payment
                move.invoice_outstanding_credits_debits_widget = json.dumps(info)
                move.invoice_has_outstanding = True

    def _get_reconciled_info_JSON_values(self):
        self.ensure_one()
        foreign_currency = self.currency_id if self.currency_id != self.company_id.currency_id else False

        reconciled_vals = []
        pay_term_line_ids = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        partials = pay_term_line_ids.mapped('matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
        for partial in partials:
            counterpart_lines = partial.debit_move_id + partial.credit_move_id
            # In case we are in an onchange, line_ids is a NewId, not an integer. By using line_ids.ids we get the correct integer value.
            counterpart_line = counterpart_lines.filtered(lambda line: line.id not in self.line_ids.ids)

            if foreign_currency and partial.currency_id == foreign_currency:
                amount = partial.amount_currency
            else:
                amount = partial.company_currency_id._convert(partial.amount, self.currency_id, self.company_id, self.date)

            if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                continue

            ref = counterpart_line.move_id.name
            if counterpart_line.move_id.ref:
                ref += ' (' + counterpart_line.move_id.ref + ')'

            reconciled_vals.append({
                'name': counterpart_line.name,
                'journal_name': counterpart_line.journal_id.name,
                'amount': amount,
                'currency': self.currency_id.symbol,
                'digits': [69, self.currency_id.decimal_places],
                'position': self.currency_id.position,
                'date': counterpart_line.date,
                'payment_id': counterpart_line.id,
                'account_payment_id': counterpart_line.payment_id.id,
                'payment_method_name': counterpart_line.payment_id.payment_method_id.name if counterpart_line.journal_id.type == 'bank' else None,
                'move_id': counterpart_line.move_id.id,
                'ref': ref,
            })
        return reconciled_vals

    @api.depends('type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            if move.state != 'posted' or not move.is_invoice(include_receipts=True):
                move.invoice_payments_widget = json.dumps(False)
                continue
            reconciled_vals = move._get_reconciled_info_JSON_values()
            if reconciled_vals:
                info = {
                    'title': _('Less Payment'),
                    'outstanding': False,
                    'content': reconciled_vals,
                }
                move.invoice_payments_widget = json.dumps(info, default=date_utils.json_default)
            else:
                move.invoice_payments_widget = json.dumps(False)

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id')
    def _compute_invoice_taxes_by_group(self):
        for move in self:

            # Not working on something else than invoices.
            if not move.is_invoice(include_receipts=True):
                move.amount_by_group = []
                continue

            balance_multiplicator = -1 if move.is_inbound() else 1

            tax_lines = move.line_ids.filtered('tax_line_id')
            base_lines = move.line_ids.filtered('tax_ids')

            tax_group_mapping = defaultdict(lambda: {
                'base_lines': set(),
                'base_amount': 0.0,
                'tax_amount': 0.0,
            })

            # Compute base amounts.
            for base_line in base_lines:
                base_amount = balance_multiplicator * (base_line.amount_currency if base_line.currency_id else base_line.balance)

                for tax in base_line.tax_ids.flatten_taxes_hierarchy():

                    if base_line.tax_line_id.tax_group_id == tax.tax_group_id:
                        continue

                    tax_group_vals = tax_group_mapping[tax.tax_group_id]
                    if base_line not in tax_group_vals['base_lines']:
                        tax_group_vals['base_amount'] += base_amount
                        tax_group_vals['base_lines'].add(base_line)

            # Compute tax amounts.
            for tax_line in tax_lines:
                tax_amount = balance_multiplicator * (tax_line.amount_currency if tax_line.currency_id else tax_line.balance)
                tax_group_vals = tax_group_mapping[tax_line.tax_line_id.tax_group_id]
                tax_group_vals['tax_amount'] += tax_amount

            tax_groups = sorted(tax_group_mapping.keys(), key=lambda x: x.sequence)
            amount_by_group = []
            for tax_group in tax_groups:
                tax_group_vals = tax_group_mapping[tax_group]
                amount_by_group.append((
                    tax_group.name,
                    tax_group_vals['tax_amount'],
                    tax_group_vals['base_amount'],
                    formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=move.currency_id),
                    formatLang(self.env, tax_group_vals['base_amount'], currency_obj=move.currency_id),
                    len(tax_group_mapping),
                    tax_group.id
                ))
            move.amount_by_group = amount_by_group

    @api.model
    def _get_tax_key_for_group_add_base(self, line):
        """
        Useful for _compute_invoice_taxes_by_group
        must be consistent with _get_tax_grouping_key_from_tax_line
         @return list
        """
        # DEPRECATED: TO BE REMOVED IN MASTER
        return [line.tax_line_id.id]

    @api.depends('date', 'line_ids.debit', 'line_ids.credit', 'line_ids.tax_line_id', 'line_ids.tax_ids', 'line_ids.tag_ids')
    def _compute_tax_lock_date_message(self):
        for move in self:
            if move._affect_tax_report() and move.company_id.tax_lock_date and move.date and move.date <= move.company_id.tax_lock_date:
                move.tax_lock_date_message = _(
                    "The accounting date is prior to the tax lock date which is set on %s. "
                    "Then, this will be moved to the next available one during the invoice validation."
                    % format_date(self.env, move.company_id.tax_lock_date))
            else:
                move.tax_lock_date_message = False

    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------

    @api.constrains('line_ids', 'journal_id')
    def _validate_move_modification(self):
        if 'posted' in self.mapped('line_ids.payment_id.state'):
            raise ValidationError(_("You cannot modify a journal entry linked to a posted payment."))

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        moves = self.filtered(lambda move: move.state == 'posted')
        if not moves:
            return

        self.flush()

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
            SELECT move2.id
            FROM account_move move
            INNER JOIN account_move move2 ON
                move2.name = move.name
                AND move2.journal_id = move.journal_id
                AND move2.type = move.type
                AND move2.id != move.id
            WHERE move.id IN %s AND move2.state = 'posted'
        ''', [tuple(moves.ids)])
        res = self._cr.fetchone()
        if res:
            raise ValidationError(_('Posted journal entry must have an unique sequence number per company.'))

    @api.constrains('ref', 'type', 'partner_id', 'journal_id', 'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        moves = self.filtered(lambda move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        self.env["account.move"].flush([
            "ref", "type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush(["company_id"])
        self.env["res.partner"].flush(["commercial_partner_id"])

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
            SELECT move2.id
            FROM account_move move
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_partner partner ON partner.id = move.partner_id
            INNER JOIN account_move move2 ON
                move2.ref = move.ref
                AND move2.company_id = journal.company_id
                AND move2.commercial_partner_id = partner.commercial_partner_id
                AND move2.type = move.type
                AND (move.invoice_date is NULL OR move2.invoice_date = move.invoice_date)
                AND move2.id != move.id
            WHERE move.id IN %s
        ''', [tuple(moves.ids)])
        duplicated_moves = self.browse([r[0] for r in self._cr.fetchall()])
        if duplicated_moves:
            raise ValidationError(_('Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note:\n%s') % "\n".join(
                duplicated_moves.mapped(lambda m: "%(partner)s - %(ref)s - %(date)s" % {'ref': m.ref, 'partner': m.partner_id.display_name, 'date': format_date(self.env, m.date)})
            ))

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(['debit', 'credit', 'move_id'])
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))

    def _check_fiscalyear_lock_date(self):
        for move in self.filtered(lambda move: move.state == 'posted'):
            lock_date = max(move.company_id.period_lock_date or date.min, move.company_id.fiscalyear_lock_date or date.min)
            if self.user_has_groups('account.group_account_manager'):
                lock_date = move.company_id.fiscalyear_lock_date
            if move.date <= (lock_date or date.min):
                if self.user_has_groups('account.group_account_manager'):
                    message = _("You cannot add/modify entries prior to and inclusive of the lock date %s.") % format_date(self.env, lock_date)
                else:
                    message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % format_date(self.env, lock_date)
                raise UserError(message)
        return True

    @api.constrains('type', 'journal_id')
    def _check_journal_type(self):
        for record in self:
            journal_type = record.journal_id.type

            if record.is_sale_document() and journal_type != 'sale' or record.is_purchase_document() and journal_type != 'purchase':
                raise ValidationError(_("The chosen journal has a type that is not compatible with your invoice type. Sales operations should go to 'sale' journals, and purchase operations to 'purchase' ones."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def _move_autocomplete_invoice_lines_values(self):
        ''' This method recomputes dynamic lines on the current journal entry that include taxes, cash rounding
        and payment terms lines.
        '''
        self.ensure_one()

        line_currency = self.currency_id if self.currency_id != self.company_id.currency_id else False
        for line in self.line_ids.filtered(lambda l: not l.display_type):
            # Do something only on invoice lines.
            if line.exclude_from_invoice_tab:
                continue

            # Shortcut to load the demo data.
            # Doing line.account_id triggers a default_get(['account_id']) that could returns a result.
            # A section / note must not have an account_id set.
            if not line._cache.get('account_id') and not line._origin:
                line.account_id = line._get_computed_account()
                if not line.account_id:
                    if self.is_sale_document(include_receipts=True):
                        line.account_id = self.journal_id.default_credit_account_id
                    elif self.is_purchase_document(include_receipts=True):
                        line.account_id = self.journal_id.default_debit_account_id
            if line.product_id and not line._cache.get('name'):
                line.name = line._get_computed_name()

            # Compute the account before the partner_id
            # In case account_followup is installed
            # Setting the partner will get the account_id in cache
            # If the account_id is not in cache, it will trigger the default value
            # Which is wrong in some case
            # It's better to set the account_id before the partner_id
            # Ensure related fields are well copied.
            line.partner_id = self.partner_id.commercial_partner_id
            line.date = self.date
            line.recompute_tax_line = True
            line.currency_id = line_currency


        self.line_ids._onchange_price_subtotal()
        self._recompute_dynamic_lines(recompute_all_taxes=True)

        values = self._convert_to_write(self._cache)
        values.pop('invoice_line_ids', None)
        return values

    @api.model
    def _move_autocomplete_invoice_lines_create(self, vals_list):
        ''' During the create of an account.move with only 'invoice_line_ids' set and not 'line_ids', this method is called
        to auto compute accounting lines of the invoice. In that case, accounts will be retrieved and taxes, cash rounding
        and payment terms will be computed. At the end, the values will contains all accounting lines in 'line_ids'
        and the moves should be balanced.

        :param vals_list:   The list of values passed to the 'create' method.
        :return:            Modified list of values.
        '''
        new_vals_list = []
        for vals in vals_list:
            vals = dict(vals)

            if vals.get('invoice_date') and not vals.get('date'):
                vals['date'] = vals['invoice_date']

            default_type = vals.get('type') or self._context.get('default_type')
            ctx_vals = {}
            if default_type:
                ctx_vals['default_type'] = default_type
            if vals.get('journal_id'):
                ctx_vals['default_journal_id'] = vals['journal_id']
                # reorder the companies in the context so that the company of the journal
                # (which will be the company of the move) is the main one, ensuring all
                # property fields are read with the correct company
                journal_company = self.env['account.journal'].browse(vals['journal_id']).company_id
                allowed_companies = self._context.get('allowed_company_ids', journal_company.ids)
                reordered_companies = sorted(allowed_companies, key=lambda cid: cid != journal_company.id)
                ctx_vals['allowed_company_ids'] = reordered_companies
            self_ctx = self.with_context(**ctx_vals)
            vals = self_ctx._add_missing_default_values(vals)

            is_invoice = vals.get('type') in self.get_invoice_types(include_receipts=True)

            if 'line_ids' in vals:
                vals.pop('invoice_line_ids', None)
                new_vals_list.append(vals)
                continue

            if is_invoice and 'invoice_line_ids' in vals:
                vals['line_ids'] = vals['invoice_line_ids']

            vals.pop('invoice_line_ids', None)

            move = self_ctx.new(vals)
            new_vals_list.append(move._move_autocomplete_invoice_lines_values())

        return new_vals_list

    def _move_autocomplete_invoice_lines_write(self, vals):
        ''' During the write of an account.move with only 'invoice_line_ids' set and not 'line_ids', this method is called
        to auto compute accounting lines of the invoice. In that case, accounts will be retrieved and taxes, cash rounding
        and payment terms will be computed. At the end, the values will contains all accounting lines in 'line_ids'
        and the moves should be balanced.

        :param vals_list:   A python dict representing the values to write.
        :return:            True if the auto-completion did something, False otherwise.
        '''
        enable_autocomplete = 'invoice_line_ids' in vals and 'line_ids' not in vals and True or False

        if not enable_autocomplete:
            return False

        vals['line_ids'] = vals.pop('invoice_line_ids')
        for invoice in self:
            invoice_new = invoice.with_context(default_type=invoice.type, default_journal_id=invoice.journal_id.id).new(origin=invoice)
            invoice_new.update(vals)
            values = invoice_new._move_autocomplete_invoice_lines_values()
            values.pop('invoice_line_ids', None)
            invoice.write(values)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
            raise UserError(_('You cannot create a move already in the posted state. Please create a draft move and post it after.'))

        vals_list = self._move_autocomplete_invoice_lines_create(vals_list)
        rslt = super(AccountMove, self).create(vals_list)
        for i, vals in enumerate(vals_list):
            if 'line_ids' in vals:
                rslt[i].update_lines_tax_exigibility()
        return rslt

    def write(self, vals):
        for move in self:
            if (move.restrict_mode_hash_table and move.state == "posted" and set(vals).intersection(INTEGRITY_HASH_MOVE_FIELDS)):
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(INTEGRITY_HASH_MOVE_FIELDS))
            if (move.restrict_mode_hash_table and move.inalterable_hash and 'inalterable_hash' in vals) or (move.secure_sequence_number and 'secure_sequence_number' in vals):
                raise UserError(_('You cannot overwrite the values ensuring the inalterability of the accounting.'))
            if (move.name != '/' and 'journal_id' in vals and move.journal_id.id != vals['journal_id']):
                raise UserError(_('You cannot edit the journal of an account move if it has been posted once.'))

            # You can't change the date of a move being inside a locked period.
            if 'date' in vals and move.date != vals['date']:
                move._check_fiscalyear_lock_date()
                move.line_ids._check_tax_lock_date()

            # You can't post subtract a move to a locked period.
            if 'state' in vals and move.state == 'posted' and vals['state'] != 'posted':
                move._check_fiscalyear_lock_date()
                move.line_ids._check_tax_lock_date()

        if self._move_autocomplete_invoice_lines_write(vals):
            res = True
        else:
            vals.pop('invoice_line_ids', None)
            res = super(AccountMove, self.with_context(check_move_validity=False)).write(vals)

        # You can't change the date of a not-locked move to a locked period.
        # You can't post a new journal entry inside a locked period.
        if 'date' in vals or 'state' in vals:
            self._check_fiscalyear_lock_date()
            self.mapped('line_ids')._check_tax_lock_date()

        if ('state' in vals and vals.get('state') == 'posted') and self.restrict_mode_hash_table:
            for move in self.filtered(lambda m: not(m.secure_sequence_number or m.inalterable_hash)):
                new_number = move.journal_id.secure_sequence_id.next_by_id()
                vals_hashing = {'secure_sequence_number': new_number,
                                'inalterable_hash': move._get_new_hash(new_number)}
                res |= super(AccountMove, move).write(vals_hashing)

        # Ensure the move is still well balanced.
        if 'line_ids' in vals:
            if self._context.get('check_move_validity', True):
                self._check_balanced()
            self.update_lines_tax_exigibility()

        return res

    def unlink(self):
        for move in self:
            if move.name != '/' and not self._context.get('force_delete'):
                raise UserError(_("You cannot delete an entry which has been posted once."))
        self.line_ids.unlink()
        return super(AccountMove, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        rec = super().copy(default)
        # invoice_date is not copied but is the basis for currency rates and payment terms
        if rec.invoice_date != self.invoice_date:
            rec.with_context(check_move_validity=False)._onchange_invoice_date()
            rec._check_balanced()
        return rec

    @api.depends('name', 'state')
    def name_get(self):
        result = []
        for move in self:
            if self._context.get('name_groupby'):
                name = '**%s**, %s' % (format_date(self.env, move.date), move._get_move_display_name())
                if move.ref:
                    name += '     (%s)' % move.ref
                if move.partner_id.name:
                    name += ' - %s' % move.partner_id.name
            else:
                name = move._get_move_display_name(show_ref=True)
            result.append((move.id, name))
        return result

    def _creation_subtype(self):
        # OVERRIDE
        if self.type in ('out_invoice', 'out_refund', 'out_receipt'):
            return self.env.ref('account.mt_invoice_created')
        else:
            return super(AccountMove, self)._creation_subtype()

    def _track_subtype(self, init_values):
        # OVERRIDE to add custom subtype depending of the state.
        self.ensure_one()

        if not self.is_invoice(include_receipts=True):
            return super(AccountMove, self)._track_subtype(init_values)

        if 'invoice_payment_state' in init_values and self.invoice_payment_state == 'paid':
            return self.env.ref('account.mt_invoice_paid')
        elif 'state' in init_values and self.state == 'posted' and self.is_sale_document(include_receipts=True):
            return self.env.ref('account.mt_invoice_validated')
        return super(AccountMove, self)._track_subtype(init_values)

    def _get_creation_message(self):
        # OVERRIDE
        if not self.is_invoice(include_receipts=True):
            return super()._get_creation_message()
        return {
            'out_invoice': _('Invoice Created'),
            'out_refund': _('Credit Note Created'),
            'in_invoice': _('Vendor Bill Created'),
            'in_refund': _('Refund Created'),
            'out_receipt': _('Sales Receipt Created'),
            'in_receipt': _('Purchase Receipt Created'),
        }[self.type]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund', 'in_refund', 'in_invoice'] + (include_receipts and ['out_receipt', 'in_receipt'] or [])

    def is_invoice(self, include_receipts=False):
        return self.type in self.get_invoice_types(include_receipts)

    @api.model
    def get_sale_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund'] + (include_receipts and ['out_receipt'] or [])

    def is_sale_document(self, include_receipts=False):
        return self.type in self.get_sale_types(include_receipts)

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ['in_invoice', 'in_refund'] + (include_receipts and ['in_receipt'] or [])

    def is_purchase_document(self, include_receipts=False):
        return self.type in self.get_purchase_types(include_receipts)

    @api.model
    def get_inbound_types(self, include_receipts=True):
        return ['out_invoice', 'in_refund'] + (include_receipts and ['out_receipt'] or [])

    def is_inbound(self, include_receipts=True):
        return self.type in self.get_inbound_types(include_receipts)

    @api.model
    def get_outbound_types(self, include_receipts=True):
        return ['in_invoice', 'out_refund'] + (include_receipts and ['in_receipt'] or [])

    def is_outbound(self, include_receipts=True):
        return self.type in self.get_outbound_types(include_receipts)

    def _affect_tax_report(self):
        return any(line._affect_tax_report() for line in self.line_ids)

    def _get_invoice_reference_euro_invoice(self):
        """ This computes the reference based on the RF Creditor Reference.
            The data of the reference is the database id number of the invoice.
            For instance, if an invoice is issued with id 43, the check number
            is 07 so the reference will be 'RF07 43'.
        """
        self.ensure_one()
        base = self.id
        check_digits = calc_check_digits('{}RF'.format(base))
        reference = 'RF{} {}'.format(check_digits, " ".join(["".join(x) for x in zip_longest(*[iter(str(base))]*4, fillvalue="")]))
        return reference

    def _get_invoice_reference_euro_partner(self):
        """ This computes the reference based on the RF Creditor Reference.
            The data of the reference is the user defined reference of the
            partner or the database id number of the parter.
            For instance, if an invoice is issued for the partner with internal
            reference 'food buyer 654', the digits will be extracted and used as
            the data. This will lead to a check number equal to 00 and the
            reference will be 'RF00 654'.
            If no reference is set for the partner, its id in the database will
            be used.
        """
        self.ensure_one()
        partner_ref = self.partner_id.ref
        partner_ref_nr = re.sub('\D', '', partner_ref or '')[-21:] or str(self.partner_id.id)[-21:]
        partner_ref_nr = partner_ref_nr[-21:]
        check_digits = calc_check_digits('{}RF'.format(partner_ref_nr))
        reference = 'RF{} {}'.format(check_digits, " ".join(["".join(x) for x in zip_longest(*[iter(partner_ref_nr)]*4, fillvalue="")]))
        return reference

    def _get_invoice_reference_odoo_invoice(self):
        """ This computes the reference based on the Odoo format.
            We simply return the number of the invoice, defined on the journal
            sequence.
        """
        self.ensure_one()
        return self.name

    def _get_invoice_reference_odoo_partner(self):
        """ This computes the reference based on the Odoo format.
            The data used is the reference set on the partner or its database
            id otherwise. For instance if the reference of the customer is
            'dumb customer 97', the reference will be 'CUST/dumb customer 97'.
        """
        ref = self.partner_id.ref or str(self.partner_id.id)
        prefix = _('CUST')
        return '%s/%s' % (prefix, ref)

    def _get_invoice_computed_reference(self):
        self.ensure_one()
        if self.journal_id.invoice_reference_type == 'none':
            return ''
        else:
            ref_function = getattr(self, '_get_invoice_reference_{}_{}'.format(self.journal_id.invoice_reference_model, self.journal_id.invoice_reference_type))
            if ref_function:
                return ref_function()
            else:
                raise UserError(_('The combination of reference model and reference type on the journal is not implemented'))

    def _get_sequence(self):
        ''' Return the sequence to be used during the post of the current move.
        :return: An ir.sequence record or False.
        '''
        self.ensure_one()

        journal = self.journal_id
        if self.type in ('entry', 'out_invoice', 'in_invoice', 'out_receipt', 'in_receipt') or not journal.refund_sequence:
            return journal.sequence_id
        if not journal.refund_sequence_id:
            return
        return journal.refund_sequence_id

    def _get_move_display_name(self, show_ref=False):
        ''' Helper to get the display name of an invoice depending of its type.
        :param show_ref:    A flag indicating of the display name must include or not the journal entry reference.
        :return:            A string representing the invoice.
        '''
        self.ensure_one()
        draft_name = ''
        if self.state == 'draft':
            draft_name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Credit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Draft Entry'),
            }[self.type]
            if not self.name or self.name == '/':
                draft_name += ' (* %s)' % str(self.id)
            else:
                draft_name += ' ' + self.name
        return (draft_name or self.name) + (show_ref and self.ref and ' (%s%s)' % (self.ref[:50], '...' if len(self.ref) > 50 else '') or '')

    def _get_invoice_delivery_partner_id(self):
        ''' Hook allowing to retrieve the right delivery address depending of installed modules.
        :return: A res.partner record's id representing the delivery address.
        '''
        self.ensure_one()
        return self.partner_id.address_get(['delivery'])['delivery']

    def _get_invoice_intrastat_country_id(self):
        ''' Hook allowing to retrieve the intrastat country depending of installed modules.
        :return: A res.country record's id.
        '''
        self.ensure_one()
        return self.partner_id.country_id.id

    def _get_cash_basis_matched_percentage(self):
        """Compute the percentage to apply for cash basis method. This value is relevant only for moves that
        involve journal items on receivable or payable accounts.
        """
        self.ensure_one()
        query = '''
            SELECT
            (
                SELECT COALESCE(SUM(line.balance), 0.0)
                FROM account_move_line line
                JOIN account_account account ON account.id = line.account_id
                JOIN account_account_type account_type ON account_type.id = account.user_type_id
                WHERE line.move_id = %s AND account_type.type IN ('receivable', 'payable')
            ) AS total_amount,
            (
                SELECT COALESCE(SUM(partial.amount), 0.0)
                FROM account_move_line line
                JOIN account_account account ON account.id = line.account_id
                JOIN account_account_type account_type ON account_type.id = account.user_type_id
                LEFT JOIN account_partial_reconcile partial ON
                    partial.debit_move_id = line.id
                    OR
                    partial.credit_move_id = line.id
                WHERE line.move_id = %s AND account_type.type IN ('receivable', 'payable')
            ) AS total_reconciled
        '''
        params = [self.id, self.id]
        self._cr.execute(query, params)
        total_amount, total_reconciled = self._cr.fetchone()
        currency = self.company_id.currency_id
        if float_is_zero(total_amount, precision_rounding=currency.rounding):
            return 1.0
        else:
            return abs(currency.round(total_reconciled) / currency.round(total_amount))

    def _get_reconciled_payments(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        pay_term_line_ids = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        reconciled_amls = pay_term_line_ids.mapped('matched_debit_ids.debit_move_id') + \
                          pay_term_line_ids.mapped('matched_credit_ids.credit_move_id')
        return reconciled_amls.mapped('payment_id')

    def _reverse_move_vals(self, default_values, cancel=True):
        ''' Reverse values passed as parameter being the copied values of the original journal entry.
        For example, debit / credit must be switched. The tax lines must be edited in case of refunds.

        :param default_values:  A copy_date of the original journal entry.
        :param cancel:          A flag indicating the reverse is made to cancel the original journal entry.
        :return:                The updated default_values.
        '''
        self.ensure_one()

        def compute_tax_repartition_lines_mapping(move_vals):
            ''' Computes and returns a mapping between the current repartition lines to the new expected one.
            :param move_vals:   The newly created invoice as a python dictionary to be passed to the 'create' method.
            :return:            A map invoice_repartition_line => refund_repartition_line.
            '''
            # invoice_repartition_line => refund_repartition_line
            mapping = {}

            for line_command in move_vals.get('line_ids', []):
                line_vals = line_command[2]  # (0, 0, {...})

                if line_vals.get('tax_line_id'):
                    # Tax line.
                    tax_ids = [line_vals['tax_line_id']]
                elif line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                    # Base line.
                    tax_ids = line_vals['tax_ids'][0][2]
                else:
                    continue

                for tax in self.env['account.tax'].browse(tax_ids).flatten_taxes_hierarchy():
                    for inv_rep_line, ref_rep_line in zip(tax.invoice_repartition_line_ids, tax.refund_repartition_line_ids):
                        mapping[inv_rep_line] = ref_rep_line
            return mapping

        def invert_tags_if_needed(repartition_line, tags):
            tax_type = repartition_line.tax_id.type_tax_use
            tags_need_inversion = self._tax_tags_need_inversion(
                self,
                (
                    (tax_type == 'purchase' and line_vals['credit'] > 0) or
                    (tax_type == 'sale' and line_vals['debit'] > 0)
                ),
                tax_type)
            if tags_need_inversion:
                return self.env['account.move.line']._revert_signed_tags(tags)
            return tags

        move_vals = self.with_context(include_business_fields=True).copy_data(default=default_values)[0]

        is_refund = False
        if move_vals['type'] in ('out_refund', 'in_refund'):
            is_refund = True
        elif move_vals['type'] == 'entry':
            base_lines = self.line_ids.filtered(lambda line: line.tax_ids)
            tax_type = set(base_lines.tax_ids.mapped('type_tax_use'))
            if tax_type == {'sale'} and sum(base_lines.mapped('debit')) == 0:
                is_refund = True
            elif tax_type == {'purchase'} and sum(base_lines.mapped('credit')) == 0:
                is_refund = True

        tax_repartition_lines_mapping = compute_tax_repartition_lines_mapping(move_vals) if is_refund else {}

        for line_command in move_vals.get('line_ids', []):
            line_vals = line_command[2]  # (0, 0, {...})

            # ==== Inverse debit / credit / amount_currency ====
            amount_currency = -line_vals.get('amount_currency', 0.0)
            balance = line_vals['credit'] - line_vals['debit']

            line_vals.update({
                'amount_currency': amount_currency,
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
            })

            if not is_refund or self.tax_cash_basis_rec_id:
                # We don't map tax repartition for non-refund operations, nor for cash basis entries.
                # Indeed, cancelling a cash basis entry usually happens when unreconciling and invoice,
                # in which case we always want the reverse entry to totally cancel the original one, keeping the same accounts,
                # tags and repartition lines
                continue

            # ==== Map tax repartition lines ====
            if line_vals.get('tax_repartition_line_id'):
                # Tax line.
                invoice_repartition_line = self.env['account.tax.repartition.line'].browse(line_vals['tax_repartition_line_id'])
                if invoice_repartition_line not in tax_repartition_lines_mapping:
                    raise UserError(_("It seems that the taxes have been modified since the creation of the journal entry. You should create the credit note manually instead."))
                refund_repartition_line = tax_repartition_lines_mapping[invoice_repartition_line]

                # Find the right account.
                account_id = self.env['account.move.line']._get_default_tax_account(refund_repartition_line).id
                if not account_id:
                    if not invoice_repartition_line.account_id:
                        # Keep the current account as the current one comes from the base line.
                        account_id = line_vals['account_id']
                    else:
                        tax = invoice_repartition_line.invoice_tax_id
                        base_line = self.line_ids.filtered(lambda line: tax in line.tax_ids.flatten_taxes_hierarchy())[0]
                        account_id = base_line.account_id.id

                tags = refund_repartition_line.tag_ids
                if line_vals.get('tax_ids'):
                    subsequent_taxes = self.env['account.tax'].browse(line_vals['tax_ids'][0][2])
                    tags += subsequent_taxes.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base').tag_ids

                tags = invert_tags_if_needed(refund_repartition_line, tags)
                line_vals.update({
                    'tax_repartition_line_id': refund_repartition_line.id,
                    'account_id': account_id,
                    'tag_ids': [(6, 0, tags.ids)],
                })
            elif line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                # Base line.
                taxes = self.env['account.tax'].browse(line_vals['tax_ids'][0][2]).flatten_taxes_hierarchy()
                invoice_repartition_lines = taxes\
                    .mapped('invoice_repartition_line_ids')\
                    .filtered(lambda line: line.repartition_type == 'base')
                refund_repartition_lines = invoice_repartition_lines\
                    .mapped(lambda line: tax_repartition_lines_mapping[line])

                tag_ids = []
                for refund_repartition_line in refund_repartition_lines:
                    tag_ids += invert_tags_if_needed(refund_repartition_line, refund_repartition_line.tag_ids).ids

                line_vals['tag_ids'] = [(6, 0, tag_ids)]
        return move_vals

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.

        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if not default_values_list:
            default_values_list = [{} for move in self]

        if cancel:
            lines = self.mapped('line_ids')
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()

        reverse_type_map = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'out_refund': 'entry',
            'in_invoice': 'in_refund',
            'in_refund': 'entry',
            'out_receipt': 'entry',
            'in_receipt': 'entry',
        }

        move_vals_list = []
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'type': reverse_type_map[move.type],
                'reversed_entry_id': move.id,
            })
            move_vals_list.append(move.with_context(move_reverse_cancel=cancel)._reverse_move_vals(default_values, cancel=cancel))

        reverse_moves = self.env['account.move'].create(move_vals_list)
        for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False, move_reverse_cancel=cancel)):
            # Update amount_currency if the date has changed.
            if move.date != reverse_move.date:
                for line in reverse_move.line_ids:
                    if line.currency_id:
                        line._onchange_currency()
            reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
        reverse_moves._check_balanced()

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel).post()
            for move, reverse_move in zip(self, reverse_moves):
                accounts = move.mapped('line_ids.account_id') \
                    .filtered(lambda account: account.reconcile or account.internal_type == 'liquidity')
                for account in accounts:
                    (move.line_ids + reverse_move.line_ids)\
                        .filtered(lambda line: line.account_id == account and line.balance)\
                        .reconcile()

        return reverse_moves

    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # OVERRIDE
        # Add custom behavior when receiving a new invoice through the mail's gateway.
        if (custom_values or {}).get('type', 'entry') not in ('out_invoice', 'in_invoice'):
            return super().message_new(msg_dict, custom_values=custom_values)

        def is_internal_partner(partner):
            # Helper to know if the partner is an internal one.
            return partner.user_ids and all(user.has_group('base.group_user') for user in partner.user_ids)

        extra_domain = False
        if custom_values.get('company_id'):
            extra_domain = ['|', ('company_id', '=', custom_values['company_id']), ('company_id', '=', False)]

        # Search for partners in copy.
        cc_mail_addresses = email_split(msg_dict.get('cc', ''))
        followers = [partner for partner in self._mail_find_partner_from_emails(cc_mail_addresses, extra_domain) if partner]

        # Search for partner that sent the mail.
        from_mail_addresses = email_split(msg_dict.get('from', ''))
        senders = partners = [partner for partner in self._mail_find_partner_from_emails(from_mail_addresses, extra_domain) if partner]

        # Search for partners using the user.
        if not senders:
            senders = partners = list(self._mail_search_on_user(from_mail_addresses))

        if partners:
            # Check we are not in the case when an internal user forwarded the mail manually.
            if is_internal_partner(partners[0]):
                # Search for partners in the mail's body.
                body_mail_addresses = set(email_re.findall(msg_dict.get('body')))
                company_id = custom_values.get('company_id', self.env.company.id)
                partners = [
                    partner
                    for partner in self._mail_find_partner_from_emails(body_mail_addresses, extra_domain)
                    if not is_internal_partner(partner) and partner.company_id.id in (False, company_id)
                ]

        # Little hack: Inject the mail's subject in the body.
        if msg_dict.get('subject') and msg_dict.get('body'):
            msg_dict['body'] = '<div><div><h3>%s</h3></div>%s</div>' % (msg_dict['subject'], msg_dict['body'])

        # Create the invoice.
        values = {
            'name': self.default_get(['name'])['name'],
            'invoice_source_email': from_mail_addresses[0],
            'partner_id': partners and partners[0].id or False,
        }
        move_ctx = self.with_context(default_type=custom_values['type'], default_journal_id=custom_values['journal_id'])
        move = super(AccountMove, move_ctx).message_new(msg_dict, custom_values=values)

        # Assign followers.
        all_followers_ids = set(partner.id for partner in followers + senders + partners if is_internal_partner(partner))
        move.message_subscribe(list(all_followers_ids))
        return move

    def post(self):
        # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))
        for move in self:
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: not line.display_type):
                raise UserError(_('You need to add a line before posting.'))
            if move.auto_post and move.date > fields.Date.today():
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s" % date_msg))

            if not move.partner_id:
                if move.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif move.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
                raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
            # environment.
            if not move.invoice_date and move.is_invoice(include_receipts=True):
                move.invoice_date = fields.Date.context_today(self)
                move.with_context(check_move_validity=False)._onchange_invoice_date()

            # When the accounting date is prior to the tax lock date, move it automatically to the next available date.
            # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
            # environment.
            if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (move.line_ids.tax_ids or move.line_ids.tag_ids):
                move.date = move.company_id.tax_lock_date + timedelta(days=1)
                move.with_context(check_move_validity=False)._onchange_currency()

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        self.mapped('line_ids').create_analytic_lines()
        for move in self.sorted(lambda m: (m.date, m.ref or '', m.id)):
            if move.auto_post and move.date > fields.Date.today():
                raise UserError(_("This move is configured to be auto-posted on {}".format(move.date.strftime(get_lang(self.env).date_format))))

            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = move.is_invoice() and move.line_ids.filtered(lambda aml: aml.partner_id != move.commercial_partner_id and not aml.display_type)
            if wrong_lines:
                wrong_lines.partner_id = move.commercial_partner_id.id

            move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

            to_write = {'state': 'posted'}

            if move.name == '/':
                # Get the journal's sequence.
                sequence = move._get_sequence()
                if not sequence:
                    raise UserError(_('Please define a sequence on your journal.'))

                # Consume a new number.
                to_write['name'] = sequence.with_context(ir_sequence_date=move.date).next_by_id()

            move.write(to_write)

            # Compute 'ref' for 'out_invoice'.
            if move.type == 'out_invoice' and not move.invoice_payment_ref:
                to_write = {
                    'invoice_payment_ref': move._get_invoice_computed_reference(),
                    'line_ids': []
                }
                for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
                    to_write['line_ids'].append((1, line.id, {'name': to_write['invoice_payment_ref']}))
                move.write(to_write)

            if move == move.company_id.account_opening_move_id and not move.company_id.account_bank_reconciliation_start:
                # For opening moves, we set the reconciliation date threshold
                # to the move's date if it wasn't already set (we don't want
                # to have to reconcile all the older payments -made before
                # installing Accounting- with bank statements)
                move.company_id.account_bank_reconciliation_start = move.date

        for move in self:
            if not move.partner_id: continue
            partners = (move.partner_id | move.partner_id.commercial_partner_id)
            if move.type.startswith('out_'):
                partners._increase_rank('customer_rank')
            elif move.type.startswith('in_'):
                partners._increase_rank('supplier_rank')
            else:
                continue

        # Trigger action for paid invoices in amount is zero
        self.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        ).action_invoice_paid()

        # Force balance check since nothing prevents another module to create an incorrect entry.
        # This is performed at the very end to avoid flushing fields before the whole processing.
        self._check_balanced()
        return True

    def action_reverse(self):
        action = self.env.ref('account.action_view_account_move_reversal').read()[0]

        if self.is_invoice():
            action['name'] = _('Credit Note')

        return action

    def action_post(self):
        if self.filtered(lambda x: x.journal_id.post_at == 'bank_rec').mapped('line_ids.payment_id').filtered(lambda x: x.state != 'reconciled'):
            raise UserError(_("A payment journal entry generated in a journal configured to post entries only when payments are reconciled with a bank statement cannot be manually posted. Those will be posted automatically after performing the bank reconciliation."))
        if self.env.context.get('default_type'):
            context = dict(self.env.context)
            del context['default_type']
            self = self.with_context(context)
        return self.post()

    def js_assign_outstanding_line(self, line_id):
        self.ensure_one()
        lines = self.env['account.move.line'].browse(line_id)
        lines += self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
        return lines.reconcile()

    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id:
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft'})

    def button_cancel(self):
        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'cancel'})

    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        lang = get_lang(self.env)
        if template and template.lang:
            lang = template._render_template(template.lang, 'account.move', self.id)
        else:
            lang = lang.code
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
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

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #get the only one exact previous move in the securisation sequence
        prev_move = self.search([('state', '=', 'posted'),
                                 ('company_id', '=', self.company_id.id),
                                 ('journal_id', '=', self.journal_id.id),
                                 ('secure_sequence_number', '!=', 0),
                                 ('secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_move and len(prev_move) != 1:
            raise UserError(
               _('An error occured when computing the inalterability. Impossible to get the unique previous posted journal entry.'))

        #build and return the hash
        return self._compute_hash(prev_move.inalterable_hash if prev_move else u'')

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""
        self.ensure_one()
        hash_string = sha256((previous_hash + self.string_to_hash).encode('utf-8'))
        return hash_string.hexdigest()

    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            return str(field_value)

        for move in self:
            values = {}
            for field in INTEGRITY_HASH_MOVE_FIELDS:
                values[field] = _getattrstring(move, field)

            for line in move.line_ids:
                for field in INTEGRITY_HASH_LINE_FIELDS:
                    k = 'line_%d_%s' % (line.id, field)
                    values[k] = _getattrstring(line, field)
            #make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            move.string_to_hash = dumps(values, sort_keys=True,
                                                ensure_ascii=True, indent=None,
                                                separators=(',',':'))

    def action_invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))

        self.filtered(lambda inv: not inv.invoice_sent).write({'invoice_sent': True})
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)

    def action_invoice_paid(self):
        ''' Hook to be overrided called when the invoice moves to the paid state. '''
        pass

    def action_open_matching_suspense_moves(self):
        self.ensure_one()
        domain = self._get_domain_matching_suspense_moves()
        ids = self.env['account.move.line'].search(domain).mapped('statement_line_id').ids
        action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
        action_context.update({'suspense_moves_mode': True})
        action_context.update({'statement_line_ids': ids})
        action_context.update({'partner_id': self.partner_id.id})
        action_context.update({'partner_name': self.partner_id.name})
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': action_context,
        }

    def action_invoice_register_payment(self):
        return self.env['account.payment']\
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
            .action_register_payment()

    def action_switch_invoice_into_refund_credit_note(self):
        if any(move.type not in ('in_invoice', 'out_invoice') for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            move.type = move.type.replace('invoice', 'refund')
            reversed_move = move._reverse_move_vals({}, False)
            new_invoice_line_ids = []
            for cmd, virtualid, line_vals in reversed_move['line_ids']:
                if not line_vals['exclude_from_invoice_tab']:
                    new_invoice_line_ids.append((0, 0,line_vals))
            if move.amount_total < 0:
                # Inverse all invoice_line_ids
                for cmd, virtualid, line_vals in new_invoice_line_ids:
                    line_vals.update({
                        'quantity' : -line_vals['quantity'],
                        'amount_currency' : -line_vals['amount_currency'],
                        'debit' : line_vals['credit'],
                        'credit' : line_vals['debit']
                    })
            move.write({'invoice_line_ids' : [(5, 0, 0)]})
            move.write({'invoice_line_ids' : new_invoice_line_ids})

    def _get_report_base_filename(self):
        return self._get_move_display_name()

    def preview_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _compute_access_url(self):
        super(AccountMove, self)._compute_access_url()
        for move in self.filtered(lambda move: move.is_invoice()):
            move.access_url = '/my/invoices/%s' % (move.id)

    @api.depends('line_ids')
    def _compute_has_reconciled_entries(self):
        for move in self:
            move.has_reconciled_entries = len(move.line_ids._reconciled_lines()) > 1

    def action_view_reverse_entry(self):
        self.ensure_one()

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        reverse_entries = self.env['account.move'].search([('reversed_entry_id', '=', self.id)])
        if len(reverse_entries) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': reverse_entries.id,
            })
        else:
            action.update({
                'view_mode': 'tree',
                'domain': [('id', 'in', reverse_entries.ids)],
            })
        return action

    @api.model
    def _autopost_draft_entries(self):
        ''' This method is called from a cron job.
        It is used to post entries such as those created by the module
        account_asset.
        '''
        records = self.search([
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.today()),
            ('auto_post', '=', True),
        ])
        for ids in self._cr.split_for_in_conditions(records.ids, size=1000):
            self.browse(ids).post()
            if not self.env.registry.in_test_mode():
                self._cr.commit()

    # offer the possibility to duplicate thanks to a button instead of a hidden menu, which is more visible
    def action_duplicate(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['context'] = dict(self.env.context)
        action['context']['form_view_initial_mode'] = 'edit'
        action['context']['view_no_maturity'] = False
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.copy().id
        return action

    def _notify_get_groups(self, msg_vals=None):
        """ Give access button to users and portal customer as portal is integrated
        in account. Customer and portal group have probably no right to see
        the document so they don't have the access button. """
        groups = super(AccountMove, self)._notify_get_groups(msg_vals=msg_vals)

        self.ensure_one()
        if self.type != 'entry':
            for group_name, _group_method, group_data in groups:
                if group_name == 'portal_customer':
                    group_data['has_button_access'] = True

        return groups

class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _description = "Journal Item"
    _order = "date desc, move_name desc, id"
    _check_company_auto = True

    # ==== Business fields ====
    move_id = fields.Many2one('account.move', string='Journal Entry',
        index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
        help="The move of this entry line.")
    move_name = fields.Char(string='Number', related='move_id.name', store=True, index=True)
    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False, group_operator='min')
    ref = fields.Char(related='move_id.ref', store=True, copy=False, index=True, readonly=True)
    parent_state = fields.Selection(related='move_id.state', store=True, readonly=True)
    journal_id = fields.Many2one(related='move_id.journal_id', store=True, index=True, copy=False)
    company_id = fields.Many2one(related='move_id.company_id', store=True, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    country_id = fields.Many2one(comodel_name='res.country', related='move_id.company_id.country_id')
    account_id = fields.Many2one('account.account', string='Account',
        index=True, ondelete="restrict", check_company=True,
        domain=[('deprecated', '=', False)])
    account_internal_type = fields.Selection(related='account_id.user_type_id.type', string="Internal Type", store=True, readonly=True)
    account_root_id = fields.Many2one(related='account_id.root_id', string="Account Root", store=True, readonly=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Label')
    quantity = fields.Float(string='Quantity',
        default=1.0, digits='Product Unit of Measure',
        help="The optional quantity expressed by this line, eg: number of product sold. "
             "The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', store=True,
        currency_field='company_currency_id',
        compute='_compute_balance',
        help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    amount_currency = fields.Monetary(string='Amount in Currency', store=True, copy=True,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True,
        currency_field='always_set_currency_id')
    price_total = fields.Monetary(string='Total', store=True, readonly=True,
        currency_field='always_set_currency_id')
    reconciled = fields.Boolean(compute='_amount_residual', store=True)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due Date', index=True,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    currency_id = fields.Many2one('res.currency', string='Currency')
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')

    # ==== Origin fields ====
    reconcile_model_id = fields.Many2one('account.reconcile.model', string="Reconciliation Model", copy=False, readonly=True)
    payment_id = fields.Many2one('account.payment', string="Originator Payment", copy=False,
        help="Payment that created this entry")
    statement_line_id = fields.Many2one('account.bank.statement.line',
        string='Bank statement line reconciled with this entry',
        index=True, copy=False, readonly=True)
    statement_id = fields.Many2one(related='statement_line_id.statement_id', store=True, index=True, copy=False,
        help="The bank statement used for bank reconciliation")

    # ==== Tax fields ====
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        context={'active_test': False},
        help="Taxes that apply on the base amount")
    tax_line_id = fields.Many2one('account.tax', string='Originator Tax', ondelete='restrict', store=True,
        compute='_compute_tax_line_id', help="Indicates that this journal item is a tax line")
    tax_group_id = fields.Many2one(related='tax_line_id.tax_group_id', string='Originator tax group',
        readonly=True, store=True,
        help='technical field for widget tax-group-custom-field')
    tax_base_amount = fields.Monetary(string="Base Amount", store=True, readonly=True,
        currency_field='company_currency_id')
    tax_exigible = fields.Boolean(string='Appears in VAT report', default=True, readonly=True,
        help="Technical field used to mark a tax line as exigible in the vat report or not (only exigible journal items"
             " are displayed). By default all new journal items are directly exigible, but with the feature cash_basis"
             " on taxes, some will become exigible only when the payment is recorded.")
    tax_repartition_line_id = fields.Many2one(comodel_name='account.tax.repartition.line',
        string="Originator Tax Repartition Line", ondelete='restrict', readonly=True,
        help="Tax repartition line that caused the creation of this move line, if any")
    tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    tax_audit = fields.Char(string="Tax Audit String", compute="_compute_tax_audit", store=True,
        help="Computed field, listing the tax grids impacted by this line, and the amount it applies to each of them.")

    # ==== Reconciliation fields ====
    amount_residual = fields.Monetary(string='Residual Amount', store=True,
        currency_field='company_currency_id',
        compute='_amount_residual',
        help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Monetary(string='Residual Amount in Currency', store=True,
        compute='_amount_residual',
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Matching #", copy=False, index=True, readonly=True)
    matched_debit_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', string='Matched Debits',
        help='Debit journal items that are matched with this journal item.', readonly=True)
    matched_credit_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', string='Matched Credits',
        help='Credit journal items that are matched with this journal item.', readonly=True)

    # ==== Analytic fields ====
    analytic_line_ids = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', index=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    # ==== Onchange / display purpose fields ====
    recompute_tax_line = fields.Boolean(store=False, readonly=True,
        help="Technical field used to know on which lines the taxes must be recomputed.")
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    is_rounding_line = fields.Boolean(help="Technical field used to retrieve the cash rounding line.")
    exclude_from_invoice_tab = fields.Boolean(help="Technical field used to exclude some lines from the invoice_line_ids tab in the form view.")
    always_set_currency_id = fields.Many2one('res.currency', string='Foreign Currency',
        compute='_compute_always_set_currency_id',
        help="Technical field used to compute the monetary field. As currency_id is not a required field, we need to use either the foreign currency, either the company one.")

    _sql_constraints = [
        (
            'check_credit_debit',
            'CHECK(credit + debit>=0 AND credit * debit=0)',
            'Wrong credit or debit value in accounting entry !'
        ),
        (
            'check_accountable_required_fields',
             "CHECK(COALESCE(display_type IN ('line_section', 'line_note'), 'f') OR account_id IS NOT NULL)",
             "Missing required account on accountable invoice line."
        ),
        (
            'check_non_accountable_fields_null',
             "CHECK(display_type NOT IN ('line_section', 'line_note') OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
             "Forbidden unit price, account and quantity on non-accountable invoice line"
        ),
        (
            'check_amount_currency_balance_sign',
            '''CHECK(
                currency_id IS NULL
                OR
                company_currency_id IS NULL
                OR
                (
                    (currency_id != company_currency_id)
                    AND
                    (
                        (balance > 0 AND amount_currency > 0)
                        OR (balance <= 0 AND amount_currency <= 0)
                        OR (balance >= 0 AND amount_currency >= 0)
                    )
                )
            )''',
            "The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited. Moreover, the currency field has to be left empty when the amount is expressed in the company currency."
        ),
    ]

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_tax_account(self, repartition_line):
        tax = repartition_line.invoice_tax_id or repartition_line.refund_tax_id
        if tax.tax_exigibility == 'on_payment':
            account = tax.cash_basis_transition_account_id
        else:
            account = repartition_line.account_id
        return account

    def _get_computed_name(self):
        self.ensure_one()

        if not self.product_id:
            return ''

        if self.partner_id.lang:
            product = self.product_id.with_context(lang=self.partner_id.lang)
        else:
            product = self.product_id

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if self.journal_id.type == 'sale':
            if product.description_sale:
                values.append(product.description_sale)
        elif self.journal_id.type == 'purchase':
            if product.description_purchase:
                values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        self.ensure_one()

        if not self.product_id:
            return 0.0
        if self.move_id.is_sale_document(include_receipts=True):
            document_type = 'sale'
        elif self.move_id.is_purchase_document(include_receipts=True):
            document_type = 'purchase'
        else:
            document_type = 'other'
        return self.product_id._get_tax_included_unit_price(
            self.move_id.company_id,
            self.move_id.currency_id,
            self.move_id.date,
            document_type,
            fiscal_position=self.move_id.fiscal_position_id,
            product_uom=self.product_uom_id
        )

    def _get_computed_account(self):
        self.ensure_one()
        self = self.with_context(force_company=self.move_id.journal_id.company_id.id)

        if not self.product_id:
            return

        fiscal_position = self.move_id.fiscal_position_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            return accounts['income'] or self.account_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            return accounts['expense'] or self.account_id

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        return tax_ids

    def _get_computed_uom(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id.uom_id
        return False

    def _set_price_and_tax_after_fpos(self):
        self.ensure_one()
        # Manage the fiscal position after that and adapt the price_unit.
        # E.g. mapping a price-included-tax to a price-excluded-tax must
        # remove the tax amount from the price_unit.
        # However, mapping a price-included tax to another price-included tax must preserve the balance but
        # adapt the price_unit to the new tax.
        # E.g. mapping a 10% price-included tax to a 20% price-included tax for a price_unit of 110 should preserve
        # 100 as balance but set 120 as price_unit.
        if self.tax_ids and self.move_id.fiscal_position_id and self.move_id.fiscal_position_id.tax_ids:
            price_subtotal = self._get_price_total_and_subtotal()['price_subtotal']
            self.tax_ids = self.move_id.fiscal_position_id.map_tax(
                self.tax_ids._origin,
                partner=self.move_id.partner_id)
            accounting_vals = self._get_fields_onchange_subtotal(
                price_subtotal=price_subtotal,
                currency=self.move_id.company_currency_id)
            balance = accounting_vals['debit'] - accounting_vals['credit']
            business_vals = self._get_fields_onchange_balance(balance=balance)
            if 'price_unit' in business_vals:
                self.price_unit = business_vals['price_unit']

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=self.price_unit if price_unit is None else price_unit,
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            currency=self.currency_id if currency is None else currency,
            product=self.product_id if product is None else product,
            partner=self.partner_id if partner is None else partner,
            taxes=self.tax_ids if taxes is None else taxes,
            move_type=self.move_id.type if move_type is None else move_type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(price_unit_wo_discount,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        self.ensure_one()
        return self._get_fields_onchange_subtotal_model(
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            move_type=self.move_id.type if move_type is None else move_type,
            currency=self.currency_id if currency is None else currency,
            company=self.move_id.company_id if company is None else company,
            date=self.move_id.date if date is None else date,
        )

    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        ''' This method is used to recompute the values of 'amount_currency', 'debit', 'credit' due to a change made
        in some business fields (affecting the 'price_subtotal' field).

        :param price_subtotal:  The untaxed amount.
        :param move_type:       The type of the move.
        :param currency:        The line's currency.
        :param company:         The move's company.
        :param date:            The move's date.
        :return:                A dictionary containing 'debit', 'credit', 'amount_currency'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        price_subtotal *= sign

        if currency and currency != company.currency_id:
            # Multi-currencies.
            balance = currency._convert(price_subtotal, company.currency_id, company, date)
            return {
                'amount_currency': price_subtotal,
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
            }
        else:
            # Single-currency.
            return {
                'amount_currency': 0.0,
                'debit': price_subtotal > 0.0 and price_subtotal or 0.0,
                'credit': price_subtotal < 0.0 and -price_subtotal or 0.0,
            }

    def _get_fields_onchange_balance(self, quantity=None, discount=None, balance=None, move_type=None, currency=None, taxes=None, price_subtotal=None, force_computation=False):
        self.ensure_one()
        return self._get_fields_onchange_balance_model(
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            balance=self.balance if balance is None else balance,
            move_type=self.move_id.type if move_type is None else move_type,
            currency=self.currency_id or self.move_id.currency_id if currency is None else currency,
            taxes=self.tax_ids if taxes is None else taxes,
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            force_computation=force_computation,
        )

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, balance, move_type, currency, taxes, price_subtotal, force_computation=False):
        ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
        in some accounting fields such as 'balance'.

        This method is a bit complex as we need to handle some special cases.
        For example, setting a positive balance with a 100% discount.

        :param quantity:        The current quantity.
        :param discount:        The current discount.
        :param balance:         The new balance.
        :param move_type:       The type of the move.
        :param currency:        The currency.
        :param taxes:           The applied taxes.
        :param price_subtotal:  The price_subtotal.
        :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        balance *= sign

        # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
        # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
        # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
        # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
        # issue.
        if not force_computation and currency.is_zero(balance - price_subtotal):
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            # Inverse taxes. E.g:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 110           | 10% incl, 5%  |                   | 100               | 115
            # 10            |               | 10% incl          | 10                | 10
            # 5             |               | 5%                | 5                 | 5
            #
            # When setting the balance to -200, the expected result is:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 220           | 10% incl, 5%  |                   | 200               | 230
            # 20            |               | 10% incl          | 20                | 20
            # 10            |               | 5%                | 10                | 10
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(balance, currency=currency, handle_price_include=False)
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    balance += tax_res['amount']

        discount_factor = 1 - (discount / 100.0)
        if balance and discount_factor:
            # discount != 100%
            vals = {
                'quantity': quantity or 1.0,
                'price_unit': balance / discount_factor / (quantity or 1.0),
            }
        elif balance and not discount_factor:
            # discount == 100%
            vals = {
                'quantity': quantity or 1.0,
                'discount': 0.0,
                'price_unit': balance / (quantity or 1.0),
            }
        elif not discount_factor:
            # balance of line is 0, but discount  == 100% so we display the normal unit_price
            vals = {}
        else:
            # balance is 0, so unit price is 0 as well
            vals = {'price_unit': 0.0}
        return vals

    def _get_invoiced_qty_per_product(self):
        qties = defaultdict(float)
        for aml in self:
            qty = aml.product_uom_id._compute_quantity(aml.quantity, aml.product_id.uom_id)
            if aml.move_id.type == 'out_invoice':
                qties[aml.product_id] += qty
            elif aml.move_id.type == 'out_refund':
                qties[aml.product_id] -= qty
        return qties

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('amount_currency', 'currency_id', 'debit', 'credit', 'tax_ids', 'account_id', 'price_unit')
    def _onchange_mark_recompute_taxes(self):
        ''' Recompute the dynamic onchange based on taxes.
        If the edited line is a tax line, don't recompute anything as the user must be able to
        set a custom value.
        '''
        for line in self:
            if not line.tax_repartition_line_id:
                line.recompute_tax_line = True

    @api.onchange('analytic_account_id', 'analytic_tag_ids')
    def _onchange_mark_recompute_taxes_analytic(self):
        ''' Trigger tax recomputation only when some taxes with analytics
        '''
        for line in self:
            if not line.tax_repartition_line_id and any(tax.analytic for tax in line.tax_ids):
                line.recompute_tax_line = True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()

        if len(self) == 1:
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_uom_id.category_id.id)]}}

    @api.onchange('product_uom_id')
    def _onchange_uom_id(self):
        ''' Recompute the 'price_unit' depending of the unit of measure. '''
        if self.display_type in ('line_section', 'line_note'):
            return
        taxes = self._get_computed_taxes()
        if taxes and self.move_id.fiscal_position_id:
            taxes = self.move_id.fiscal_position_id.map_tax(taxes, partner=self.partner_id)
        self.tax_ids = taxes
        self.price_unit = self._get_computed_price_unit()

    @api.onchange('account_id')
    def _onchange_account_id(self):
        ''' Recompute 'tax_ids' based on 'account_id'.
        /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
        '''
        if not self.display_type and (self.account_id.tax_ids or not self.tax_ids):
            taxes = self._get_computed_taxes()

            if taxes and self.move_id.fiscal_position_id:
                taxes = self.move_id.fiscal_position_id.map_tax(taxes, partner=self.partner_id)

            self.tax_ids = taxes

    def _onchange_balance(self):
        for line in self:
            if line.currency_id:
                continue
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())

    @api.onchange('debit')
    def _onchange_debit(self):
        if self.debit:
            self.credit = 0.0
        self._onchange_balance()

    @api.onchange('credit')
    def _onchange_credit(self):
        if self.credit:
            self.debit = 0.0
        self._onchange_balance()

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            if not line.currency_id:
                continue
            if not line.move_id.is_invoice(include_receipts=True):
                line._recompute_debit_credit_from_amount_currency()
                continue
            line.update(line._get_fields_onchange_balance(
                balance=line.amount_currency,
            ))
            line.update(line._get_price_total_and_subtotal())

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

    @api.onchange('currency_id')
    def _onchange_currency(self):
        for line in self:
            if line.move_id.is_invoice(include_receipts=True):
                line._onchange_price_subtotal()
            elif not line.move_id.reversed_entry_id:
                line._recompute_debit_credit_from_amount_currency()

    def _recompute_debit_credit_from_amount_currency(self):
        for line in self:
            # Recompute the debit/credit based on amount_currency/currency_id and date.

            company_currency = line.account_id.company_id.currency_id
            balance = line.amount_currency
            if line.currency_id and company_currency and line.currency_id != company_currency:
                balance = line.currency_id._convert(balance, company_currency, line.account_id.company_id, line.move_id.date or fields.Date.today())
                line.debit = balance > 0 and balance or 0.0
                line.credit = balance < 0 and -balance or 0.0
    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('currency_id')
    def _compute_always_set_currency_id(self):
        for line in self:
            line.always_set_currency_id = line.currency_id or line.company_currency_id

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.depends('debit', 'credit', 'account_id', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state', 'company_id')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                line.reconciled = False
                line.amount_residual = 0
                line.amount_residual_currency = 0
                continue
            #amounts in the partial reconcile table aren't signed, so we need to use abs()
            amount = abs(line.debit - line.credit)
            amount_residual_currency = abs(line.amount_currency) or 0.0
            sign = 1 if (line.debit - line.credit) > 0 else -1
            if not line.debit and not line.credit and line.amount_currency and line.currency_id:
                #residual for exchange rate entries
                sign = 1 if float_compare(line.amount_currency, 0, precision_rounding=line.currency_id.rounding) == 1 else -1

            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                # If line is a credit (sign = -1) we:
                #  - subtract matched_debit_ids (partial_line.credit_move_id == line)
                #  - add matched_credit_ids (partial_line.credit_move_id != line)
                # If line is a debit (sign = 1), do the opposite.
                sign_partial_line = sign if partial_line.credit_move_id == line else (-1 * sign)

                amount += sign_partial_line * partial_line.amount
                #getting the date of the matched item to compute the amount_residual in currency
                if line.currency_id and line.amount_currency:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency += sign_partial_line * partial_line.amount_currency
                    else:
                        if line.balance and line.amount_currency:
                            rate = line.amount_currency / line.balance
                        else:
                            date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                            rate = line.currency_id.with_context(date=date).rate
                        amount_residual_currency += sign_partial_line * line.currency_id.round(partial_line.amount * rate)

            #computing the `reconciled` field.
            reconciled = False
            digits_rounding_precision = line.move_id.company_id.currency_id.rounding
            if float_is_zero(amount, precision_rounding=digits_rounding_precision) and (line.matched_debit_ids or line.matched_credit_ids):
                if line.currency_id and line.amount_currency:
                    if float_is_zero(amount_residual_currency, precision_rounding=line.currency_id.rounding):
                        reconciled = True
                else:
                    reconciled = True
            line.reconciled = reconciled

            line.amount_residual = line.move_id.company_id.currency_id.round(amount * sign) if line.move_id.company_id else amount * sign
            line.amount_residual_currency = line.currency_id and line.currency_id.round(amount_residual_currency * sign) or 0.0

    @api.depends('tax_repartition_line_id.invoice_tax_id', 'tax_repartition_line_id.refund_tax_id')
    def _compute_tax_line_id(self):
        """ tax_line_id is computed as the tax linked to the repartition line creating
        the move.
        """
        for record in self:
            rep_line = record.tax_repartition_line_id
            # A constraint on account.tax.repartition.line ensures both those fields are mutually exclusive
            record.tax_line_id = rep_line.invoice_tax_id or rep_line.refund_tax_id

    @api.depends('tag_ids', 'debit', 'credit')
    def _compute_tax_audit(self):
        separator = '        '

        for record in self:
            currency = record.company_id.currency_id
            audit_str = ''
            for tag in record.tag_ids:

                if record.move_id.tax_cash_basis_rec_id:
                    # Cash basis entries are always treated as misc operations, applying the tag sign directly to the balance
                    type_multiplicator = 1
                else:
                    type_multiplicator = (record.journal_id.type == 'sale' and self._get_not_entry_condition(record) and -1 or 1) * (self._get_refund_tax_audit_condition(record) and -1 or 1)

                tag_amount = type_multiplicator * (tag.tax_negate and -1 or 1) * record.balance

                if tag.tax_report_line_ids:
                    #Then, the tag comes from a report line, and hence has a + or - sign (also in its name)
                    for report_line in tag.tax_report_line_ids:
                        audit_str += separator if audit_str else ''
                        audit_str += report_line.tag_name + ': ' + formatLang(self.env, tag_amount, currency_obj=currency)
                else:
                    # Then, it's a financial tag (sign is always +, and never shown in tag name)
                    audit_str += separator if audit_str else ''
                    audit_str += tag.name + ': ' + formatLang(self.env, tag_amount, currency_obj=currency)

            record.tax_audit = audit_str

    def _get_not_entry_condition(self, aml):
        """
        Returns the condition to exclude entry move types to avoid their tax_audit value
        to be revesed if they are from type entry.
        This function is overridden in pos.
        """
        return aml.move_id.type != 'entry'

    def _get_refund_tax_audit_condition(self, aml):
        """ Returns the condition to be used for the provided move line to tell
        whether or not it comes from a refund operation.
        This is overridden by pos in order to treat returns properly.
        """
        return aml.move_id.type in ('in_refund', 'out_refund')

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('currency_id', 'account_id')
    def _check_account_currency(self):
        for line in self:
            account_currency = line.account_id.currency_id
            if account_currency and account_currency != line.company_currency_id and account_currency != line.currency_id:
                raise UserError(_('The account selected on your journal entry forces to provide a secondary currency. You should remove the secondary currency on the account.'))

    @api.constrains('account_id')
    def _check_constrains_account_id(self):
        for line in self.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            account = line.account_id
            journal = line.journal_id

            if account.deprecated:
                raise UserError(_('The account %s (%s) is deprecated.') % (account.name, account.code))

            failed_check = False
            if journal.type_control_ids or journal.account_control_ids:
                failed_check = True
                if journal.type_control_ids:
                    failed_check = account.user_type_id not in journal.type_control_ids
                if failed_check and journal.account_control_ids:
                    failed_check = account not in journal.account_control_ids

            if failed_check:
                raise UserError(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

    @api.constrains('account_id', 'tax_ids', 'tax_line_id', 'reconciled')
    def _check_off_balance(self):
        for line in self:
            if line.account_id.internal_group == 'off_balance':
                if any(a.internal_group != line.account_id.internal_group for a in line.move_id.line_ids.account_id):
                    raise UserError(_('If you want to use "Off-Balance Sheet" accounts, all the accounts of the journal entry must be of this type'))
                if line.tax_ids or line.tax_line_id:
                    raise UserError(_('You cannot use taxes on lines with an Off-Balance account'))
                if line.reconciled:
                    raise UserError(_('Lines from "Off-Balance Sheet" accounts cannot be reconciled'))

    def _affect_tax_report(self):
        self.ensure_one()
        return self.tax_ids or self.tax_line_id or self.tag_ids.filtered(lambda x: x.applicability == "taxes")

    def _check_tax_lock_date(self):
        for line in self.filtered(lambda l: l.parent_state == 'posted'):
            move = line.move_id
            if move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date and line._affect_tax_report():
                raise UserError(_("The operation is refused as it would impact an already issued tax statement. "
                                  "Please change the journal entry date or the tax lock date set in the settings (%s) to proceed.")
                                % format_date(self.env, move.company_id.tax_lock_date))

    def _check_reconciliation(self):
        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                                  "You can just change some non legal fields or you must unreconcile first.\n"
                                  "Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def init(self):
        """ change index on partner_id to a multi-column index on (partner_id, ref), the new index will behave in the
            same way when we search on partner_id, with the addition of being optimal when having a query that will
            search on partner_id and ref at the same time (which is the case when we open the bank reconciliation widget)
        """
        cr = self._cr
        cr.execute('DROP INDEX IF EXISTS account_move_line_partner_id_index')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_move_line_partner_id_ref_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_partner_id_ref_idx ON account_move_line (partner_id, ref)')

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')

        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id', move.company_id.currency_id.id) # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.resolve_2many_commands('tax_ids', vals.get('tax_ids', []), fields=['id'])
                tax_ids = set(tax['id'] for tax in taxes)
                taxes = self.env['account.tax'].browse(tax_ids)

                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    if vals.get('currency_id'):
                        balance = vals.get('amount_currency', 0.0)
                    else:
                        balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.type,
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        balance,
                        move.type,
                        currency,
                        taxes,
                        price_subtotal
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.type,
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.type,
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.type,
                        currency,
                        move.company_id,
                        move.date,
                    ))

        lines = super(AccountMoveLine, self).create(vals_list)

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves._check_fiscalyear_lock_date()
        lines._check_tax_lock_date()

        return lines

    def write(self, vals):
        # OVERRIDE
        def field_will_change(line, field_name):
            if field_name not in vals:
                return False
            field = line._fields[field_name]
            if field.type == 'many2one':
                return line[field_name].id != vals[field_name]
            if field.type in ('one2many', 'many2many'):
                current_ids = set(line[field_name].ids)
                after_write_ids = set(r['id'] for r in line.resolve_2many_commands(field_name, vals[field_name], fields=['id']))
                return current_ids != after_write_ids
            if field.type == 'monetary' and line[field.currency_field]:
                return not line[field.currency_field].is_zero(line[field_name] - vals[field_name])
            return line[field_name] != vals[field_name]

        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['debit', 'credit', 'tax_line_id', 'tax_ids', 'tag_ids']
        PROTECTED_FIELDS_LOCK_DATE = PROTECTED_FIELDS_TAX_LOCK_DATE + ['account_id', 'journal_id', 'amount_currency', 'currency_id', 'partner_id']
        PROTECTED_FIELDS_RECONCILIATION = ('account_id', 'date', 'debit', 'credit', 'amount_currency', 'currency_id')

        account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None

        # Check writing a deprecated account.
        if account_to_write and account_to_write.deprecated:
            raise UserError(_('You cannot use a deprecated account.'))

        # when making a reconciliation on an existing liquidity journal item, mark the payment as reconciled
        for line in self:
            if line.parent_state == 'posted':
                if line.move_id.restrict_mode_hash_table and set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
                    raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(INTEGRITY_HASH_LINE_FIELDS))
                if any(key in vals for key in ('tax_ids', 'tax_line_id')):
                    raise UserError(_('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))
            if 'statement_line_id' in vals and line.payment_id:
                # In case of an internal transfer, there are 2 liquidity move lines to match with a bank statement
                if all(_line.statement_id for _line in line.payment_id.move_line_ids.filtered(
                        lambda r: r.id != line.id and r.account_id.internal_type == 'liquidity')):
                    line.payment_id.state = 'reconciled'

            # Check the lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_LOCK_DATE):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_TAX_LOCK_DATE):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_RECONCILIATION):
                line._check_reconciliation()

            # Check switching receivable / payable accounts.
            if account_to_write:
                account_type = line.account_id.user_type_id.type
                if line.move_id.is_sale_document(include_receipts=True):
                    if (account_type == 'receivable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'receivable' and account_to_write.user_type_id.type == 'receivable'):
                        raise UserError(_("You can only set an account having the receivable type on payment terms lines for customer invoice."))
                if line.move_id.is_purchase_document(include_receipts=True):
                    if (account_type == 'payable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'payable' and account_to_write.user_type_id.type == 'payable'):
                        raise UserError(_("You can only set an account having the payable type on payment terms lines for vendor bill."))

        result = True
        for line in self:
            cleaned_vals = line.move_id._cleanup_write_orm_values(line, vals)
            if not cleaned_vals:
                continue

            result |= super(AccountMoveLine, line).write(cleaned_vals)

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            # Ensure consistency between accounting & business fields.
            # As we can't express such synchronization as computed fields without cycling, we need to do it both
            # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
            # business [resp. accounting] fields are recomputed.
            if any(field in cleaned_vals for field in ACCOUNTING_FIELDS):
                balance = line.currency_id and line.amount_currency or line.debit - line.credit
                price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
                to_write = line._get_fields_onchange_balance(
                    balance=balance,
                    price_subtotal=price_subtotal,
                )
                to_write.update(line._get_price_total_and_subtotal(
                    price_unit=to_write.get('price_unit', line.price_unit),
                    quantity=to_write.get('quantity', line.quantity),
                    discount=to_write.get('discount', line.discount),
                ))
                result |= super(AccountMoveLine, line).write(to_write)
            elif any(field in cleaned_vals for field in BUSINESS_FIELDS):
                to_write = line._get_price_total_and_subtotal()
                to_write.update(line._get_fields_onchange_subtotal(
                    price_subtotal=to_write['price_subtotal'],
                ))
                result |= super(AccountMoveLine, line).write(to_write)

        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
            self.mapped('move_id')._check_balanced()

        return result

    def unlink(self):
        moves = self.mapped('move_id')

        # Prevent deleting lines on posted entries
        if any(m.state == 'posted' for m in moves):
            raise UserError(_('You cannot delete an item linked to a posted entry.'))

        # Check the lines are not reconciled (partially or not).
        self._check_reconciliation()

        # Check the lock date.
        moves._check_fiscalyear_lock_date()

        # Check the tax lock date.
        self._check_tax_lock_date()

        res = super(AccountMoveLine, self).unlink()

        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
            moves._check_balanced()

        return res

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(AccountMoveLine, self).default_get(default_fields)

        if 'account_id' in default_fields \
            and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
            and not values.get('account_id') \
            and self._context.get('default_type') in self.move_id.get_inbound_types():
            # Fill missing 'account_id'.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            values['account_id'] = journal.default_credit_account_id.id
        elif 'account_id' in default_fields \
            and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
            and not values.get('account_id') \
            and self._context.get('default_type') in self.move_id.get_outbound_types():
            # Fill missing 'account_id'.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            values['account_id'] = journal.default_debit_account_id.id
        elif self._context.get('line_ids') and any(field_name in default_fields for field_name in ('debit', 'credit', 'account_id', 'partner_id')):
            move = self.env['account.move'].new({'line_ids': self._context['line_ids']})

            # Suggest default value for debit / credit to balance the journal entry.
            balance = sum(line['debit'] - line['credit'] for line in move.line_ids)
            # if we are here, line_ids is in context, so journal_id should also be.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            currency = journal.exists() and journal.company_id.currency_id
            if currency:
                balance = currency.round(balance)
            if balance < 0.0:
                values.update({'debit': -balance})
            if balance > 0.0:
                values.update({'credit': balance})

            # Suggest default value for 'partner_id'.
            if 'partner_id' in default_fields and not values.get('partner_id'):
                if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].partner_id == move.line_ids[-2].partner_id != False:
                    values['partner_id'] = move.line_ids[-2:].mapped('partner_id').id

            # Suggest default value for 'account_id'.
            if 'account_id' in default_fields and not values.get('account_id'):
                if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].account_id == move.line_ids[-2].account_id != False:
                    values['account_id'] = move.line_ids[-2:].mapped('account_id').id
        if values.get('display_type'):
            values.pop('account_id', None)
        return values

    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            name = line.move_id.name or ''
            if line.ref:
                name += " (%s)" % line.ref
            name += (line.name or line.product_id.display_name) and (' ' + (line.name or line.product_id.display_name)) or ''
            result.append((line.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike':
            args = ['|', '|',
                    ('name', 'ilike', name),
                    ('move_id', 'ilike', name),
                    ('product_id', 'ilike', name)]
            result = self._search(args, limit=limit, access_rights_uid=name_get_uid)
            return models.lazy_name_get(self.browse(result).with_user(name_get_uid))

        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.model
    def invalidate_cache(self, fnames=None, ids=None):
        # Invalidate cache of related moves
        if fnames is None or 'move_id' in fnames:
            field = self._fields['move_id']
            lines = self.env.cache.get_records(self, field) if ids is None else self.browse(ids)
            move_ids = {id_ for id_ in self.env.cache.get_values(lines, field) if id_}
            if move_ids:
                self.env['account.move'].invalidate_cache(ids=move_ids)
        return super().invalidate_cache(fnames=fnames, ids=ids)

    # -------------------------------------------------------------------------
    # RECONCILIATION
    # -------------------------------------------------------------------------

    def check_full_reconcile(self):
        """
        This method check if a move is totally reconciled and if we need to create exchange rate entries for the move.
        In case exchange rate entries needs to be created, one will be created per currency present.
        In case of full reconciliation, all moves belonging to the reconciliation will belong to the same account_full_reconcile object.
        """
        # Get first all aml involved
        todo = self.env['account.partial.reconcile'].search_read(['|', ('debit_move_id', 'in', self.ids), ('credit_move_id', 'in', self.ids)], ['debit_move_id', 'credit_move_id'])
        amls = set(self.ids)
        seen = set()
        while todo:
            aml_ids = [rec['debit_move_id'][0] for rec in todo if rec['debit_move_id']] + [rec['credit_move_id'][0] for rec in todo if rec['credit_move_id']]
            amls |= set(aml_ids)
            seen |= set([rec['id'] for rec in todo])
            todo = self.env['account.partial.reconcile'].search_read(['&', '|', ('credit_move_id', 'in', aml_ids), ('debit_move_id', 'in', aml_ids), '!', ('id', 'in', list(seen))], ['debit_move_id', 'credit_move_id'])

        partial_rec_ids = list(seen)
        if not amls:
            return
        else:
            amls = self.browse(list(amls))

        # If we have multiple currency, we can only base ourselves on debit-credit to see if it is fully reconciled
        currency = set([a.currency_id for a in amls if a.currency_id.id != False])
        multiple_currency = False
        if len(currency) != 1:
            currency = False
            multiple_currency = True
        else:
            currency = list(currency)[0]
        # Get the sum(debit, credit, amount_currency) of all amls involved
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        maxdate = date.min
        to_balance = {}
        cash_basis_partial = self.env['account.partial.reconcile']
        for aml in amls:
            cash_basis_partial |= aml.move_id.tax_cash_basis_rec_id
            total_debit += aml.debit
            total_credit += aml.credit
            maxdate = max(aml.date, maxdate)
            total_amount_currency += aml.amount_currency
            # Convert in currency if we only have one currency and no amount_currency
            if not aml.amount_currency and currency:
                multiple_currency = True
                total_amount_currency += aml.company_id.currency_id._convert(aml.balance, currency, aml.company_id, aml.date)
            # If we still have residual value, it means that this move might need to be balanced using an exchange rate entry
            if aml.amount_residual != 0 or aml.amount_residual_currency != 0:
                if not to_balance.get(aml.currency_id):
                    to_balance[aml.currency_id] = [self.env['account.move.line'], 0]
                to_balance[aml.currency_id][0] += aml
                to_balance[aml.currency_id][1] += aml.amount_residual != 0 and aml.amount_residual or aml.amount_residual_currency

        # Check if reconciliation is total
        # To check if reconciliation is total we have 3 different use case:
        # 1) There are multiple currency different than company currency, in that case we check using debit-credit
        # 2) We only have one currency which is different than company currency, in that case we check using amount_currency
        # 3) We have only one currency and some entries that don't have a secundary currency, in that case we check debit-credit
        #   or amount_currency.
        # 4) Cash basis full reconciliation
        #     - either none of the moves are cash basis reconciled, and we proceed
        #     - or some moves are cash basis reconciled and we make sure they are all fully reconciled

        digits_rounding_precision = amls[0].company_id.currency_id.rounding
        caba_reconciled_amls = cash_basis_partial.mapped('debit_move_id') + cash_basis_partial.mapped('credit_move_id')
        caba_connected_amls = amls.filtered(lambda x: x.move_id.tax_cash_basis_rec_id) + caba_reconciled_amls
        matched_percentages = caba_connected_amls._get_matched_percentage()
        if (
                (all(amls.mapped('tax_exigible')) or all(matched_percentages[aml.move_id.id] >= 1.0 for aml in caba_connected_amls))
                and
                (
                    currency and float_is_zero(total_amount_currency, precision_rounding=currency.rounding) or
                    multiple_currency and float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0
                )
        ):

            exchange_move_id = False
            missing_exchange_difference = False
            # Eventually create a journal entry to book the difference due to foreign currency's exchange rate that fluctuates
            if to_balance and any([not float_is_zero(residual, precision_rounding=digits_rounding_precision) for aml, residual in to_balance.values()]):
                if not self.env.context.get('no_exchange_difference'):
                    exchange_move_vals = self.env['account.full.reconcile']._prepare_exchange_diff_move(
                        move_date=maxdate, company=amls[0].company_id)
                    if len(amls.mapped('partner_id')) == 1 and amls[0].partner_id:
                        exchange_move_vals['partner_id'] = amls[0].partner_id.id
                    exchange_move = self.env['account.move'].with_context(default_type='entry').create(exchange_move_vals)
                    part_reconcile = self.env['account.partial.reconcile']
                    for aml_to_balance, total in to_balance.values():
                        if total:
                            rate_diff_amls, rate_diff_partial_rec = part_reconcile.create_exchange_rate_entry(aml_to_balance, exchange_move)
                            amls += rate_diff_amls
                            partial_rec_ids += rate_diff_partial_rec.ids
                        else:
                            aml_to_balance.reconcile()
                    exchange_move.post()
                    exchange_move_id = exchange_move.id
                else:
                    missing_exchange_difference = True
            if not missing_exchange_difference:
                #mark the reference of the full reconciliation on the exchange rate entries and on the entries
                self.env['account.full.reconcile'].create({
                    'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                    'reconciled_line_ids': [(6, 0, amls.ids)],
                    'exchange_move_id': exchange_move_id,
                })

    def _reconcile_lines(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}
        dc_vals ={}
        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual)
            temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
            dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field])

            #Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency

            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual
            elif bool(debit_move.currency_id) != bool(credit_move.currency_id):
                # If only one of debit_move or credit_move has a secondary currency, also record the converted amount
                # in that secondary currency in the partial reconciliation. That allows the exchange difference entry
                # to be created, in case it is needed. It also allows to compute the amount residual in foreign currency.
                currency = debit_move.currency_id or credit_move.currency_id
                currency_date = debit_move.currency_id and credit_move.date or debit_move.date
                amount_reconcile_currency = company_currency._convert(amount_reconcile, currency, debit_move.company_id, currency_date)
                currency = currency.id

            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())

            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })

        cash_basis_subjected = []
        part_rec = self.env['account.partial.reconcile']
        for partial_rec_dict in to_create:
            debit_move, credit_move, amount_residual_currency = dc_vals[partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
            # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
            # i. e: we don't really receive/give money in a customer/provider fashion
            # Since those are not subjected to cash basis computation we process them first
            if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
                part_rec.create(partial_rec_dict)
            else:
                cash_basis_subjected.append(partial_rec_dict)

        for after_rec_dict in cash_basis_subjected:
            new_rec = part_rec.create(after_rec_dict)
            # if the pair belongs to move being reverted, do not create CABA entry
            if cash_basis and not (
                    new_rec.debit_move_id.move_id == new_rec.credit_move_id.move_id.reversed_entry_id
                    or
                    new_rec.credit_move_id.move_id == new_rec.debit_move_id.move_id.reversed_entry_id
            ):
                new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
        return debit_moves+credit_moves

    def auto_reconcile_lines(self):
        # Create list of debit and list of credit move ordered by date-currency
        debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
        credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
        void_moves = self.filtered(lambda r: not r.credit and not r.debit and not r.amount_currency)
        debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        # Compute on which field reconciliation should be based upon:
        if self[0].account_id.currency_id and self[0].account_id.currency_id != self[0].account_id.company_id.currency_id:
            field = 'amount_residual_currency'
        else:
            field = 'amount_residual'
        #if all lines share the same currency, use amount_residual_currency to avoid currency rounding error
        if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
            field = 'amount_residual_currency'
        # Reconcile lines
        if debit_moves:
            ret = self._reconcile_lines(debit_moves, void_moves + credit_moves, field)
        elif credit_moves:
            ret = self._reconcile_lines(void_moves + debit_moves, credit_moves, field)
        else:
            ret = self._reconcile_lines(void_moves[:len(void_moves) // 2], void_moves[len(void_moves) // 2:], field)
        return ret

    def _check_reconcile_validity(self):
        # Empty self can happen if there is no line to check.
        if not self:
            return

        #Perform all checks on lines
        company_ids = set()
        all_accounts = []
        for line in self:
            company_ids.add(line.company_id.id)
            all_accounts.append(line.account_id)
            if line.reconciled:
                raise UserError(_('You are trying to reconcile some entries that are already reconciled.'))
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries.'))
        if len(set(all_accounts)) > 1:
            raise UserError(_('Entries are not from the same account.'))
        if not (all_accounts[0].reconcile or all_accounts[0].internal_type == 'liquidity'):
            raise UserError(_('Account %s (%s) does not allow reconciliation. First change the configuration of this account to allow it.') % (all_accounts[0].name, all_accounts[0].code))

    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        # Empty self can happen if the user tries to reconcile entries which are already reconciled.
        # The calling method might have filtered out reconciled lines.
        if not self:
            return

        # List unpaid invoices
        not_paid_invoices = self.mapped('move_id').filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.invoice_payment_state not in ('paid', 'in_payment')
        )

        reconciled_lines = self.filtered(lambda aml: float_is_zero(aml.balance, precision_rounding=aml.move_id.company_id.currency_id.rounding) and aml.reconciled)
        (self - reconciled_lines)._check_reconcile_validity()
        #reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines()

        writeoff_to_reconcile = self.env['account.move.line']
        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            all_aml_share_same_currency = all([x.currency_id == self[0].currency_id for x in self])
            writeoff_vals = {
                'account_id': writeoff_acc_id.id,
                'journal_id': writeoff_journal_id.id
            }
            if not all_aml_share_same_currency:
                writeoff_vals['amount_currency'] = False
            writeoff_to_reconcile = remaining_moves._create_writeoff([writeoff_vals])
            #add writeoff line to reconcile algorithm and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).auto_reconcile_lines()
        # Check if reconciliation is total or needs an exchange rate entry to be created
        (self + writeoff_to_reconcile).check_full_reconcile()

        # Trigger action for paid invoices
        not_paid_invoices.filtered(
            lambda m: m.invoice_payment_state in ('paid', 'in_payment')
        ).action_invoice_paid()

        return True

    def _create_writeoff(self, writeoff_vals):
        """ Create a writeoff move per journal for the account.move.lines in self. If debit/credit is not specified in vals,
            the writeoff amount will be computed as the sum of amount_residual of the given recordset.
            :param writeoff_vals: list of dicts containing values suitable for account_move_line.create(). The data in vals will
                be processed to create bot writeoff account.move.line and their enclosing account.move.
        """
        def compute_writeoff_counterpart_vals(values):
            line_values = values.copy()
            line_values['debit'], line_values['credit'] = line_values['credit'], line_values['debit']
            if 'amount_currency' in values:
                line_values['amount_currency'] = -line_values['amount_currency']
            return line_values
        # Group writeoff_vals by journals
        writeoff_dict = {}
        for val in writeoff_vals:
            journal_id = val.get('journal_id', False)
            if not writeoff_dict.get(journal_id, False):
                writeoff_dict[journal_id] = [val]
            else:
                writeoff_dict[journal_id].append(val)

        partner_id = self.env['res.partner']._find_accounting_partner(self[0].partner_id).id
        company_currency = self[0].account_id.company_id.currency_id
        writeoff_currency = self[0].account_id.currency_id or company_currency
        line_to_reconcile = self.env['account.move.line']
        # Iterate and create one writeoff by journal
        writeoff_moves = self.env['account.move']
        for journal_id, lines in writeoff_dict.items():
            total = 0
            total_currency = 0
            writeoff_lines = []
            date = fields.Date.today()
            for vals in lines:
                # Check and complete vals
                if 'account_id' not in vals or 'journal_id' not in vals:
                    raise UserError(_("It is mandatory to specify an account and a journal to create a write-off."))
                if ('debit' in vals) ^ ('credit' in vals):
                    raise UserError(_("Either pass both debit and credit or none."))
                if 'date' not in vals:
                    vals['date'] = self._context.get('date_p') or fields.Date.today()
                vals['date'] = fields.Date.to_date(vals['date'])
                if vals['date'] and vals['date'] < date:
                    date = vals['date']
                if 'name' not in vals:
                    vals['name'] = self._context.get('comment') or _('Write-Off')
                if 'analytic_account_id' not in vals:
                    vals['analytic_account_id'] = self.env.context.get('analytic_id', False)
                #compute the writeoff amount if not given
                if 'credit' not in vals and 'debit' not in vals:
                    amount = sum([r.amount_residual for r in self])
                    vals['credit'] = amount > 0 and amount or 0.0
                    vals['debit'] = amount < 0 and abs(amount) or 0.0
                vals['partner_id'] = partner_id
                total += vals['debit']-vals['credit']
                if 'amount_currency' not in vals and writeoff_currency != company_currency:
                    vals['currency_id'] = writeoff_currency.id
                    sign = 1 if vals['debit'] > 0 else -1
                    vals['amount_currency'] = sign * abs(sum([r.amount_residual_currency for r in self]))
                    total_currency += vals['amount_currency']

                writeoff_lines.append(compute_writeoff_counterpart_vals(vals))

            # Create balance line
            writeoff_lines.append({
                'name': _('Write-Off'),
                'debit': total > 0 and total or 0.0,
                'credit': total < 0 and -total or 0.0,
                'amount_currency': total_currency,
                'currency_id': total_currency and writeoff_currency.id or False,
                'journal_id': journal_id,
                'account_id': self[0].account_id.id,
                'partner_id': partner_id
                })

            # Create the move
            writeoff_move = self.env['account.move'].create({
                'journal_id': journal_id,
                'date': date,
                'state': 'draft',
                'line_ids': [(0, 0, line) for line in writeoff_lines],
            })
            writeoff_moves += writeoff_move
            line_to_reconcile += writeoff_move.line_ids.filtered(lambda r: r.account_id == self[0].account_id).sorted(key='id')[-1:]

        #post all the writeoff moves at once
        if writeoff_moves:
            writeoff_moves.post()

        # Return the writeoff move.line which is to be reconciled
        return line_to_reconcile

    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        # Payment partial reconcile
        rec_partial_reconcile = self.mapped('matched_debit_ids') + self.mapped('matched_credit_ids')
        if self.env.context.get('move_id'):
            # If an invoice is specified, we will only remove the reconciliation between the payment
            # and that specific invoice.
            # Note that, if a write-off was created this one must be removed too.
            current_invoice = self.env['account.move'].browse(self.env.context.get('move_id'))
            # Current invoice partial reconcile
            invoice_wo_partial_reconcile = current_invoice.line_ids.mapped('matched_debit_ids') + current_invoice.line_ids.mapped('matched_credit_ids')
            writeoff = current_invoice.line_ids.mapped('full_reconcile_id.exchange_move_id')
            if writeoff:
                # Write-off partial reconcile
                invoice_wo_partial_reconcile += writeoff.line_ids.mapped('matched_credit_ids')
                invoice_wo_partial_reconcile += writeoff.line_ids.mapped('matched_debit_ids')
            rec_partial_reconcile = rec_partial_reconcile & invoice_wo_partial_reconcile
        rec_partial_reconcile.unlink()

    def _copy_data_extend_business_fields(self, values):
        ''' Hook allowing copying business fields under certain conditions.
        E.g. The link to the sale order lines must be preserved in case of a refund.
        '''
        self.ensure_one()

    def copy_data(self, default=None):
        res = super(AccountMoveLine, self).copy_data(default=default)

        for line, values in zip(self, res):
            # Don't copy the name of a payment term line.
            if line.move_id.is_invoice() and line.account_id.user_type_id.type in ('receivable', 'payable'):
                values['name'] = ''
            # Don't copy restricted fields of notes
            if line.display_type in ('line_section', 'line_note'):
                values['amount_currency'] = 0
                values['debit'] = 0
                values['credit'] = 0
                values['account_id'] = False
            if self._context.get('include_business_fields'):
                line._copy_data_extend_business_fields(values)
        return res

    # -------------------------------------------------------------------------
    # MISC
    # -------------------------------------------------------------------------

    def _get_matched_percentage(self):
        """ This function returns a dictionary giving for each move_id of self, the percentage to consider as cash basis factor.
        This is actually computing the same as the matched_percentage field of account.move, except in case of multi-currencies
        where we recompute the matched percentage based on the amount_currency fields.
        Note that this function is used only by the tax cash basis module since we want to consider the matched_percentage only
        based on the company currency amounts in reports.
        """
        matched_percentage_per_move = {}
        for line in self:
            if not matched_percentage_per_move.get(line.move_id.id, False):
                lines_to_consider = line.move_id.line_ids.filtered(lambda x: x.account_id.internal_type in ('receivable', 'payable'))
                total_amount_currency = 0.0
                total_reconciled_currency = 0.0
                all_same_currency = False
                #if all receivable/payable aml and their payments have the same currency, we can safely consider
                #the amount_currency fields to avoid including the exchange rate difference in the matched_percentage
                if lines_to_consider and all([x.currency_id.id == lines_to_consider[0].currency_id.id for x in lines_to_consider]):
                    all_same_currency = lines_to_consider[0].currency_id.id
                    for line in lines_to_consider:
                        if all_same_currency:
                            total_amount_currency += abs(line.amount_currency)
                            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                                if partial_line.currency_id and partial_line.currency_id.id == all_same_currency:
                                    total_reconciled_currency += partial_line.amount_currency
                                else:
                                    all_same_currency = False
                                    break
                if not all_same_currency:
                    #we cannot rely on amount_currency fields as it is not present on all partial reconciliation
                    matched_percentage_per_move[line.move_id.id] = line.move_id._get_cash_basis_matched_percentage()
                else:
                    #we can rely on amount_currency fields, which allow us to post a tax cash basis move at the initial rate
                    #to avoid currency rate difference issues.
                    if total_amount_currency == 0.0:
                        matched_percentage_per_move[line.move_id.id] = 1.0
                    else:
                        # lines_to_consider is always non-empty when total_amount_currency is 0
                        currency = lines_to_consider[0].currency_id or lines_to_consider[0].company_id.currency_id
                        matched_percentage_per_move[line.move_id.id] = currency.round(total_reconciled_currency) / currency.round(total_amount_currency)
        return matched_percentage_per_move

    def _get_analytic_tag_ids(self):
        self.ensure_one()
        return self.analytic_tag_ids.filtered(lambda r: not r.active_analytic_distribution).ids

    def create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic account or an analytic distribution.
        """
        lines_to_create_analytic_entries = self.env['account.move.line']
        for obj_line in self:
            for tag in obj_line.analytic_tag_ids.filtered('active_analytic_distribution'):
                for distribution in tag.analytic_distribution_ids:
                    vals_line = obj_line._prepare_analytic_distribution_line(distribution)
                    self.env['account.analytic.line'].create(vals_line)
            if obj_line.analytic_account_id:
                lines_to_create_analytic_entries |= obj_line

        # create analytic entries in batch
        if lines_to_create_analytic_entries:
            values_list = lines_to_create_analytic_entries._prepare_analytic_line()
            self.env['account.analytic.line'].create(values_list)

    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
            :return list of values to create analytic.line
            :rtype list
        """
        result = []
        for move_line in self:
            amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
            default_name = move_line.name or (move_line.ref or '/' + ' -- ' + (move_line.partner_id and move_line.partner_id.name or '/'))
            result.append({
                'name': default_name,
                'date': move_line.date,
                'account_id': move_line.analytic_account_id.id,
                'group_id': move_line.analytic_account_id.group_id.id,
                'tag_ids': [(6, 0, move_line._get_analytic_tag_ids())],
                'unit_amount': move_line.quantity,
                'product_id': move_line.product_id and move_line.product_id.id or False,
                'product_uom_id': move_line.product_uom_id and move_line.product_uom_id.id or False,
                'amount': amount,
                'general_account_id': move_line.account_id.id,
                'ref': move_line.ref,
                'move_id': move_line.id,
                'user_id': move_line.move_id.invoice_user_id.id or self._uid,
                'partner_id': move_line.partner_id.id,
                'company_id': move_line.analytic_account_id.company_id.id or move_line.move_id.company_id.id,
            })
        return result

    def _prepare_analytic_distribution_line(self, distribution):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        amount = -self.balance * distribution.percentage / 100.0
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            'account_id': distribution.account_id.id,
            'partner_id': self.partner_id.id,
            'tag_ids': [(6, 0, [distribution.tag_id.id] + self._get_analytic_tag_ids())],
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': distribution.account_id.company_id.id or self.company_id.id or self.env.company.id,
        }

    @api.model
    def _query_get(self, domain=None):
        self.check_access_rights('read')

        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = safe_eval(domain)

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']), ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('parent_state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        if 'company_ids' in context:
            domain += [('company_id', 'in', context['company_ids'])]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.max_date', '>', context['reconcile_date']), ('matched_credit_ids.max_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += [('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        if context.get('partner_ids'):
            domain += [('partner_id', 'in', context['partner_ids'].ids)]

        if context.get('partner_categories'):
            domain += [('partner_id.category_id', 'in', context['partner_categories'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            domain.append(('display_type', 'not in', ('line_section', 'line_note')))
            domain.append(('parent_state', '!=', 'cancel'))

            query = self._where_calc(domain)

            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self._apply_ir_rules(query)

            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params

    def _reconciled_lines(self):
        ids = []
        for aml in self.filtered('account_id.reconcile'):
            ids.extend([r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in aml.matched_credit_ids])
            ids.append(aml.id)
        return ids

    def open_reconcile_view(self):
        [action] = self.env.ref('account.action_account_moves_all_a').read()
        ids = self._reconciled_lines()
        action['domain'] = [('id', 'in', ids)]
        return action

    def action_accrual_entry(self):
        [action] = self.env.ref('account.account_accrual_accounting_wizard_action').read()
        action['context'] = self.env.context
        return action

    @api.model
    def _get_suspense_moves_domain(self):
        return [
            ('move_id.to_check', '=', True),
            ('full_reconcile_id', '=', False),
            ('statement_line_id', '!=', False),
        ]

    def _convert_tags_for_cash_basis(self, tags):
        """ Cash basis entries are managed by the tax report just like misc operations.
        So it means that the tax report will not apply any additional multiplicator
        to the balance of the cash basis lines.

        For invoices move lines whose multiplicator would have been -1 (if their
        taxes had not CABA), it will hence cause sign inversion if we directly copy
        the tags from those lines. Instead, we need to invert all the signs from these
        tags (if they come from tax report lines; tags created in data for financial
        reports will stay onchanged).
        """
        self.ensure_one()
        tax_multiplicator = (self.journal_id.type == 'sale' and -1 or 1) * (self.move_id.type in ('in_refund', 'out_refund') and -1 or 1)
        if tax_multiplicator == -1:
            # Take the opposite tags instead
            return self._revert_signed_tags(tags)

        return tags

    @api.model
    def _revert_signed_tags(self, tags):
        rslt = self.env['account.account.tag']
        for tag in tags:
            if tag.tax_report_line_ids:
                # tag created by an account.tax.report.line
                new_tag = tag.tax_report_line_ids[0].tag_ids.filtered(lambda x: x.tax_negate != tag.tax_negate)
                rslt += new_tag
            else:
                # tag created in data for use by an account.financial.html.report.line
                rslt += tag

        return rslt


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Reconcile"
    _rec_name = "id"

    debit_move_id = fields.Many2one('account.move.line', index=True, required=True)
    credit_move_id = fields.Many2one('account.move.line', index=True, required=True)
    amount = fields.Monetary(currency_field='company_currency_id', help="Amount concerned by this matching. Assumed to be always positive")
    amount_currency = fields.Monetary(string="Amount in Currency")
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_currency_id = fields.Many2one('res.currency', string="Company Currency", related='company_id.currency_id', readonly=True,
        help='Utility field to express amount currency')
    company_id = fields.Many2one('res.company', related='debit_move_id.company_id', store=True, string='Company', readonly=False)
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Full Reconcile", copy=False)
    max_date = fields.Date(string='Max Date of Matched Lines', compute='_compute_max_date',
        readonly=True, copy=False, store=True,
        help='Technical field used to determine at which date this reconciliation needs to be shown on the aged receivable/payable reports.')

    @api.depends('debit_move_id.date', 'credit_move_id.date')
    def _compute_max_date(self):
        for rec in self:
            rec.max_date = max(
                rec.debit_move_id.date,
                rec.credit_move_id.date
            )

    @api.model
    def _prepare_exchange_diff_partial_reconcile(self, aml, line_to_reconcile, currency):
        """
        Prepares the values for the partial reconciliation between an account.move.line
        that needs to be fixed by an exchange rate entry and the account.move.line that fixes it

        @param {account.move.line} aml:
            The line that needs fixing with exchange difference entry
            (e.g. a receivable/payable from an invoice)
        @param {account.move.line} line_to_reconcile:
            The line that fixes the aml. it is the receivable/payable line
            of the exchange difference entry move
        @param {res.currency} currency

        @return {dict} values of account.partial.reconcile; ready for create()
        """

        # the exhange rate difference that will be fixed may be of opposite direction
        # than the original move line (i.e. the exchange difference may be negative whereas
        # the move line on which it applies may be a debit -- positive)
        # So we need to register both the move line and the exchange line
        # to either debit_move or credit_move as a function of whether the direction (debit VS credit)
        # of the exchange loss/gain is the same (or not) as the direction of the line that is fixed here
        if aml.currency_id:
            residual_same_sign = aml.amount_currency * aml.amount_residual_currency >= 0
        else:
            residual_same_sign = aml.balance * aml.amount_residual >= 0

        if residual_same_sign:
            debit_move_id = line_to_reconcile.id if aml.credit else aml.id
            credit_move_id = line_to_reconcile.id if aml.debit else aml.id
        else:
            debit_move_id = aml.id if aml.credit else line_to_reconcile.id
            credit_move_id = aml.id if aml.debit else line_to_reconcile.id

        return {
            'debit_move_id': debit_move_id,
            'credit_move_id': credit_move_id,
            'amount': abs(aml.amount_residual),
            'amount_currency': abs(aml.amount_residual_currency),
            'currency_id': currency and currency.id or False,
        }

    @api.model
    def create_exchange_rate_entry(self, aml_to_fix, move):
        """
        Automatically create a journal items to book the exchange rate
        differences that can occur in multi-currencies environment. That
        new journal item will be made into the given `move` in the company
        `currency_exchange_journal_id`, and one of its journal items is
        matched with the other lines to balance the full reconciliation.
        :param aml_to_fix: recordset of account.move.line (possible several
            but sharing the same currency)
        :param move: account.move
        :return: tuple.
            [0]: account.move.line created to balance the `aml_to_fix`
            [1]: recordset of account.partial.reconcile created between the
                tuple first element and the `aml_to_fix`
        """
        partial_rec = self.env['account.partial.reconcile']
        aml_model = self.env['account.move.line']

        created_lines = self.env['account.move.line']
        for aml in aml_to_fix:
            #create the line that will compensate all the aml_to_fix
            line_to_rec = aml_model.with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'credit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'account_id': aml.account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                'amount_currency': aml.amount_residual_currency and -aml.amount_residual_currency or 0.0,
                'partner_id': aml.partner_id.id,
            })
            #create the counterpart on exchange gain/loss account
            exchange_journal = move.company_id.currency_exchange_journal_id
            aml_model.with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'credit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'account_id': aml.amount_residual > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                'amount_currency': aml.amount_residual_currency and aml.amount_residual_currency or 0.0,
                'partner_id': aml.partner_id.id,
            })

            #reconcile all aml_to_fix
            partial_rec |= self.create(
                self._prepare_exchange_diff_partial_reconcile(
                        aml=aml,
                        line_to_reconcile=line_to_rec,
                        currency=aml.currency_id or False)
            )
            created_lines |= line_to_rec
        return created_lines, partial_rec

    def _get_tax_cash_basis_base_account(self, line, tax):
        ''' Get the account of lines that will contain the base amount of taxes.
        :param line: An account.move.line record
        :param tax: An account.tax record
        :return: An account record
        '''
        return tax.cash_basis_base_account_id or line.account_id

    def _get_amount_tax_cash_basis(self, amount, line):
        return line.company_id.currency_id.round(amount)

    def _set_tax_cash_basis_entry_date(self, move_date, newly_created_move):
        if move_date > (self.company_id.period_lock_date or date.min) and newly_created_move.date != move_date:
            # The move date should be the maximum date between payment and invoice (in case
            # of payment in advance). However, we should make sure the move date is not
            # recorded before the period lock date as the tax statement for this period is
            # probably already sent to the estate.
            newly_created_move.write({'date': move_date})

    def _get_tax_cash_basis_base_key(self, tax, move, line):
        account_id = self._get_tax_cash_basis_base_account(line, tax)
        tax_rep_lines = tax.refund_repartition_line_ids if line.move_id.type in ('in_refund', 'out_refund') else tax.invoice_repartition_line_ids
        original_base_tags = tax_rep_lines.filtered(lambda x: x.repartition_type == 'base').tag_ids
        base_tags = tuple(line._convert_tags_for_cash_basis(original_base_tags).ids)
        return (line.id, account_id.id, tax.id, line.tax_repartition_line_id.id, base_tags,line.currency_id.id, line.partner_id.id, line.move_id.type)

    def _get_tax_cash_basis_base_common_vals(self, key, new_move):
        self.ensure_one()
        line_id, account_id, tax_id, tax_repartition_line_id, base_tags, currency_id, partner_id, move_type = key
        line = self.env['account.move.line'].browse(line_id)
        return {
            'name': line.name,
            'account_id': account_id,
            'journal_id': new_move.journal_id.id,
            'tax_exigible': True,
            'tax_ids': [(6, 0, [tax_id])],
            'tag_ids': [(6, 0, base_tags)],
            'move_id': new_move.id,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'tax_repartition_line_id': tax_repartition_line_id,
        }

    def _create_tax_cash_basis_base_line(self, amount_dict, amount_currency_dict, tax_amount_dict, new_move):
        for key in amount_dict.keys():
            base_line = self._get_tax_cash_basis_base_common_vals(key, new_move)
            currency_id = base_line.get('currency_id', False)
            rounded_amt = amount_dict[key]
            tax_base_amount = tax_amount_dict[key]
            amount_currency = amount_currency_dict[key] if currency_id else 0.0
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            aml_obj.create(dict(
                base_line,
                tax_base_amount=tax_base_amount,
                debit=rounded_amt > 0 and rounded_amt or 0.0,
                credit=rounded_amt < 0 and abs(rounded_amt) or 0.0,
                amount_currency=amount_currency))
            aml_obj.create(dict(
                base_line,
                credit=rounded_amt > 0 and rounded_amt or 0.0,
                debit=rounded_amt < 0 and abs(rounded_amt) or 0.0,
                amount_currency=-amount_currency,
                tax_repartition_line_id=False,
                tax_ids=[],
                tag_ids=[]))

    def create_tax_cash_basis_entry(self, percentage_before_rec):
        self.ensure_one()
        move_date = self.debit_move_id.date
        newly_created_move = self.env['account.move']
        cash_basis_amount_dict = defaultdict(float)
        cash_basis_base_amount_dict = defaultdict(float)
        cash_basis_amount_currency_dict = defaultdict(float)
        # We use a set here in case the reconciled lines belong to the same move (it happens with POS)
        for move in {self.debit_move_id.move_id, self.credit_move_id.move_id}:
            #move_date is the max of the 2 reconciled items
            if move_date < move.date:
                move_date = move.date
            percentage_before = percentage_before_rec[move.id]
            percentage_after = move.line_ids[0]._get_matched_percentage()[move.id]
            # update the percentage before as the move can be part of
            # multiple partial reconciliations
            percentage_before_rec[move.id] = percentage_after

            for line in move.line_ids:
                if not line.tax_exigible:
                    #amount is the current cash_basis amount minus the one before the reconciliation
                    amount = line.balance * percentage_after - line.balance * percentage_before
                    rounded_amt = self._get_amount_tax_cash_basis(amount, line)
                    if float_is_zero(rounded_amt, precision_rounding=line.company_id.currency_id.rounding):
                        continue
                    if line.tax_line_id and line.tax_line_id.tax_exigibility == 'on_payment':
                        if not newly_created_move:
                            newly_created_move = self._create_tax_basis_move()
                        #create cash basis entry for the tax line
                        to_clear_aml = self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': line.move_id.name,
                            'debit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'credit': rounded_amt if rounded_amt > 0 else 0.0,
                            'account_id': line.account_id.id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': line.analytic_tag_ids.ids,
                            'tax_exigible': True,
                            'amount_currency': line.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            'move_id': newly_created_move.id,
                            'partner_id': line.partner_id.id,
                            'journal_id': newly_created_move.journal_id.id,
                        })
                        # Group by cash basis account and tax
                        self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': line.name,
                            'debit': rounded_amt if rounded_amt > 0 else 0.0,
                            'credit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'account_id': line.tax_repartition_line_id.account_id.id or line.account_id.id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': line.analytic_tag_ids.ids,
                            'tax_exigible': True,
                            'amount_currency': line.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            'move_id': newly_created_move.id,
                            'partner_id': line.partner_id.id,
                            'journal_id': newly_created_move.journal_id.id,
                            'tax_repartition_line_id': line.tax_repartition_line_id.id,
                            'tax_base_amount': line.tax_base_amount,
                            'tag_ids': [(6, 0, line._convert_tags_for_cash_basis(line.tag_ids).ids)],
                        })
                        if line.account_id.reconcile and not line.reconciled:
                            #setting the account to allow reconciliation will help to fix rounding errors
                            to_clear_aml |= line
                            to_clear_aml.reconcile()
                    else:
                        #create cash basis entry for the base
                        for tax in line.tax_ids.flatten_taxes_hierarchy().filtered(lambda tax: tax.tax_exigibility == 'on_payment'):
                            # We want to group base lines as much as
                            # possible to avoid creating too many of them.
                            # This will result in a more readable report
                            # tax and less cumbersome to analyse.
                            key = self._get_tax_cash_basis_base_key(tax, move, line)
                            cash_basis_amount_dict[key] += rounded_amt
                            cash_basis_base_amount_dict[key] += line.tax_base_amount
                            cash_basis_amount_currency_dict[key] += line.currency_id.round(line.amount_currency * amount / line.balance) if line.currency_id and self.amount_currency else 0.0

        if cash_basis_amount_dict:
            if not newly_created_move:
                newly_created_move = self._create_tax_basis_move()
            self._create_tax_cash_basis_base_line(cash_basis_amount_dict, cash_basis_amount_currency_dict, cash_basis_base_amount_dict, newly_created_move)
        if newly_created_move:
            self._set_tax_cash_basis_entry_date(move_date, newly_created_move)
            # post move
            newly_created_move.post()

    def _create_tax_basis_move(self):
        # Check if company_journal for cash basis is set if not, raise exception
        if not self.company_id.tax_cash_basis_journal_id:
            raise UserError(_('There is no tax cash basis journal defined '
                              'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') %
                            (self.company_id.name))
        move_vals = {
            'type': 'entry',
            'journal_id': self.company_id.tax_cash_basis_journal_id.id,
            'tax_cash_basis_rec_id': self.id,
            'ref': self.credit_move_id.move_id.name if self.credit_move_id.payment_id else self.debit_move_id.move_id.name,
        }
        return self.env['account.move'].create(move_vals)

    def unlink(self):
        """ When removing a partial reconciliation, also unlink its full reconciliation if it exists """
        full_to_unlink = self.env['account.full.reconcile']
        for rec in self:
            if rec.full_reconcile_id:
                full_to_unlink |= rec.full_reconcile_id
        #reverse the tax basis move created at the reconciliation time
        for move in self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self._ids)]):
            if move.date > (move.company_id.period_lock_date or date.min):
                move._reverse_moves([{'ref': _('Reversal of %s') % move.name}], cancel=True)
            else:
                move._reverse_moves([{'date': fields.Date.today(), 'ref': _('Reversal of %s') % move.name}], cancel=True)
        res = super(AccountPartialReconcile, self).unlink()
        if full_to_unlink:
            full_to_unlink.unlink()
        return res


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _description = "Full Reconcile"

    name = fields.Char(string='Number', required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('account.reconcile'))
    partial_reconcile_ids = fields.One2many('account.partial.reconcile', 'full_reconcile_id', string='Reconciliation Parts')
    reconciled_line_ids = fields.One2many('account.move.line', 'full_reconcile_id', string='Matched Journal Items')
    exchange_move_id = fields.Many2one('account.move')

    def unlink(self):
        """ When removing a full reconciliation, we need to revert the eventual journal entries we created to book the
            fluctuation of the foreign currency's exchange rate.
            We need also to reconcile together the origin currency difference line and its reversal in order to completely
            cancel the currency difference entry on the partner account (otherwise it will still appear on the aged balance
            for example).
        """
        for rec in self:
            if rec.exists() and rec.exchange_move_id:
                # reverse the exchange rate entry after de-referencing it to avoid looping
                # (reversing will cause a nested attempt to drop the full reconciliation)
                to_reverse = rec.exchange_move_id
                rec.exchange_move_id = False
                if to_reverse.date > (to_reverse.company_id.period_lock_date or date.min):
                    reverse_date = to_reverse.date
                else:
                    reverse_date = fields.Date.today()
                to_reverse._reverse_moves([{
                    'date': reverse_date,
                    'ref': _('Reversal of: %s') % to_reverse.name,
                }], cancel=True)
        return super(AccountFullReconcile, self).unlink()

    @api.model
    def _prepare_exchange_diff_move(self, move_date, company):
        if not company.currency_exchange_journal_id:
            raise UserError(_("You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        if not company.income_currency_exchange_account_id.id:
            raise UserError(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        if not company.expense_currency_exchange_account_id.id:
            raise UserError(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        res = {'journal_id': company.currency_exchange_journal_id.id}
        # The move date should be the maximum date between payment and invoice
        # (in case of payment in advance). However, we should make sure the
        # move date is not recorded after the end of year closing.
        if move_date > (company.fiscalyear_lock_date or date.min):
            res['date'] = move_date
        return res
