# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from functools import partial
from odoo.tools.misc import formatLang


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    l10n_latam_amount_tax = fields.Monetary(
        compute='_compute_l10n_latam_amount_and_taxes'
    )
    l10n_latam_amount_untaxed = fields.Monetary(
        compute='_compute_l10n_latam_amount_and_taxes'
    )
    l10n_latam_tax_line_ids = fields.One2many(
        compute="_compute_l10n_latam_amount_and_taxes",
        comodel_name='account.invoice.tax',
    )
    l10n_latam_default_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        compute='_compute_l10n_latam_documents',
    )
    l10n_latam_available_document_type_ids = fields.Many2many(
        'l10n_latam.document.type',
        compute='_compute_l10n_latam_documents',
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
        readonly=True,
        states={'draft': [('readonly', False)]},
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
                move_name = move_name.split(" ", 1)[-1]
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
            rec.l10n_latam_sequence_id = rec.get_document_type_sequence()

    @api.depends(
        'amount_untaxed', 'amount_tax', 'tax_line_ids',
        'l10n_latam_document_type_id')
    def _compute_l10n_latam_amount_and_taxes(self):
        for invoice in self:
            included_taxes = invoice.l10n_latam_document_type_id and \
                invoice.l10n_latam_document_type_id._filter_taxes_included(invoice.tax_line_ids.mapped('tax_id'))
            if not included_taxes:
                l10n_latam_amount_tax = invoice.amount_tax
                l10n_latam_amount_untaxed = invoice.amount_untaxed
                not_included_invoice_taxes = invoice.tax_line_ids
            else:
                included_invoice_taxes = invoice.tax_line_ids.filtered(
                    lambda x: x.tax_id in included_taxes)
                not_included_invoice_taxes = (
                    invoice.tax_line_ids - included_invoice_taxes)
                l10n_latam_amount_tax = sum(
                    not_included_invoice_taxes.mapped('amount'))
                l10n_latam_amount_untaxed = invoice.amount_untaxed + sum(
                    included_invoice_taxes.mapped('amount'))
            invoice.l10n_latam_amount_tax = l10n_latam_amount_tax
            invoice.l10n_latam_amount_untaxed = l10n_latam_amount_untaxed
            invoice.l10n_latam_tax_line_ids = not_included_invoice_taxes

    def _get_onchange_create(self):
        res = super()._get_onchange_create()
        res.update([('onchange_journal_partner_company', ['l10n_latam_document_type_id'])])
        return res

    @api.multi
    def action_move_create(self):
        for rec in self.filtered(lambda x: x.l10n_latam_use_documents and not x.l10n_latam_document_number):
            rec.l10n_latam_document_number = rec.l10n_latam_sequence_id.next_by_id()
        res = super(AccountInvoice, self).action_move_create()
        for rec in self.filtered('l10n_latam_use_documents'):
            rec.move_id.l10n_latam_document_type_id = rec.l10n_latam_document_type_id.id
        return res

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

    @api.onchange('l10n_latam_default_document_type_id')
    def onchange_journal_partner_company(self):
        self.l10n_latam_document_type_id = self.l10n_latam_default_document_type_id

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if self.type in ['out_refund', 'in_refund']:
            internal_types = ['credit_note']
        else:
            internal_types = ['invoice', 'debit_note']
        return [
            ('internal_type', 'in', internal_types),
            ('country_id', '=', self.company_id.country_id.id),
        ]

    @api.depends('journal_id', 'partner_id', 'company_id')
    def _compute_l10n_latam_documents(self):
        internal_type = self._context.get('internal_type', False)
        for rec in self.filtered(lambda x: x.journal_id and x.l10n_latam_use_documents and x.partner_id):
            document_types = self.env['l10n_latam.document.type'].search(rec._get_l10n_latam_documents_domain())

            # If internal_type is in context we try to search for an specific document. for eg used on debit notes
            document_type = internal_type and document_types.filtered(lambda x: x.internal_type == internal_type) or document_types

            rec.l10n_latam_available_document_type_ids = document_types
            rec.l10n_latam_default_document_type_id = document_type and document_type[0]

    @api.multi
    def write(self, vals):
        """ If someone change the type (for eg from
        sale_order.action_invoice_create), we update the document type"""
        if 'type' not in vals:
            return super(AccountInvoice, self).write(vals)
        res = super(AccountInvoice, rec).write(vals)
        for rec in self.filtered('l10n_latam_use_documents'):
            rec.l10n_latam_document_type_id = rec.l10n_latam_default_document_type_id
        return res

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

    def _amount_by_group(self):
        invoice_with_doc_type = self.filtered('l10n_latam_document_type_id')
        for invoice in invoice_with_doc_type:
            currency = invoice.currency_id or invoice.company_id.currency_id
            fmt = partial(formatLang, invoice.with_context(lang=invoice.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in invoice.l10n_latam_tax_line_ids:
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
        super(AccountInvoice, self - invoice_with_doc_type)._amount_by_group()

    @api.multi
    def unlink(self):
        """ When using documents, on vendor bills the document_number is
        setted manually by the number given from the vendor, the odoo sequence
        is not used. In this case We allow to delete vendor bills with
        document_number/move_name
        """
        self.filtered(lambda x:
            x.type in ['in_refund', 'in_invoice'] and
            x.state in ('draft', 'cancel') and
            x.l10n_latam_use_documents and
            x.move_name
        ).write({'move_name': False})
        return super(AccountInvoice, self).unlink()

    def get_document_type_sequence(self):
        """ Method to be inherited by different localizations.
        """
        self.ensure_one()
        return self.env['ir.sequence']
