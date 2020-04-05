# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_latam_document_type_id_code = fields.Char(related='l10n_latam_document_type_id.code', string='Doc Type')
    partner_id_vat = fields.Char(related='partner_id.vat', string='VAT No')
    l10n_latam_internal_type = fields.Selection(
        related='l10n_latam_document_type_id.internal_type', string='L10n Latam Internal Type')

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (self.journal_id.l10n_latam_use_documents and
                self.journal_id.company_id.country_id == self.env.ref('base.cl')):
            if self.move_type in ['in_invoice', 'in_refund']:
                if self.partner_id.l10n_cl_sii_taxpayer_type == '2':
                    domain += [('code', '=', '71')]
                return domain
            document_type_ids = self.journal_id.l10n_cl_sequence_ids.mapped('l10n_latam_document_type_id').ids
            domain += [('id', 'in', document_type_ids)]
            if self.partner_id.l10n_cl_sii_taxpayer_type == '3':
                domain += [('code', 'in', ['35', '38', '39', '41', '56', '61'])]
        return domain

    @api.constrains('move_type', 'l10n_latam_document_type_id')
    def _check_invoice_type_document_type(self):
        super()._check_invoice_type_document_type()
        for rec in self.filtered(lambda r: r.company_id.country_id == self.env.ref(
                'base.cl') and r.l10n_latam_document_type_id):
            tax_payer_type = rec.partner_id.l10n_cl_sii_taxpayer_type
            latam_document_type_code = rec.l10n_latam_document_type_id.code
            if not tax_payer_type and latam_document_type_code not in ['35', '38', '39', '41']:
                raise ValidationError(_('Tax payer type is mandatory for this type of document. '
                                        'Please set the current tax payer type of this client'))

    def _l10n_cl_get_formatted_sequence(self, number=0):
        return "%s %06d" % (self.l10n_latam_document_type_id.doc_code_prefix, number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.journal_id.l10n_latam_use_documents and self.env.company.country_id == self.env.ref('base.cl'):
            if self.l10n_latam_document_type_id:
                return self._l10n_cl_get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.country_id == self.env.ref('base.cl') and self.l10n_latam_use_documents:
            journals = self.journal_id.l10n_cl_sequence_ids.filtered(lambda s: s.l10n_latam_document_type_id == self.l10n_latam_document_type_id).l10n_cl_journal_ids.ids
            if len(journals) > 1:
                where_string.replace("journal_id = %(journal_ids)s", "journal_id in %(journal_ids)s")
                param['journal_ids'] = journals
            where_string += " AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s "
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
        return where_string, param