# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    l10n_latam_amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_l10n_latam_amount_and_taxes'
    )
    l10n_latam_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_l10n_latam_amount_and_taxes'
    )
    l10n_latam_tax_line_ids = fields.One2many(
        compute="_compute_l10n_latam_amount_and_taxes",
        comodel_name='account.invoice.tax',
        string='Taxes'
    )
    l10n_latam_available_document_type_ids = fields.Many2many(
        'l10n_latam.document.type',
        compute='_compute_l10n_latam_available_document_types',
        string='Available Document Types',
    )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Document Type',
        copy=False,
        readonly=True,
        auto_join=True,
        index=True,
    )
    l10n_latam_sequence_id = fields.Many2one(
        'ir.sequence',
        compute='_compute_l10n_latam_sequence',
    )
    l10n_latam_document_number = fields.Char(
        compute='_compute_l10n_latam_document_number',
        inverse='_inverse_l10n_latam_document_number',
        string='Document Number',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        index=True,
    )
    l10n_latam_use_documents = fields.Boolean(
        related='journal_id.l10n_latam_use_documents',
    )
    l10n_latam_country_code = fields.Char(
        related='company_id.country_id.code',
        help='Technical field used to hide/show fields regarding the '
        'localization'
    )
    def _get_sequence_prefix(self):
        """ If we use documents we update sequences only from journal """
        return super(AccountInvoice, self.filtered(
            lambda x: not x.l10n_latam_use_documents))._get_sequence_prefix()

    @api.depends('move_name')
    def _compute_l10n_latam_document_number(self):
        for rec in self:
            move_name = rec.move_name
            doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
            if doc_code_prefix and move_name:
                move_name = move_name.replace(doc_code_prefix + " ", "")
            rec.l10n_latam_document_number = move_name

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        for rec in self.filtered('l10n_latam_document_type_id'):
            l10n_latam_document_number = \
                rec.l10n_latam_document_type_id._format_document_number(
                    rec.l10n_latam_document_number)
            if rec.l10n_latam_document_number != l10n_latam_document_number:
                rec.l10n_latam_document_number = l10n_latam_document_number
            rec.move_name = l10n_latam_document_number and "%s %s" % (
                rec.l10n_latam_document_type_id.doc_code_prefix,
                l10n_latam_document_number)

    @api.depends('l10n_latam_document_type_id', 'journal_id')
    def _compute_l10n_latam_sequence(self):
        for rec in self.filtered('journal_id'):
            rec.l10n_latam_sequence_id = \
                rec.journal_id.get_document_type_sequence(rec)

    @api.depends(
        'amount_untaxed', 'amount_tax', 'tax_line_ids', 'l10n_latam_document_type_id')
    def _compute_l10n_latam_amount_and_taxes(self):
        for invoice in self:
            taxes_included = (
                invoice.l10n_latam_document_type_id and
                invoice.l10n_latam_document_type_id.get_taxes_included() or False)
            if not taxes_included:
                l10n_latam_amount_tax = invoice.amount_tax
                l10n_latam_amount_untaxed = invoice.amount_untaxed
                not_included_taxes = invoice.tax_line_ids
            else:
                included_taxes = invoice.tax_line_ids.filtered(
                    lambda x: x.tax_id in taxes_included)
                not_included_taxes = (
                    invoice.tax_line_ids - included_taxes)
                l10n_latam_amount_tax = sum(not_included_taxes.mapped('amount'))
                l10n_latam_amount_untaxed = invoice.amount_untaxed + sum(
                    included_taxes.mapped('amount'))
            invoice.l10n_latam_amount_tax = l10n_latam_amount_tax
            invoice.l10n_latam_amount_untaxed = l10n_latam_amount_untaxed
            invoice.l10n_latam_tax_line_ids = not_included_taxes

    @api.constrains(
        'journal_id',
        'partner_id',
        'l10n_latam_document_type_id',
    )
    def _get_document_type(self):
        """ Como los campos responsible y journal document type no los
        queremos hacer funcion porque no queremos que sus valores cambien nunca
        y como con la funcion anterior solo se almacenan solo si se crea desde
        interfaz, hacemos este hack de constraint para computarlos si no estan
        computados"""
        for rec in self.filtered(
                lambda x: not x.l10n_latam_document_type_id and
                x.l10n_latam_available_document_type_ids):
            rec.l10n_latam_document_type_id = (
                rec._get_available_document_types(
                    rec.journal_id, rec.type, rec.partner_id
                ).get('document_type'))

    @api.multi
    def action_move_create(self):
        self._pre_action_move_create()
        res = super(AccountInvoice, self).action_move_create()
        self._post_action_move_create()
        return res

    @api.multi
    def _pre_action_move_create(self):
        for rec in self.filtered('l10n_latam_use_documents'):
            if not rec.l10n_latam_document_type_id:
                raise UserError(_(
                    'The journal require a document type but not '
                    'document type has been selected on invoice id %s.' % (
                        rec.id)))
            if not rec.l10n_latam_document_number:
                if not rec.l10n_latam_sequence_id:
                    raise UserError(_(
                        'Error!. Please define sequence on the journal '
                        'related documents to this invoice or set the '
                        'document number.'))
                rec.l10n_latam_document_number = \
                    rec.l10n_latam_sequence_id.next_by_id()

    @api.multi
    def _post_action_move_create(self):
        for rec in self.filtered('l10n_latam_use_documents'):
            rec.move_id.l10n_latam_document_type_id = \
                rec.l10n_latam_document_type_id.id,
        return True

    @api.onchange('journal_id', 'partner_id', 'company_id')
    def onchange_journal_partner_company(self):
        res = self._get_available_document_types(
            self.journal_id, self.type, self.partner_id)
        self.l10n_latam_document_type_id = res['document_type']

    @api.depends('journal_id', 'partner_id', 'company_id')
    def _compute_l10n_latam_available_document_types(self):
        """
        This function should only be inherited if you need to add another
        "depends", for eg, if you need to add a depend on "new_field" you
        should add:

        @api.depends('new_field')
        def _get_available_document_types(
                self, journal, invoice_type, partner):
            return super(
                AccountInvoice, self)._get_available_document_types(
                    journal, invoice_type, partner)
        """
        for invoice in self:
            res = invoice._get_available_document_types(
                invoice.journal_id, invoice.type, invoice.partner_id)
            invoice.l10n_latam_available_document_type_ids = res[
                'available_document_types']

    @api.multi
    def write(self, vals):
        """ If someone change the type (for eg from sale order), we update
        the document type"""
        inv_type = vals.get('type')
        # if len(vals) == 1 and vals.get('type'):
        # podrian pasarse otras cosas ademas del type
        if not inv_type:
            return super(AccountInvoice, self).write(vals)

        for rec in self:
            res = rec._get_available_document_types(
                rec.journal_id, inv_type, rec.partner_id)
            vals['l10n_latam_document_type_id'] = res['document_type'].id
            # call write for each invoice
            super(AccountInvoice, rec).write(vals)
        return True

    @api.model
    def _get_available_document_types(
            self, journal, invoice_type, partner):
        """ This function is to be inherited by different localizations and
        MUST return a dictionary with two keys:
        * 'available_document_types': available document types on
        this invoice
        * 'document_type': suggested document type on this invoice
        """
        if not journal.l10n_latam_use_documents:
            return {
                'available_document_types':
                    self.env['l10n_latam.document.type'],
                'document_type':
                    self.env['l10n_latam.document.type'],
            }
        raise UserError(_(
            'Method not implemented by localization of %s') % (
                journal.company_id.country_id.name))

    @api.constrains('type', 'l10n_latam_document_type_id')
    def check_invoice_type_document_type(self):
        for rec in self.filtered('l10n_latam_document_type_id.internal_type'):
            internal_type = rec.l10n_latam_document_type_id.internal_type
            invoice_type = rec.type
            if internal_type in [
                    'debit_note', 'invoice'] and invoice_type in [
                    'out_refund', 'in_refund']:
                raise ValidationError(_(
                    'You can not use a %s document type with a refund '
                    'invoice') % internal_type)
            elif internal_type == 'credit_note' and invoice_type in [
                    'out_invoice', 'in_invoice']:
                raise ValidationError(_(
                    'You can not use a %s document type with a invoice') % (
                    internal_type))

    @api.model
    def _prepare_refund(
            self, invoice, date_invoice=None,
            date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice=date_invoice,
            date=date, description=description, journal_id=journal_id)
        refund_document_type_id = self._context.get(
            'refund_document_type_id', False)
        refund_document_number = self._context.get(
            'refund_document_number', False)
        if refund_document_type_id:
            values['l10n_latam_document_type_id'] = \
                refund_document_type_id
        if refund_document_number:
            values['l10n_latam_document_number'] = refund_document_number
        return values

    @api.multi
    def _check_duplicate_supplier_reference(self):
        """We make reference only unique if you are not using documents.
        Documents already guarantee to not encode twice same vendor bill.
        """
        return super(
            AccountInvoice,
            self.filtered(lambda x: not x.l10n_latam_use_documents))
