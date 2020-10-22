# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
from odoo.tools.misc import formatLang
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):

    _inherit = "account.move"

    def _auto_init(self):
        # Skip the computation of the field `l10n_latam_document_type_id` at the module installation
        # Without this, at the module installation,
        # it would call `_compute_l10n_latam_document_type` on all existing records
        # which can take quite a while if you already have a lot of moves. It can even fail with a MemoryError.
        # In addition, it sets `_compute_l10n_latam_document_type = False` on all records
        # because this field depends on the many2many `l10n_latam_available_document_type_ids`,
        # which relies on having records for the model `l10n_latam.document.type`
        # which only happens once the according localization module is loaded.
        # The localization module is loaded afterwards, because the localization module depends on this module,
        # (e.g. `l10n_cl` depends on `l10n_latam_invoice_document`, and therefore `l10n_cl` is loaded after)
        # and therefore there are no records for the model `l10n_latam.document.type` at the time this fields
        # gets computed on installation. Hence, all records' `_compute_l10n_latam_document_type` are set to `False`.
        # In addition, multiple localization module depends on this module (e.g. `l10n_cl`, `l10n_ar`)
        # So, imagine `l10n_cl` gets installed first, and then `l10n_ar` is installed next,
        # if `l10n_latam_document_type_id` needed to be computed on install,
        # the install of `l10n_cl` would call the compute method,
        # because `l10n_latam_invoice_document` would be installed at the same time,
        # but then `l10n_ar` would miss it, because `l10n_latam_invoice_document` would already be installed.
        # Besides, this field is computed only for drafts invoices, as stated in the compute method:
        # `for rec in self.filtered(lambda x: x.state == 'draft'):`
        # So, if we want this field to be computed on install, it must be done only on draft invoices, and only once
        # the localization modules are loaded.
        # It should be done in a dedicated post init hook,
        # filtering correctly the invoices for which it must be computed.
        # Though I don't think this is needed.
        # In practical, it's very rare to already have invoices (draft, in addition)
        # for a Chilian or Argentian company (`res.company`) before installing `l10n_cl` or `l10n_ar`.
        if not column_exists(self.env.cr, "account_move", "l10n_latam_document_type_id"):
            create_column(self.env.cr, "account_move", "l10n_latam_document_type_id", "int4")
        return super()._auto_init()

    l10n_latam_amount_untaxed = fields.Monetary(compute='_compute_l10n_latam_amount_and_taxes')
    l10n_latam_tax_ids = fields.One2many(compute="_compute_l10n_latam_amount_and_taxes", comodel_name='account.move.line')
    l10n_latam_available_document_type_ids = fields.Many2many('l10n_latam.document.type', compute='_compute_l10n_latam_available_document_types')
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', string='Document Type', readonly=False, auto_join=True, index=True,
        states={'posted': [('readonly', True)]}, compute='_compute_l10n_latam_document_type', store=True)
    l10n_latam_document_number = fields.Char(
        compute='_compute_l10n_latam_document_number', inverse='_inverse_l10n_latam_document_number',
        string='Document Number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_latam_use_documents = fields.Boolean(related='journal_id.l10n_latam_use_documents')
    l10n_latam_manual_document_number = fields.Boolean(compute='_compute_l10n_latam_manual_document_number', string='Manual Number')

    @api.depends('l10n_latam_document_type_id')
    def _compute_name(self):
        """ Change the way that the use_document moves name is computed:

        * If move use document but does not have document type selected then name = '/' to do not show the name.
        * If move use document and are numbered manually do not compute name at all (will be set manually)
        * If move use document and is in draft state and has not been posted before we restart name to '/' (this is
           when we change the document type) """
        without_doc_type = self.filtered(lambda x: x.journal_id.l10n_latam_use_documents and not x.l10n_latam_document_type_id)
        manual_documents = self.filtered(lambda x: x.journal_id.l10n_latam_use_documents and x.l10n_latam_manual_document_number)
        (without_doc_type + manual_documents.filtered(lambda x: not x.name or x.name and x.state == 'draft' and not x.posted_before)).name = '/'
        # if we change document or journal and we are in draft and not posted, we clean number so that is recomputed in super
        self.filtered(
            lambda x: x.journal_id.l10n_latam_use_documents and x.l10n_latam_document_type_id
            and not x.l10n_latam_manual_document_number and x.state == 'draft' and not x.posted_before).name = '/'
        super(AccountMove, self - without_doc_type - manual_documents)._compute_name()

    @api.depends('l10n_latam_document_type_id', 'journal_id')
    def _compute_l10n_latam_manual_document_number(self):
        """ Indicates if this document type uses a sequence or if the numbering is made manually """
        recs_with_journal_id = self.filtered(lambda x: x.journal_id and x.journal_id.l10n_latam_use_documents)
        for rec in recs_with_journal_id:
            rec.l10n_latam_manual_document_number = self._is_manual_document_number(rec.journal_id)
        remaining = self - recs_with_journal_id
        remaining.l10n_latam_manual_document_number = False

    def _is_manual_document_number(self, journal):
        return True if journal.type == 'purchase' else False

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
        for rec in self.filtered(lambda x: x.l10n_latam_document_type_id and (x.l10n_latam_manual_document_number or not x.highest_name)):
            if not rec.l10n_latam_document_number:
                rec.name = '/'
            else:
                l10n_latam_document_number = rec.l10n_latam_document_type_id._format_document_number(rec.l10n_latam_document_number)
                if rec.l10n_latam_document_number != l10n_latam_document_number:
                    rec.l10n_latam_document_number = l10n_latam_document_number
                rec.name = "%s %s" % (rec.l10n_latam_document_type_id.doc_code_prefix, l10n_latam_document_number)

    @api.depends('journal_id', 'l10n_latam_document_type_id')
    def _compute_highest_name(self):
        manual_records = self.filtered('l10n_latam_manual_document_number')
        manual_records.highest_name = ''
        super(AccountMove, self - manual_records)._compute_highest_name()

    @api.model
    def _deduce_sequence_number_reset(self, name):
        if self.l10n_latam_use_documents:
            return 'never'
        return super(AccountMove, self)._deduce_sequence_number_reset(name)

    def _get_starting_sequence(self):
        if self.journal_id.l10n_latam_use_documents:
            if self.l10n_latam_document_type_id:
                return "%s 00000000" % (self.l10n_latam_document_type_id.doc_code_prefix)
            # There was no pattern found, propose one
            return ""

        return super(AccountMove, self)._get_starting_sequence()

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
        remaining.l10n_latam_tax_ids = [(5, 0)]

    def _post(self, soft=True):
        for rec in self.filtered(lambda x: x.l10n_latam_use_documents and (not x.name or x.name == '/')):
            if rec.move_type in ('in_receipt', 'out_receipt'):
                raise UserError(_('We do not accept the usage of document types on receipts yet. '))
        return super()._post(soft)

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        """ This uniqueness verification is only valid for customer invoices, and vendor bills that does not use
        documents. A new constraint method _check_unique_vendor_number has been created just for validate for this purpose """
        vendor = self.filtered(lambda x: x.is_purchase_document() and x.l10n_latam_use_documents)
        return super(AccountMove, self - vendor)._check_unique_sequence_number()

    @api.constrains('state', 'l10n_latam_document_type_id')
    def _check_l10n_latam_documents(self):
        """ This constraint checks that if a invoice is posted and does not have a document type configured will raise
        an error. This only applies to invoices related to journals that has the "Use Documents" set as True.
        And if the document type is set then check if the invoice number has been set, because a posted invoice
        without a document number is not valid in the case that the related journals has "Use Docuemnts" set as True """
        validated_invoices = self.filtered(lambda x: x.l10n_latam_use_documents and x.state == 'posted')
        without_doc_type = validated_invoices.filtered(lambda x: not x.l10n_latam_document_type_id)
        if without_doc_type:
            raise ValidationError(_(
                'The journal require a document type but not document type has been selected on invoices %s.',
                without_doc_type.ids
            ))
        without_number = validated_invoices.filtered(
            lambda x: not x.l10n_latam_document_number and x.l10n_latam_manual_document_number)
        if without_number:
            raise ValidationError(_(
                'Please set the document number on the following invoices %s.',
                without_number.ids
            ))

    @api.constrains('move_type', 'l10n_latam_document_type_id')
    def _check_invoice_type_document_type(self):
        for rec in self.filtered('l10n_latam_document_type_id.internal_type'):
            internal_type = rec.l10n_latam_document_type_id.internal_type
            invoice_type = rec.move_type
            if internal_type in ['debit_note', 'invoice'] and invoice_type in ['out_refund', 'in_refund'] and \
               rec.l10n_latam_document_type_id.code != '99':
                raise ValidationError(_('You can not use a %s document type with a refund invoice', internal_type))
            elif internal_type == 'credit_note' and invoice_type in ['out_invoice', 'in_invoice']:
                raise ValidationError(_('You can not use a %s document type with a invoice', internal_type))

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if self.move_type in ['out_refund', 'in_refund']:
            internal_types = ['credit_note']
        else:
            internal_types = ['invoice', 'debit_note']
        return [('internal_type', 'in', internal_types), ('country_id', '=', self.company_id.country_id.id)]

    @api.depends('journal_id', 'partner_id', 'company_id', 'move_type')
    def _compute_l10n_latam_available_document_types(self):
        self.l10n_latam_available_document_type_ids = False
        for rec in self.filtered(lambda x: x.journal_id and x.l10n_latam_use_documents and x.partner_id):
            rec.l10n_latam_available_document_type_ids = self.env['l10n_latam.document.type'].search(rec._get_l10n_latam_documents_domain())

    @api.depends('l10n_latam_available_document_type_ids', 'debit_origin_id')
    def _compute_l10n_latam_document_type(self):
        debit_note = self.debit_origin_id
        for rec in self.filtered(lambda x: x.state == 'draft'):
            document_types = rec.l10n_latam_available_document_type_ids._origin
            document_types = debit_note and document_types.filtered(lambda x: x.internal_type == 'debit_note') or document_types
            rec.l10n_latam_document_type_id = document_types and document_types[0].id

    def _compute_invoice_taxes_by_group(self):
        report_or_portal_view = 'commit_assetsbundle' in self.env.context or \
            not self.env.context.get('params', {}).get('view_type') == 'form'
        if not report_or_portal_view:
            return super()._compute_invoice_taxes_by_group()

        move_with_doc_type = self.filtered('l10n_latam_document_type_id')
        for move in move_with_doc_type:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_lines = move.l10n_latam_tax_ids
            res = {}
            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in tax_lines:
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += line.price_subtotal
                tax_key_add_base = tuple(move._get_tax_key_for_group_add_base(line))
                if tax_key_add_base not in done_taxes:
                    # The base should be added ONCE
                    res[line.tax_line_id.tax_group_id]['base'] += line.tax_base_amount
                    done_taxes.add(tax_key_add_base)
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            move.amount_by_group = [(
                group.name, amounts['amount'],
                amounts['base'],
                formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
                group.id,
            ) for group, amounts in res]
        super(AccountMove, self - move_with_doc_type)._compute_invoice_taxes_by_group()

    @api.constrains('name', 'partner_id', 'company_id', 'posted_before')
    def _check_unique_vendor_number(self):
        """ The constraint _check_unique_sequence_number is valid for customer bills but not valid for us on vendor
        bills because the uniqueness must be per partner """
        for rec in self.filtered(
                lambda x: x.name and x.name != '/' and x.is_purchase_document() and x.l10n_latam_use_documents):
            domain = [
                ('move_type', '=', rec.move_type),
                # by validating name we validate l10n_latam_document_type_id
                ('name', '=', rec.name),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
                ('commercial_partner_id', '=', rec.commercial_partner_id.id),
                # allow to have to equal if they are cancelled
                ('state', '!=', 'cancel'),
            ]
            if rec.search(domain):
                raise ValidationError(_('Vendor bill number must be unique per vendor and company.'))
