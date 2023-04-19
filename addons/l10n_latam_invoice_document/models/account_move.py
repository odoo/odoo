# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from textwrap import shorten

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import column_exists, create_column, drop_index, index_exists
from odoo.tools import format_date


class AccountMove(models.Model):

    _inherit = "account.move"

    _sql_constraints = [(
        'unique_name', "", "Another entry with the same name already exists.",
    ), (
        'unique_name_latam', "", "Another entry with the same name already exists.",
    )]

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

        if not index_exists(self.env.cr, "account_move_unique_name_latam"):
            drop_index(self.env.cr, "account_move_unique_name", self._table)
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_move_unique_name
                                 ON account_move(name, journal_id)
                              WHERE (state = 'posted' AND name != '/'
                                AND (l10n_latam_document_type_id IS NULL OR move_type NOT IN ('in_invoice', 'in_refund', 'in_receipt')));
                CREATE UNIQUE INDEX account_move_unique_name_latam
                                 ON account_move(name, commercial_partner_id, l10n_latam_document_type_id, company_id)
                              WHERE (state = 'posted' AND name != '/'
                                AND (l10n_latam_document_type_id IS NOT NULL AND move_type IN ('in_invoice', 'in_refund', 'in_receipt')));
            """)
        return super()._auto_init()

    l10n_latam_available_document_type_ids = fields.Many2many('l10n_latam.document.type', compute='_compute_l10n_latam_available_document_types')
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', string='Document Type', readonly=False, auto_join=True, index='btree_not_null',
        states={'posted': [('readonly', True)]}, compute='_compute_l10n_latam_document_type', store=True)
    # TODO rename this field?
    # this fields represents the stored value of the document number without the prefix.
    # for simplcity on migration anf proof of concept with do this way.
    # somewhow this field replace usage of actual account.move.name field
    l10n_latam_full_document_number = fields.Char(
        string='Document Number (full)', readonly=True, states={'draft': [('readonly', False)]})
    l10n_latam_document_number = fields.Char(
        compute='_compute_l10n_latam_document_number', inverse='_inverse_l10n_latam_document_number',
        string='Document Number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_latam_use_documents = fields.Boolean(related='journal_id.l10n_latam_use_documents')
    l10n_latam_manual_document_number = fields.Boolean(compute='_compute_l10n_latam_manual_document_number', string='Manual Number')
    l10n_latam_document_type_id_code = fields.Char(related='l10n_latam_document_type_id.code', string='Doc Type')

    # @api.depends('l10n_latam_document_type_id')
    # def _compute_name(self):
    #     """ Change the way that the use_document moves name is computed:

    #     * If move use document but does not have document type selected then name = '/' to do not show the name.
    #     * If move use document and are numbered manually do not compute name at all (will be set manually)
    #     * If move use document and is in draft state and has not been posted before we restart name to '/' (this is
    #        when we change the document type) """
    #     without_doc_type = self.filtered(lambda x: x.journal_id.l10n_latam_use_documents and not x.l10n_latam_document_type_id)
    #     manual_documents = self.filtered(lambda x: x.journal_id.l10n_latam_use_documents and x.l10n_latam_manual_document_number)
    #     (without_doc_type + manual_documents.filtered(lambda x: not x.name or x.name and x.state == 'draft' and not x.posted_before)).name = '/'
    #     # we need to group moves by document type as _compute_name will apply the same name prefix of the first record to the others
    #     group_by_document_type = defaultdict(self.env['account.move'].browse)
    #     for move in (self - without_doc_type - manual_documents):
    #         group_by_document_type[move.l10n_latam_document_type_id.id] += move
    #     for group in group_by_document_type.values():
    #         super(AccountMove, group)._compute_name()

    @api.depends('l10n_latam_document_type_id', 'journal_id')
    def _compute_l10n_latam_manual_document_number(self):
        """ Indicates if this document type uses a sequence or if the numbering is made manually """
        recs_with_journal_id = self.filtered(lambda x: x.journal_id and x.journal_id.l10n_latam_use_documents)
        for rec in recs_with_journal_id:
            rec.l10n_latam_manual_document_number = rec._is_manual_document_number()
        remaining = self - recs_with_journal_id
        remaining.l10n_latam_manual_document_number = False

    def _is_manual_document_number(self):
        return True
        # TODO when we implement sequence restore this behaviour
        # return self.journal_id.type == 'purchase'

    @api.depends('l10n_latam_full_document_number')
    def _compute_l10n_latam_document_number(self):
        recs_with_name = self.filtered(lambda x: x.l10n_latam_full_document_number)
        for rec in recs_with_name:
            name = rec.l10n_latam_full_document_number
            doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
            if doc_code_prefix and name:
                name = name.split(" ", 1)[-1]
            rec.l10n_latam_document_number = name
        remaining = self - recs_with_name
        remaining.l10n_latam_document_number = False

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        for rec in self.filtered(lambda x: x.l10n_latam_document_type_id):
            if not rec.l10n_latam_document_number:
                rec.l10n_latam_full_document_number = False
            else:
                l10n_latam_document_number = rec.l10n_latam_document_type_id._format_document_number(rec.l10n_latam_document_number)
                if rec.l10n_latam_document_number != l10n_latam_document_number:
                    rec.l10n_latam_document_number = l10n_latam_document_number
                rec.l10n_latam_full_document_number = "%s %s" % (rec.l10n_latam_document_type_id.doc_code_prefix, l10n_latam_document_number)

    # @api.onchange('l10n_latam_document_type_id')
    # def _onchange_l10n_latam_document_type_id(self):
    #     # if we change document or journal and we are in draft and not posted, we clean number so that is recomputed
    #     if (self.journal_id.l10n_latam_use_documents and self.l10n_latam_document_type_id
    #           and not self.l10n_latam_manual_document_number and self.state == 'draft' and not self.posted_before):
    #         self.name = '/'
    #         self._compute_name()

    # @api.depends('journal_id', 'l10n_latam_document_type_id')
    # def _compute_highest_name(self):
    #     manual_records = self.filtered('l10n_latam_manual_document_number')
    #     manual_records.highest_name = ''
    #     super(AccountMove, self - manual_records)._compute_highest_name()

    # @api.model
    # def _deduce_sequence_number_reset(self, name):
    #     if self.l10n_latam_use_documents:
    #         return 'never'
    #     return super(AccountMove, self)._deduce_sequence_number_reset(name)

    # def _get_starting_sequence(self):
    #     if self.journal_id.l10n_latam_use_documents:
    #         if self.l10n_latam_document_type_id:
    #             return "%s 00000000" % (self.l10n_latam_document_type_id.doc_code_prefix)
    #         # There was no pattern found, propose one
    #         return ""

    #     return super(AccountMove, self)._get_starting_sequence()

    def _post(self, soft=True):
        for rec in self.filtered(lambda x: x.move_type in ('in_receipt', 'out_receipt') and x.l10n_latam_use_documents):
            raise UserError(_('We do not accept the usage of document types on receipts yet. '))
        return super()._post(soft)

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
            if internal_type in ['debit_note', 'invoice'] and invoice_type in ['out_refund', 'in_refund']:
                raise ValidationError(_('You can not use a %s document type with a refund invoice', internal_type))
            elif internal_type == 'credit_note' and invoice_type in ['out_invoice', 'in_invoice']:
                raise ValidationError(_('You can not use a %s document type with a invoice', internal_type))

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if self.move_type in ['out_refund', 'in_refund']:
            internal_types = ['credit_note']
        else:
            internal_types = ['invoice', 'debit_note']
        return [('internal_type', 'in', internal_types), ('country_id', '=', self.company_id.account_fiscal_country_id.id)]

    @api.depends('journal_id', 'partner_id', 'company_id', 'move_type')
    def _compute_l10n_latam_available_document_types(self):
        self.l10n_latam_available_document_type_ids = False
        for rec in self.filtered(lambda x: x.journal_id and x.l10n_latam_use_documents and x.partner_id):
            rec.l10n_latam_available_document_type_ids = self.env['l10n_latam.document.type'].search(rec._get_l10n_latam_documents_domain())

    @api.depends('l10n_latam_available_document_type_ids', 'debit_origin_id')
    def _compute_l10n_latam_document_type(self):
        for rec in self.filtered(lambda x: x.state == 'draft'):
            document_types = rec.l10n_latam_available_document_type_ids._origin
            invoice_type = rec.move_type
            if invoice_type in ['out_refund', 'in_refund']:
                document_types = document_types.filtered(lambda x: x.internal_type not in ['debit_note', 'invoice'])
            elif invoice_type in ['out_invoice', 'in_invoice']:
                document_types = document_types.filtered(lambda x: x.internal_type not in ['credit_note'])
            if rec.debit_origin_id:
                document_types = document_types.filtered(lambda x: x.internal_type == 'debit_note')
            rec.l10n_latam_document_type_id = document_types and document_types[0].id

    # super method is not using anymore? maybe remove this and super?
    def _get_invoice_reference_odoo_invoice(self):
        if not self.l10n_latam_use_documents:
            return super()._get_invoice_reference_odoo_invoice()
        return self.l10n_latam_full_document_number

    def _get_move_display_name(self, show_ref=False):
        if self._context.get('latam_display_internal_name') or not self.l10n_latam_use_documents:
            return super()._get_move_display_name(show_ref=show_ref)
        self.ensure_one()
        name = ''
        if self.state == 'draft':
            name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Credit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Draft Entry'),
            }[self.move_type]
            name += ' '
        if not self.l10n_latam_full_document_number:
            name += '(* %s)' % str(self.id)
        else:
            name += self.l10n_latam_full_document_number
            if self.env.context.get('input_full_display_name'):
                if self.partner_id:
                    name += f', {self.partner_id.name}'
                if self.date:
                    name += f', {format_date(self.env, self.date)}'
        return name + (f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else '')
