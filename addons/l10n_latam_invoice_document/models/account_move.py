# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from functools import partial
from odoo.tools.misc import formatLang


class AccountMove(models.Model):

    _inherit = "account.move"

    l10n_latam_amount_untaxed = fields.Monetary(compute='_compute_l10n_latam_amount_and_taxes')
    l10n_latam_tax_ids = fields.One2many(compute="_compute_l10n_latam_amount_and_taxes", comodel_name='account.move.line')
    l10n_latam_available_document_type_ids = fields.Many2many('l10n_latam.document.type', compute='_compute_l10n_latam_documents')
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', string='Document Type', copy=False, readonly=True, auto_join=True, index=True,
        states={'posted': [('readonly', True)]})
    l10n_latam_sequence_id = fields.Many2one('ir.sequence', compute='_compute_l10n_latam_sequence')
    l10n_latam_document_number = fields.Char(
        compute='_compute_l10n_latam_document_number', inverse='_inverse_l10n_latam_document_number',
        string='Document Number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_latam_use_documents = fields.Boolean(related='journal_id.l10n_latam_use_documents')
    l10n_latam_country_code = fields.Char(
        related='company_id.country_id.code', help='Technical field used to hide/show fields regarding the localization')

    def _get_sequence_prefix(self):
        """ If we use documents we update sequences only from journal """
        return super(AccountMove, self.filtered(lambda x: not x.l10n_latam_use_documents))._get_sequence_prefix()

    @api.depends('name')
    def _compute_l10n_latam_document_number(self):
        recs_with_name = self.filtered(lambda x: x.name != '/')
        for rec in recs_with_name:
            name = rec.name
            doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
            if doc_code_prefix and name:
                name = name.split(" ", 1)[-1]
            rec.l10n_latam_document_number = name
        remaining = self - recs_with_name
        remaining.l10n_latam_document_number = False

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        for rec in self.filtered('l10n_latam_document_type_id'):
            if not rec.l10n_latam_document_number:
                rec.name = '/'
            else:
                l10n_latam_document_number = rec.l10n_latam_document_type_id._format_document_number(rec.l10n_latam_document_number)
                if rec.l10n_latam_document_number != l10n_latam_document_number:
                    rec.l10n_latam_document_number = l10n_latam_document_number
                rec.name = "%s %s" % (rec.l10n_latam_document_type_id.doc_code_prefix, l10n_latam_document_number)

    @api.depends('l10n_latam_document_type_id', 'journal_id')
    def _compute_l10n_latam_sequence(self):
        recs_with_journal_id = self.filtered('journal_id')
        for rec in recs_with_journal_id:
            rec.l10n_latam_sequence_id = rec._get_document_type_sequence()
        remaining = self - recs_with_journal_id
        remaining.l10n_latam_sequence_id = False

    def _compute_l10n_latam_amount_and_taxes(self):
        recs_invoice = self.filtered(lambda x: x.is_invoice())
        for invoice in recs_invoice:
            tax_lines = invoice.line_ids.filtered('tax_line_id')
            included_taxes = invoice.l10n_latam_document_type_id and \
                invoice.l10n_latam_document_type_id._filter_taxes_included(tax_lines.mapped('tax_line_id'))
            if not included_taxes:
                l10n_latam_amount_untaxed = invoice.amount_untaxed
                not_included_invoice_taxes = tax_lines
            else:
                included_invoice_taxes = tax_lines.filtered(lambda x: x.tax_line_id in included_taxes)
                not_included_invoice_taxes = tax_lines - included_invoice_taxes
                if invoice.is_inbound():
                    sign = -1
                else:
                    sign = 1
                l10n_latam_amount_untaxed = invoice.amount_untaxed + sign * sum(included_invoice_taxes.mapped('balance'))
            invoice.l10n_latam_amount_untaxed = l10n_latam_amount_untaxed
            invoice.l10n_latam_tax_ids = not_included_invoice_taxes
        remaining = self - recs_invoice
        remaining.l10n_latam_amount_untaxed = False
        remaining.l10n_latam_tax_ids = []

    def _compute_invoice_sequence_number_next(self):
        """ If journal use documents disable the next number header"""
        with_latam_document_number = self.filtered('l10n_latam_use_documents')
        with_latam_document_number.invoice_sequence_number_next_prefix = False
        with_latam_document_number.invoice_sequence_number_next = False
        return super(AccountMove, self - with_latam_document_number)._compute_invoice_sequence_number_next()

    def post(self):
        for rec in self.filtered(lambda x: x.l10n_latam_use_documents and (not x.name or x.name == '/')):
            if not rec.l10n_latam_sequence_id:
                raise UserError(_('No sequence or document number linked to invoice id %s') % rec.id)
            if rec.type in ('in_receipt', 'out_receipt'):
                raise UserError(_('We do not accept the usage of document types on receipts yet. '))
            rec.l10n_latam_document_number = rec.l10n_latam_sequence_id.next_by_id()
        return super().post()

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        """ Do not apply unique sequence number for vendoer bills and refunds.
        Also apply constraint when state change """
        vendor = self.filtered(lambda x: x.type in ['in_refund', 'in_invoice'])
        try:
            return super(AccountMove, self - vendor)._check_unique_sequence_number()
        except ValidationError:
            raise ValidationError(_('Duplicated invoice number detected. You probably added twice the same vendor'
                                    ' bill/debit note.'))

    @api.constrains('state', 'l10n_latam_document_type_id')
    def _check_l10n_latam_documents(self):
        validated_invoices = self.filtered(lambda x: x.l10n_latam_use_documents and x.state in ['open', 'done'])
        without_doc_type = validated_invoices.filtered(lambda x: not x.l10n_latam_document_type_id)
        if without_doc_type:
            raise ValidationError(_(
                'The journal require a document type but not document type has been selected on invoices %s.' % (
                    without_doc_type.ids)))
        without_number = validated_invoices.filtered(
            lambda x: not x.l10n_latam_document_number and not x.l10n_latam_sequence_id)
        if without_number:
            raise ValidationError(_('Please set the document number on the following invoices %s.' % (
                without_number.ids)))

    @api.constrains('type', 'l10n_latam_document_type_id')
    def _check_invoice_type_document_type(self):
        for rec in self.filtered('l10n_latam_document_type_id.internal_type'):
            internal_type = rec.l10n_latam_document_type_id.internal_type
            invoice_type = rec.type
            if internal_type in ['debit_note', 'invoice'] and invoice_type in ['out_refund', 'in_refund']:
                raise ValidationError(_('You can not use a %s document type with a refund invoice') % internal_type)
            elif internal_type == 'credit_note' and invoice_type in ['out_invoice', 'in_invoice']:
                raise ValidationError(_('You can not use a %s document type with a invoice') % (internal_type))

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if self.type in ['out_refund', 'in_refund']:
            internal_types = ['credit_note']
        else:
            internal_types = ['invoice', 'debit_note']
        return [('internal_type', 'in', internal_types), ('country_id', '=', self.company_id.country_id.id)]

    @api.depends('journal_id', 'partner_id', 'company_id')
    def _compute_l10n_latam_documents(self):
        internal_type = self._context.get('internal_type', False)
        recs_with_journal_partner = self.filtered(lambda x: x.journal_id and x.l10n_latam_use_documents and x.partner_id)
        for rec in recs_with_journal_partner:
            document_types = self.env['l10n_latam.document.type'].search(rec._get_l10n_latam_documents_domain())

            # If internal_type is in context we try to search for an specific document. for eg used on debit notes
            document_type = internal_type and document_types.filtered(
                lambda x: x.internal_type == internal_type) or document_types

            rec.l10n_latam_available_document_type_ids = document_types
            rec.l10n_latam_document_type_id = document_type and document_type[0]
        remaining = self - recs_with_journal_partner
        remaining.l10n_latam_available_document_type_ids = []
        remaining.l10n_latam_document_type_id = False

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs.filtered(lambda x: x.l10n_latam_use_documents and not x.l10n_latam_document_type_id)._compute_l10n_latam_documents()
        return recs

    def _compute_invoice_taxes_by_group(self):
        move_with_doc_type = self.filtered('l10n_latam_document_type_id')
        for move in move_with_doc_type:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_lines = move.l10n_latam_tax_ids
            res = {}
            for line in tax_lines:
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += line.price_subtotal
                res[line.tax_line_id.tax_group_id]['base'] += line.tax_base_amount
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            move.amount_by_group = [(
                group.name, amounts['amount'],
                amounts['base'],
                formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
            ) for group, amounts in res]
        super(AccountMove, self - move_with_doc_type)._compute_invoice_taxes_by_group()

    def _get_document_type_sequence(self):
        """ Method to be inherited by different localizations. """
        self.ensure_one()
        return self.env['ir.sequence']

    @api.constrains('name', 'partner_id', 'company_id')
    def _check_unique_vendor_number(self):
        """ The constraint _check_unique_sequence_number is valid for customer bills but not valid for us on vendor
        bills because the uniqueness must be per partner and also because we want to validate on entry creation and
        not on entry validation """
        for rec in self.filtered(lambda x: x.is_purchase_document() and x.l10n_latam_use_documents and x.l10n_latam_document_number):
            domain = [
                ('type', '=', rec.type),
                # by validating name we validate l10n_latam_document_number and l10n_latam_document_type_id
                ('name', '=', rec.name),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
                ('commercial_partner_id', '=', rec.commercial_partner_id.id)
            ]
            if rec.search(domain):
                raise ValidationError(_('Vendor bill number must be unique per vendor and company.'))
