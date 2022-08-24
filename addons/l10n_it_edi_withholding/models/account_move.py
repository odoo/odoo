# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import namedtuple
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_amount_vat_signed = fields.Monetary(string='VAT', compute='_compute_amount_extended', readonly=True)
    l10n_it_amount_pension_fund_signed = fields.Monetary(string='Pension Fund', compute='_compute_amount_extended', readonly=True)
    l10n_it_amount_withholding_signed = fields.Monetary(string='Withholding', compute='_compute_amount_extended', readonly=True)
    l10n_it_amount_before_withholding_signed = fields.Monetary(string='Before Withholding', compute='_compute_amount_extended', readonly=True)

    @api.depends('amount_total_signed')
    def _compute_amount_extended(self):
        for move in self:
            totals = dict(vat=0.0, withholding=0.0, pension_fund=0.0)
            for line in [line for line in move.line_ids if move.is_invoice(True) and line.display_type == 'tax' and line.tax_line_id]:
                totals[line.tax_line_id.l10n_it_tax_kind] -= line.balance
            move.l10n_it_amount_vat_signed = totals['vat']
            move.l10n_it_amount_withholding_signed = totals['withholding']
            move.l10n_it_amount_pension_fund_signed = totals['pension_fund']
            move.l10n_it_amount_before_withholding_signed = move.amount_untaxed_signed - totals['vat'] - totals['pension_fund']

    def _l10n_it_edi_fatturapa_select_only_vat_tax(self, taxes):
        return taxes._filter_kind('vat')

    def _l10n_it_edi_prepare_fatturapa_tax_details(self, tax_details, reverse_charge_refund=False):
        tax_details['tax_details'] = {k: v for k, v in tax_details['tax_details'].items() if v['tax'].l10n_it_tax_kind == 'vat'}
        return super()._l10n_it_edi_prepare_fatturapa_tax_details(tax_details, reverse_charge_refund)

    def _l10n_it_edi_filter_fatturapa_tax_details(self, line):
        """Filters tax details to only include the positive amounted lines regarding VAT taxes."""
        repartition_line, tax = line['tax_repartition_line_id'], line['tax_id']
        return repartition_line.factor_percent >= 0 and tax.amount >= 0 and tax.l10n_it_tax_kind

    def _prepare_fatturapa_export_values(self):
        """Add withholding and pension_fund features."""
        template_values = super()._prepare_fatturapa_export_values()

        # Withholding tax data
        WithholdingTaxData = namedtuple('TaxData', ['tax', 'tax_amount'])
        withholding_lines = self.line_ids.filtered(lambda x: x.tax_line_id._filter_kind('withholding'))
        withholding_values = [WithholdingTaxData(x.tax_line_id, abs(x.balance)) for x in withholding_lines]

        # Fix the total eventually as it must be without considering ritenuta
        document_total = template_values['document_total']
        if withholding_values:
            document_total += sum(x.tax_amount for x in withholding_values)

        # Pension fund tax data, I need the base amount so I have to sum the amounts of the lines with the tax
        PensionFundTaxData = namedtuple('TaxData', ['tax', 'base_amount', 'tax_amount', 'vat_tax', 'withholding_tax'])
        pension_fund_lines = self.line_ids.filtered(lambda line: line.tax_line_id._filter_kind('pension_fund'))
        pension_fund_mapping = {}
        for line in self.line_ids:
            pension_fund_tax = line.tax_ids._filter_kind('pension_fund')
            if pension_fund_tax:
                pension_fund_mapping[pension_fund_tax.id] = (line.tax_ids._filter_kind('vat'), line.tax_ids._filter_kind('withholding'))

        # Pension fund taxes in the XML must have a reference to their VAT tax (Aliquota tag)
        pension_fund_values = []
        enasarco_taxes = []
        for line in pension_fund_lines:
            # Enasarco must be treated separately
            if line.tax_line_id.l10n_it_pension_fund_type == 'TC07':
                enasarco_taxes.append(line.tax_line_id)
                continue
            pension_fund_tax = line.tax_line_id
            # Here we are supposing that the same pension_fund is always associated to the same VAT and Withholding taxes
            # That's also what the "Aliquota" tag seems to imply in the XML
            vat_tax, withholding_tax = pension_fund_mapping[pension_fund_tax.id]
            pension_fund_values.append(PensionFundTaxData(pension_fund_tax, line.tax_base_amount, abs(line.balance), vat_tax, withholding_tax))

        # Enasarco pension fund must be expressed in the AltriDatiGestionali at the line detail level
        enasarco_values = False
        if enasarco_taxes:
            enasarco_values = {}
            all_tax_details = self._prepare_edi_tax_details(filter_to_apply=lambda line: line['tax_id'].l10n_it_pension_fund_type == 'TC07')
            for enasarco_tax in enasarco_taxes:
                for detail in all_tax_details['tax_details'][str(enasarco_tax)]['group_tax_details']:
                    # Withholdings are removed from the total, we have to re-add them
                    document_total += abs(detail['tax_amount'])
                    enasarco_values[detail['base_line_id'].id] = {
                        'amount': detail['tax_id'].amount,
                        'tax_amount': detail['tax_amount'],
                    }

        # Update the template_values that will be read while rendering
        template_values.update({
            'withholding_values': withholding_values,
            'pension_fund_values': pension_fund_values,
            'enasarco_values': enasarco_values,
            'document_total': document_total,
        })
        return template_values
