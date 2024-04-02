# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from odoo.tools.float_utils import float_repr, float_round

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
                            'Document types for foreign customers must be export type (codes 110, 111 or 112) or you should define the customer as an end consumer and use receipts (codes 39 or 41)'))
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

    def _format_lang_totals(self, value, currency):
        return formatLang(self.env, value, currency_obj=currency)

    def _l10n_cl_get_invoice_totals_for_report(self):
        self.ensure_one()
        include_sii = self._l10n_cl_include_sii()

        base_lines = self.line_ids.filtered(lambda x: x.display_type == 'product')
        tax_lines = self.line_ids.filtered(lambda x: x.display_type == 'tax')

        base_line_vals_list = [x._convert_to_tax_base_line_dict() for x in base_lines]
        if include_sii:
            for vals in base_line_vals_list:
                vals['taxes'] = vals['taxes'].flatten_taxes_hierarchy().filtered(lambda tax: tax.l10n_cl_sii_code != 14)

        tax_line_vals_list = [x._convert_to_tax_line_dict() for x in tax_lines]
        if include_sii:
            tax_line_vals_list = [x for x in tax_line_vals_list if x['tax_repartition_line'].tax_id.l10n_cl_sii_code != 14]

        tax_totals = self.env['account.tax']._prepare_tax_totals(
            base_line_vals_list,
            self.currency_id,
            tax_lines=tax_line_vals_list,
        )

        if include_sii:
            tax_totals['amount_total'] = self.amount_total
            tax_totals['amount_untaxed'] = self.currency_id.round(
                tax_totals['amount_total'] - sum([x['tax_amount'] for x in tax_line_vals_list if 'tax_amount' in x]))
            tax_totals['formatted_amount_total'] = formatLang(self.env, tax_totals['amount_total'], currency_obj=self.currency_id)
            tax_totals['formatted_amount_untaxed'] = formatLang(self.env, tax_totals['amount_untaxed'], currency_obj=self.currency_id)
            if tax_totals['subtotals']:
                tax_totals['subtotals'][0]['formatted_amount'] = tax_totals['formatted_amount_untaxed']

        return tax_totals

    def _l10n_cl_include_sii(self):
        self.ensure_one()
        return self.l10n_latam_document_type_id.code in ['39', '41', '110', '111', '112', '34']

    def _is_manual_document_number(self):
        if self.journal_id.company_id.country_id.code == 'CL':
            return self.journal_id.type == 'purchase' and not self.l10n_latam_document_type_id._is_doc_type_vendor()
        return super()._is_manual_document_number()

    def _l10n_cl_get_amounts(self):
        """
        This method is used to calculate the amount and taxes required in the Chilean localization electronic documents.
        """
        self.ensure_one()
        global_discounts = self.invoice_line_ids.filtered(lambda x: x.price_subtotal < 0)
        export = self.l10n_latam_document_type_id._is_doc_type_export()
        main_currency = self.company_id.currency_id if not export else self.currency_id
        key_main_currency = 'amount_currency' if export else 'balance'
        sign_main_currency = -1 if self.move_type == 'out_invoice' else 1
        currency_round_main_currency = self.currency_id if export else self.company_id.currency_id
        currency_round_other_currency = self.company_id.currency_id if export else self.currency_id
        total_amount_main_currency = currency_round_main_currency.round(self.amount_total) if export \
            else (currency_round_main_currency.round(abs(self.amount_total_signed)))
        other_currency = self.currency_id != self.company_id.currency_id
        values = {
            'main_currency': main_currency,
            'vat_amount': 0,
            'subtotal_amount_taxable': 0,
            'subtotal_amount_exempt': 0, 'total_amount': total_amount_main_currency,
            'main_currency_round': currency_round_main_currency.decimal_places,
            'main_currency_name': self._l10n_cl_normalize_currency_name(
                currency_round_main_currency.name) if export else False
        }
        vat_percent = 0

        if other_currency:
            key_other_currency = 'balance' if export else 'amount_currency'
            values['second_currency'] = {
                'subtotal_amount_taxable': 0,
                'subtotal_amount_exempt': 0,
                'vat_amount': 0,
                'total_amount': currency_round_other_currency.round(abs(self.amount_total_signed)) \
                    if export else currency_round_other_currency.round(self.amount_total),
                'round_currency': currency_round_other_currency.decimal_places,
                'name': self._l10n_cl_normalize_currency_name(currency_round_other_currency.name),
                'rate': round(abs(self.amount_total_signed) / self.amount_total, 4),
            }
        for line in self.line_ids:
            if line.tax_line_id and line.tax_line_id.l10n_cl_sii_code == 14:
                values['vat_amount'] += line[key_main_currency] * sign_main_currency
                if other_currency:
                    values['second_currency']['vat_amount'] += line[key_other_currency] * sign_main_currency # amount_currency behaves as balance
                vat_percent = line.tax_line_id.amount if line.tax_line_id.amount > vat_percent else vat_percent
            if line.display_type == 'product':
                if line.tax_ids.filtered(lambda x: x.l10n_cl_sii_code == 14):
                    values['subtotal_amount_taxable'] += line[key_main_currency] * sign_main_currency
                    if other_currency:
                        values['second_currency']['subtotal_amount_taxable'] += line[key_other_currency] * sign_main_currency
                elif not line.tax_ids:
                    values['subtotal_amount_exempt'] += line[key_main_currency] * sign_main_currency
                    if other_currency:
                        values['second_currency']['subtotal_amount_exempt'] += line[key_other_currency] * sign_main_currency
        values['global_discounts'] = []
        for gd in global_discounts:
            main_value = currency_round_main_currency.round(abs(gd.price_subtotal)) if \
                (not other_currency and not export) or (other_currency and export) else \
                currency_round_main_currency.round(abs(gd.balance))
            second_value = currency_round_other_currency.round(abs(gd.balance)) if other_currency and export else \
                currency_round_other_currency.round(abs(gd.price_subtotal))
            values['global_discounts'].append(
                {
                    'name': gd.name,
                    'global_discount_main_value': main_value,
                    'global_discount_second_value': second_value if second_value != main_value else False,
                    'tax_ids': gd.tax_ids,
                }
            )
        values['vat_percent'] = '%.2f' % vat_percent if vat_percent > 0 else False
        return values

    def _l10n_cl_get_withholdings(self):
        """
        This method calculates the section of withholding taxes, or 'other' taxes for the Chilean electronic invoices.
        These taxes are not VAT taxes in general; they are special taxes (for example, alcohol or sugar-added beverages,
        withholdings for meat processing, fuel, etc.
        The taxes codes used are included here:
        [15, 17, 18, 19, 24, 25, 26, 27, 271]
        http://www.sii.cl/declaraciones_juradas/ddjj_3327_3328/cod_otros_imp_retenc.pdf
        The need of the tax is not just the amount, but the code of the tax, the percentage amount and the amount
        :return:
        """
        self.ensure_one()

        tax = [{'tax_code': line.tax_line_id.l10n_cl_sii_code,
                'tax_name': line.tax_line_id.name,
                'tax_base': abs(sum(self.invoice_line_ids.filtered(
                    lambda x: line.tax_line_id.l10n_cl_sii_code in x.tax_ids.mapped('l10n_cl_sii_code')).mapped(
                    'balance'))),
                'tax_percent': abs(line.tax_line_id.amount),
                'tax_amount_currency': self.currency_id.round(abs(line.amount_currency)),
                'tax_amount': self.currency_id.round(abs(line.balance))} for line in self.line_ids.filtered(
            lambda x: x.tax_group_id.id in [
                self.env.ref('l10n_cl.tax_group_ila').id, self.env.ref('l10n_cl.tax_group_retenciones').id])]
        return tax

    def _float_repr_float_round(self, value, decimal_places):
        return float_repr(float_round(value, decimal_places), decimal_places)
