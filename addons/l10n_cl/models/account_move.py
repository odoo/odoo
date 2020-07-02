# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_latam_document_type_id_code = fields.Char(related='l10n_latam_document_type_id.code', string='Doc Type')
    partner_id_vat = fields.Char(related='partner_id.vat', string='VAT No')
    l10n_latam_internal_type = fields.Selection(
        related='l10n_latam_document_type_id.internal_type', string='L10n Latam Internal Type')

    def _get_document_type_sequence(self):
        """ Return the match sequences for the given journal and invoice """
        self.ensure_one()
        if self.journal_id.l10n_latam_use_documents and self.l10n_latam_country_code == 'CL':
            res = self.journal_id.l10n_cl_sequence_ids.filtered(
                lambda x: x.l10n_latam_document_type_id == self.l10n_latam_document_type_id)
            return res
        return super()._get_document_type_sequence()

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (self.journal_id.l10n_latam_use_documents and
                self.journal_id.company_id.country_id == self.env.ref('base.cl')):
            if self.journal_id.type == 'sale':
                document_type_ids = self.journal_id.l10n_cl_sequence_ids.mapped('l10n_latam_document_type_id').ids
            else:  # self.journal_id.type == 'purchase':
                partner_domain = [
                    ('country_id.code', '=', 'CL'),
                    ('internal_type', 'in', ['invoice', 'debit_note', 'credit_note', 'invoice_in'])]
                if not self.partner_id:
                    pass
                elif self.partner_id.l10n_cl_sii_taxpayer_type == '1' and self.partner_id_vat != '60805000-0':
                    partner_domain += [('code', 'not in', ['39', '70', '71', '914', '911'])]
                elif self.partner_id.l10n_cl_sii_taxpayer_type == '1' and self.partner_id_vat == '60805000-0':
                    partner_domain += [('code', 'not in', ['39', '70', '71'])]
                elif self.partner_id.l10n_cl_sii_taxpayer_type == '2':
                    partner_domain += [('code', 'in', ['70', '71', '56', '61'])]
                elif self.partner_id.l10n_cl_sii_taxpayer_type == '3':
                    partner_domain += [('code', 'in', ['35', '38', '39', '41', '56', '61'])]
                elif not self.partner_id.l10n_cl_sii_taxpayer_type or self.partner_id.country_id != self.env.ref(
                        'base.cl') or self.partner_id.l10n_cl_sii_taxpayer_type == '4':
                    partner_domain += [('code', 'in', [])]
                document_type_ids = self.env['l10n_latam.document.type'].search(partner_domain).ids
            domain = expression.AND([domain, [('id', 'in', document_type_ids)]])
        return domain

    def _check_document_types_post(self):
        for rec in self.filtered(
                lambda r: r.company_id.country_id == self.env.ref('base.cl') and
                          r.journal_id.type in ['sale', 'purchase']):
            tax_payer_type = rec.partner_id.l10n_cl_sii_taxpayer_type
            vat = rec.partner_id.vat
            country_id = rec.partner_id.country_id
            latam_document_type_code = rec.l10n_latam_document_type_id.code
            if (not tax_payer_type or not vat) and (country_id == self.env.ref('base.cl') and latam_document_type_code
                                                  and latam_document_type_code not in ['35', '38', '39', '41']):
                raise ValidationError(_('Tax payer type and vat number are mandatory for this type of '
                                        'document. Please set the current tax payer type of this customer'))
            if rec.journal_id.type == 'sale' and rec.journal_id.l10n_latam_use_documents:
                if (tax_payer_type == '4' or country_id != self.env.ref('base.cl')) and \
                        latam_document_type_code not in ['110', '111', '112']:
                    raise ValidationError(_(
                        'Document types for foreign customers must be export type (codes 110, 111 or 112)'))
            if rec.journal_id.type == 'purchase' and rec.journal_id.l10n_latam_use_documents:
                if vat != '60805000-0' and latam_document_type_code == '914':
                    raise ValidationError(_('The DIN document is intended to be used only with RUT 60805000-0'
                                            ' (Tesorería General de La República)'))
                if not tax_payer_type or not vat:
                    if country_id == self.env.ref('base.cl') and latam_document_type_code not in [
                            '35', '38', '39', '41']:
                        raise ValidationError(_('Tax payer type and vat number are mandatory for this type of '
                                                'document. Please set the current tax payer type of this supplier'))
                if tax_payer_type == '2' and latam_document_type_code not in ['70', '71', '56', '61']:
                    raise ValidationError(_('The tax payer type of this supplier is incorrect for the selected type'
                                            ' of document.'))
                if tax_payer_type in ['1', '3']:
                    if latam_document_type_code in ['70', '71']:
                        raise ValidationError(_('The tax payer type of this supplier is not entitled to deliver '
                                                'fees documents'))
                    if latam_document_type_code in ['110', '111', '112']:
                        raise ValidationError(_('The tax payer type of this supplier is not entitled to deliver '
                                                'imports documents'))
                if tax_payer_type == '4' or country_id != self.env.ref('base.cl'):
                    raise ValidationError(_('You need a journal without the use of documents for foreign '
                                            'suppliers'))
            if rec.journal_id.type == 'purchase' and not rec.journal_id.l10n_latam_use_documents:
                if tax_payer_type != '4':
                    raise ValidationError(_('This supplier should be defined as foreigner tax payer type and '
                                            'the country should be different from Chile to register purchases.'))

    @api.onchange('journal_id')
    def _onchange_journal(self):
        self.l10n_latam_document_type_id = False

    def post(self):
        self._check_document_types_post()
        super().post()
