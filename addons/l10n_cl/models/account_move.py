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
            if self.type in ['in_invoice', 'in_refund']:
                if self.partner_id.l10n_cl_sii_taxpayer_type == '2':
                    domain += [('code', '=', '71')]
                return domain
            document_type_ids = self.journal_id.l10n_cl_sequence_ids.mapped('l10n_latam_document_type_id').ids
            domain += [('id', 'in', document_type_ids)]
            if self.partner_id.l10n_cl_sii_taxpayer_type == '3':
                domain += [('code', 'in', ['35', '38', '39', '41', '56', '61'])]
        return domain

    @api.constrains('type', 'l10n_latam_document_type_id')
    def _check_invoice_type_document_type(self):
        super()._check_invoice_type_document_type()
        for rec in self.filtered(lambda r: r.company_id.country_id == self.env.ref(
                'base.cl') and r.l10n_latam_document_type_id):
            tax_payer_type = rec.partner_id.l10n_cl_sii_taxpayer_type
            latam_document_type_code = rec.l10n_latam_document_type_id.code
            if not tax_payer_type and latam_document_type_code not in ['35', '38', '39', '41']:
                raise ValidationError(_('Tax payer type is mandatory for this type of document. '
                                        'Please set the current tax payer type of this client'))
