# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.osv import expression

SII_VAT = '60805000-0'


class AccountMove(models.Model):
    _inherit = "account.move"

    partner_id_vat = fields.Char(related='partner_id.vat', string='VAT No')
    l10n_latam_internal_type = fields.Selection(
        related='l10n_latam_document_type_id.internal_type', string='L10n Latam Internal Type')

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if self.journal_id.company_id.account_fiscal_country_id != self.env.ref('base.cl') or not \
                self.journal_id.l10n_latam_use_documents:
            return super()._get_l10n_latam_documents_domain()
        if self.journal_id.type == 'sale':
            domain = [('country_id.code', '=', 'CL')]
            if self.move_type in ['in_invoice', 'out_invoice']:
                domain += [('internal_type', 'in', ['invoice', 'debit_note', 'invoice_in'])]
            elif self.move_type in ['in_refund', 'out_refund']:
                domain += [('internal_type', '=', 'credit_note')]
            if self.company_id.partner_id.l10n_cl_sii_taxpayer_type == '1':
                domain += [('code', '!=', '71')]  # Companies with VAT Affected doesn't have "Boleta de honorarios Electrónica"
            return domain
        if self.move_type == 'in_refund':
            internal_types_domain = ('internal_type', '=', 'credit_note')
        else:
            internal_types_domain = ('internal_type', 'in', ['invoice', 'debit_note', 'invoice_in'])
        domain = [
            ('country_id.code', '=', 'CL'),
            internal_types_domain,
        ]
        if self.partner_id.l10n_cl_sii_taxpayer_type == '1' and self.partner_id_vat != '60805000-0':
            domain += [('code', 'not in', ['39', '70', '71', '914', '911'])]
        elif self.partner_id.l10n_cl_sii_taxpayer_type == '1' and self.partner_id_vat == '60805000-0':
            domain += [('code', 'not in', ['39', '70', '71'])]
        elif self.partner_id.l10n_cl_sii_taxpayer_type == '2':
            domain += [('code', 'in', ['70', '71', '56', '61'])]
        elif self.partner_id.l10n_cl_sii_taxpayer_type == '3':
            domain += [('code', 'in', ['35', '38', '39', '41', '56', '61'])]
        elif self.partner_id.country_id.code != 'CL' or self.partner_id.l10n_cl_sii_taxpayer_type == '4':
            domain += [('code', '=', '46')]
        else:
            domain += [('code', 'in', [])]
        return domain

    def _check_document_types_post(self):
        for rec in self.filtered(
                lambda r: r.company_id.account_fiscal_country_id.code == "CL" and
                          r.journal_id.type in ['sale', 'purchase']):
            tax_payer_type = rec.partner_id.l10n_cl_sii_taxpayer_type
            vat = rec.partner_id.vat
            country_id = rec.partner_id.country_id
            latam_document_type_code = rec.l10n_latam_document_type_id.code
            if (not tax_payer_type or not vat) and (country_id.code == "CL" and latam_document_type_code
                                                  and latam_document_type_code not in ['35', '38', '39', '41']):
                raise ValidationError(_('Tax payer type and vat number are mandatory for this type of '
                                        'document. Please set the current tax payer type of this customer'))
            if rec.journal_id.type == 'sale' and rec.journal_id.l10n_latam_use_documents:
                if country_id.code != "CL":
                    if not ((tax_payer_type == '4' and latam_document_type_code in ['110', '111', '112']) or (
                            tax_payer_type == '3' and latam_document_type_code in ['39', '41', '61', '56'])):
                        raise ValidationError(_(
                            'Document types for foreign customers must be export type (codes 110, 111 or 112) or you \
                            should define the customer as an end consumer and use receipts (codes 39 or 41)'))
            if rec.journal_id.type == 'purchase' and rec.journal_id.l10n_latam_use_documents:
                if vat != SII_VAT and latam_document_type_code == '914':
                    raise ValidationError(_('The DIN document is intended to be used only with RUT 60805000-0'
                                            ' (Tesorería General de La República)'))
                if not tax_payer_type or not vat:
                    if country_id.code == "CL" and latam_document_type_code not in [
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
                if (tax_payer_type == '4' or country_id.code != "CL") and latam_document_type_code != '46':
                    raise ValidationError(_('You need a journal without the use of documents for foreign '
                                            'suppliers'))

    @api.onchange('journal_id')
    def _l10n_cl_onchange_journal(self):
        if self.company_id.country_id.code == 'CL':
            self.l10n_latam_document_type_id = False

    def _post(self, soft=True):
        self._check_document_types_post()
        return super()._post(soft)

    def _l10n_cl_get_formatted_sequence(self, number=0):
        return '%s %06d' % (self.l10n_latam_document_type_id.doc_code_prefix, number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 6 padding number """
        if self.journal_id.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == "CL":
            if self.l10n_latam_document_type_id:
                return self._l10n_cl_get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == "CL" and self.l10n_latam_use_documents:
            where_string = where_string.replace('journal_id = %(journal_id)s AND', '')
            where_string += ' AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s AND ' \
                            'company_id = %(company_id)s AND move_type IN %(move_type)s'

            param['company_id'] = self.company_id.id or False
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
            param['move_type'] = (('in_invoice', 'in_refund') if
                  self.l10n_latam_document_type_id._is_doc_type_vendor() else ('out_invoice', 'out_refund'))
        return where_string, param

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == 'CL':
            return 'l10n_cl.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_cl_get_invoice_totals_for_report(self):
        self.ensure_one()
        tax_ids_filter = tax_line_id_filter = None
        include_sii = self._l10n_cl_include_sii()

        if include_sii:
            tax_ids_filter = (lambda aml, tax: bool(tax.l10n_cl_sii_code != 14))
            tax_line_id_filter = (lambda aml, tax: bool(tax.l10n_cl_sii_code != 14))

        tax_lines_data = self._prepare_tax_lines_data_for_totals_from_invoice(
            tax_ids_filter=tax_ids_filter, tax_line_id_filter=tax_line_id_filter)

        if include_sii:
            amount_untaxed = self.currency_id.round(
                self.amount_total - sum([x['tax_amount'] for x in tax_lines_data if 'tax_amount' in x]))
        else:
            amount_untaxed = self.amount_untaxed
        return self._get_tax_totals(self.partner_id, tax_lines_data, self.amount_total, amount_untaxed, self.currency_id)

    def _l10n_cl_include_sii(self):
        self.ensure_one()
        return self.l10n_latam_document_type_id.code in ['39', '41', '110', '111', '112', '34']

    def _is_manual_document_number(self):
        if self.journal_id.company_id.country_id.code == 'CL':
            return self.journal_id.type == 'purchase' and not self.l10n_latam_document_type_id._is_doc_type_vendor()
        return super()._is_manual_document_number()
