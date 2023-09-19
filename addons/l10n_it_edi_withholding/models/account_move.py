# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import namedtuple
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_amount_vat_signed = fields.Monetary(string='VAT', compute='_compute_amount_extended')
    l10n_it_amount_pension_fund_signed = fields.Monetary(string='Pension Fund', compute='_compute_amount_extended')
    l10n_it_amount_withholding_signed = fields.Monetary(string='Withholding', compute='_compute_amount_extended')
    l10n_it_amount_before_withholding_signed = fields.Monetary(string='Total Before Withholding', compute='_compute_amount_extended')

    @api.depends('amount_total_signed')
    def _compute_amount_extended(self):
        for move in self:
            totals = dict(vat=0.0, withholding=0.0, pension_fund=0.0)
            if move.is_invoice(True):
                for line in [line for line in move.line_ids if line.tax_line_id]:
                    totals[line.tax_line_id._l10n_it_get_tax_kind()] -= line.balance
            move.l10n_it_amount_vat_signed = totals['vat']
            move.l10n_it_amount_withholding_signed = totals['withholding']
            move.l10n_it_amount_pension_fund_signed = totals['pension_fund']
            move.l10n_it_amount_before_withholding_signed = move.amount_untaxed_signed + totals['vat'] + totals['pension_fund']

    def _l10n_it_edi_filter_tax_details(self, line, tax_values):
        """Filters tax details to only include the positive amounted lines regarding VAT taxes."""
        repartition_line = tax_values['tax_repartition_line']
        repartition_line_vat = repartition_line.tax_id._l10n_it_filter_kind('vat')
        return repartition_line.factor_percent >= 0 and repartition_line_vat and repartition_line_vat.amount >= 0

    def _l10n_it_edi_get_values(self, pdf_values=None):
        """Add withholding and pension_fund features."""
        template_values = super()._l10n_it_edi_get_values(pdf_values)

        # Withholding tax data
        WithholdingTaxData = namedtuple('TaxData', ['tax', 'tax_amount'])
        withholding_lines = self.line_ids.filtered(lambda x: x.tax_line_id._l10n_it_filter_kind('withholding'))
        withholding_values = [WithholdingTaxData(x.tax_line_id, abs(x.balance)) for x in withholding_lines]

        # Eventually fix the total as it must be computed before applying the Withholding.
        # Withholding amount is negatively signed, so we need to subtract it
        document_total = template_values['document_total']
        document_total -= self.l10n_it_amount_withholding_signed

        # Pension fund tax data, I need the base amount so I have to sum the amounts of the lines with the tax
        PensionFundTaxData = namedtuple('TaxData', ['tax', 'base_amount', 'tax_amount', 'vat_tax', 'withholding_tax'])
        pension_fund_lines = self.line_ids.filtered(lambda line: line.tax_line_id._l10n_it_filter_kind('pension_fund'))
        pension_fund_mapping = {}
        for line in self.line_ids:
            pension_fund_tax = line.tax_ids._l10n_it_filter_kind('pension_fund')
            if pension_fund_tax:
                pension_fund_mapping[pension_fund_tax.id] = (line.tax_ids._l10n_it_filter_kind('vat'), line.tax_ids._l10n_it_filter_kind('withholding'))

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
            # That's also what the "Aliquota" tag seems to imply in the XML.
            vat_tax, withholding_tax = pension_fund_mapping[pension_fund_tax.id]
            pension_fund_values.append(PensionFundTaxData(pension_fund_tax, line.tax_base_amount, abs(line.balance), vat_tax, withholding_tax))

        # Enasarco pension fund must be expressed in the AltriDatiGestionali at the line detail level
        enasarco_values = False
        if enasarco_taxes:
            enasarco_values = {}
            enasarco_details = self._prepare_invoice_aggregated_taxes(
                    filter_tax_values_to_apply=lambda line, tax_values: self.env['account.tax'].browse([tax_values['id']]).l10n_it_pension_fund_type == 'TC07')
            for detail in enasarco_details['tax_details_per_record'].values():
                for subdetail in detail['tax_details'].values():
                    # Withholdings are removed from the total, we have to re-add them
                    document_total += abs(subdetail['tax_amount'])
                    line = subdetail['records'].pop()
                    enasarco_values[line.id] = {
                        'amount': subdetail['tax'].amount,
                        'tax_amount': abs(subdetail['tax_amount']),
                    }

        # Update the template_values that will be read while rendering
        template_values.update({
            'withholding_values': withholding_values,
            'pension_fund_values': pension_fund_values,
            'enasarco_values': enasarco_values,
            'document_total': document_total,
        })
        return template_values

    def _l10n_it_edi_export_taxes_data_check(self):
        """
            Override to also allow pension_fund, withholding taxes.
            Needs not to call super, because super checks for one tax only per line.
        """
        errors = []
        for invoice_line in self.invoice_line_ids.filtered(lambda x: x.display_type == 'product'):
            all_taxes = invoice_line.tax_ids.flatten_taxes_hierarchy()
            vat_taxes, withholding_taxes, pension_fund_taxes = (all_taxes._l10n_it_filter_kind(kind) for kind in
                                                                ('vat', 'withholding', 'pension_fund'))
            if len(vat_taxes.filtered(lambda x: x.amount >= 0)) != 1:
                errors.append(_("Bad tax configuration for line %s, there must be one and only one VAT tax per line", invoice_line.name))
            if len(pension_fund_taxes) > 1 or len(withholding_taxes) > 1:
                errors.append(_("Bad tax configuration for line %s, there must be one Withholding tax and one Pension Fund tax at max.", invoice_line.name))
        return errors

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _l10n_it_edi_search_tax_for_import(self, company, percentage, extra_domain=None, vat_only=True):
        """ In case no withholding_type or pension_fund is specified, exclude taxes that have it.
            It means that we're searching for VAT taxes, especially in the base l10n_it_edi module
        """
        if vat_only:
            extra_domain += [('l10n_it_withholding_type', '=', False), ('l10n_it_pension_fund_type', '=', False)]
        return super()._l10n_it_edi_search_tax_for_import(company, percentage, extra_domain)

    def _l10n_it_edi_get_extra_info(self, company, document_type, body_tree):
        extra_info, message_to_log = super()._l10n_it_edi_get_extra_info(company, document_type, body_tree)

        withholding_elements = body_tree.xpath('.//DatiGeneraliDocumento/DatiRitenuta')
        withholding_taxes = []
        for withholding in (withholding_elements or []):
            tipo_ritenuta = withholding.find("TipoRitenuta")
            reason = withholding.find("CausalePagamento")
            percentage = withholding.find('AliquotaRitenuta')
            withholding_type = tipo_ritenuta.text if tipo_ritenuta is not None else "RT02"
            withholding_reason = reason.text if reason is not None else "A"
            withholding_percentage = -float(percentage.text if percentage is not None else "0.0")
            withholding_tax = self._l10n_it_edi_search_tax_for_import(
                company,
                withholding_percentage,
                [('l10n_it_withholding_type', '=', withholding_type),
                 ('l10n_it_withholding_reason', '=', withholding_reason)],
                vat_only=False)
            if withholding_tax:
                withholding_taxes.append(withholding_tax)
            else:
                message_to_log.append("%s<br/>%s" % (
                    _("Withholding tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                ))
        extra_info["withholding_taxes"] = withholding_taxes

        pension_fund_elements = body_tree.xpath('.//DatiGeneraliDocumento/DatiCassaPrevidenziale')
        pension_fund_taxes = []
        for pension_fund in (pension_fund_elements or []):
            pension_fund_type = pension_fund.find("TipoCassa")
            tax_factor_percent = pension_fund.find("AlCassa")
            vat_tax_factor_percent = pension_fund.find("AliquotaIVA")
            pension_fund_type = pension_fund_type.text if pension_fund_type is not None else ""
            tax_factor_percent = float(tax_factor_percent.text or "0.0")
            vat_tax_factor_percent = float(vat_tax_factor_percent.text or "0.0")
            pension_fund_tax = self._l10n_it_edi_search_tax_for_import(
                company,
                tax_factor_percent,
                [('l10n_it_pension_fund_type', '=', pension_fund_type)],
                vat_only=False)
            if pension_fund_tax:
                pension_fund_taxes.append(pension_fund_tax)
            else:
                message_to_log.append("%s<br/>%s" % (
                    _("Pension Fund tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                ))
        extra_info["pension_fund_taxes"] = pension_fund_taxes

        return extra_info, message_to_log

    def _l10n_it_edi_import_line(self, element, move_line_form, extra_info=None):
        messages_to_log = super()._l10n_it_edi_import_line(element, move_line_form, extra_info)

        for withholding_tax in extra_info.get('withholding_taxes', []):
            withholding_tags = element.xpath("Ritenuta")
            if withholding_tags and withholding_tags[0].text == 'SI':
                move_line_form.tax_ids |= withholding_tax
        for pension_fund_tax in extra_info.get('pension_fund_taxes', []):
            move_line_form.tax_ids |= pension_fund_tax

        if extra_info['simplified']:
            return messages_to_log

        price_subtotal = move_line_form.price_unit
        company = move_line_form.company_id

        # ENASARCO Pension Fund tax (works as a withholding)
        for other_data_element in element.xpath('.//AltriDatiGestionali'):
            data_kind_element = other_data_element.xpath("./TipoDato")
            text_element = other_data_element.xpath("./RiferimentoTesto")
            number_element = other_data_element.xpath("./RiferimentoNumero")
            if not data_kind_element or not text_element or not number_element:
                continue
            data_kind, data_text, number_text = data_kind_element[0].text.lower(), text_element[0].text.lower(), number_element[0].text
            if data_kind != 'cassa-prev' or ('enasarco' not in data_text and 'tc07' not in data_text):
                continue
            enasarco_amount = float(number_text)
            enasarco_percentage = -self.env.company.currency_id.round(enasarco_amount / price_subtotal * 100)
            enasarco_tax = self._l10n_it_edi_search_tax_for_import(
                company,
                enasarco_percentage,
                [('l10n_it_pension_fund_type', '=', 'TC07')],
                vat_only=False)
            if enasarco_tax:
                move_line_form.tax_ids |= enasarco_tax
            else:
                messages_to_log.append("%s<br/>%s" % (
                    _("Enasarco tax not found for line with description '%s'", move_line_form.name),
                    self.env['account.move']._compose_info_message(other_data_element, '.'),
                ))

        return messages_to_log
