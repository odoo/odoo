# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from collections import namedtuple

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.addons.l10n_it_edi.models.account_move import get_float
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_amount_vat_signed = fields.Monetary(string='VAT', compute='_compute_amount_extended', currency_field='company_currency_id')
    l10n_it_amount_pension_fund_signed = fields.Monetary(string='Pension Fund', compute='_compute_amount_extended', currency_field='company_currency_id')
    l10n_it_amount_withholding_signed = fields.Monetary(string='Withholding', compute='_compute_amount_extended', currency_field='company_currency_id')
    l10n_it_amount_before_withholding_signed = fields.Monetary(string='Total Before Withholding', compute='_compute_amount_extended', currency_field='company_currency_id')

    @api.depends('amount_total_signed')
    def _compute_amount_extended(self):
        for move in self:
            totals = {None: 0.0, 'vat': 0.0, 'withholding': 0.0, 'pension_fund': 0.0}
            if move.is_invoice(True):
                for line in [line for line in move.line_ids if line.tax_line_id]:
                    tax = line.tax_line_id
                    if tax.l10n_it_pension_fund_type:
                        totals['pension_fund'] -= line.balance
                    elif tax.l10n_it_withholding_type:
                        totals['withholding'] -= line.balance
                    else:
                        totals['vat'] -= line.balance
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

        # Pension fund must be expressed in the AltriDatiGestionali at the line detail level
        pension_fund_by_line_id = {}
        if pension_fund_values:
            base_lines = [
                line._convert_to_tax_base_line_dict()
                for line in self.line_ids.filtered(lambda line: line.display_type == 'product')
            ]
            for base_line in base_lines:
                for pension_fund in pension_fund_values:
                    if pension_fund.tax.id in base_line['taxes'].ids:
                        pension_fund_by_line_id[base_line['record'].id] = pension_fund.tax

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
            'pension_fund_by_line_id': pension_fund_by_line_id,
            'enasarco_values': enasarco_values,
            'document_total': document_total,
        })
        return template_values

    def _l10n_it_edi_export_taxes_check(self):
        # EXTENDS l10n_it_edi
        errors = super()._l10n_it_edi_export_taxes_check()
        for kind_code, kind_desc in (('withholding', _('Withholding')), ('pension_fund', _('Pension Fund'))):
            errors.update(self._l10n_it_edi_check_lines_for_tax_kind(kind_code, kind_desc, min_len=0))
        return errors

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _l10n_it_edi_search_tax_for_import(self, company, percentage, extra_domain=None, vat_only=True, l10n_it_exempt_reason=False):
        """ In case no withholding_type or pension_fund is specified, exclude taxes that have it.
            It means that we're searching for VAT taxes, especially in the base l10n_it_edi module
        """
        if vat_only:
            extra_domain = (extra_domain or []) + [('l10n_it_withholding_type', '=', False), ('l10n_it_pension_fund_type', '=', False)]
        return super()._l10n_it_edi_search_tax_for_import(company, percentage, extra_domain=extra_domain, l10n_it_exempt_reason=l10n_it_exempt_reason)

    def _l10n_it_edi_get_extra_info(self, company, document_type, body_tree, incoming=True):
        extra_info, message_to_log = super()._l10n_it_edi_get_extra_info(company, document_type, body_tree, incoming=incoming)

        type_tax_use_domain = extra_info['type_tax_use_domain']

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
                ([('l10n_it_withholding_type', '=', withholding_type),
                  ('l10n_it_withholding_reason', '=', withholding_reason)]
                 + type_tax_use_domain),
                vat_only=False)
            if withholding_tax:
                withholding_taxes.append(withholding_tax)
            else:
                message_to_log.append(Markup("%s<br/>%s") % (
                    _("Withholding tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                ))
        extra_info["withholding_taxes"] = withholding_taxes

        pension_fund_elements = body_tree.xpath('.//DatiGeneraliDocumento/DatiCassaPrevidenziale')
        pension_fund_taxes = {}
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
                ([('l10n_it_pension_fund_type', '=', pension_fund_type)]
                 + type_tax_use_domain),
                vat_only=False)
            if pension_fund_tax:
                pension_fund_taxes[vat_tax_factor_percent] = pension_fund_tax
            else:
                message_to_log.append(Markup("%s<br/>%s") % (
                    _("Pension Fund tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                ))
        extra_info["pension_fund_taxes"] = pension_fund_taxes

        # If the AssoSoftware specs are used on the invoice, then only apply
        # the Pension Fund tax to the lines that show an AswCassPre
        # additional tag (AltriDatiGestionali)
        selector = ".//AltriDatiGestionali/TipoDato[contains(text(), 'AswCassPre')]"
        if self.get_tag(body_tree, selector) is not None:
            extra_info["pension_fund_assosoftware_tags"] = True

        return extra_info, message_to_log

    def get_tag(self, element, selector):
        if element is None:
            return None
        sub = element.xpath(selector)
        if sub is None or len(sub) == 0:
            return None
        return sub[0]

    def _get_pension_fund_tax_for_line(self, element, extra_info):
        """ Apply the pension fund on all lines that have the related AliquotaIVA
            If there are AssoSoftware specific AltriDatiGestionale 'AswCassPre'
            tags that specify which lines have pension funds, only apply to them.
        """
        pension_fund_map = extra_info.get('pension_fund_taxes', {})
        tax_rate_tag = self.get_tag(element, './/AliquotaIVA')
        if tax_rate_tag is None:
            return None

        tax_rate = float(tax_rate_tag.text)
        pension_fund_tax = pension_fund_map.get(tax_rate)
        if not pension_fund_tax:
            return None

        if not extra_info.get('pension_fund_assosoftware_tags'):
            return pension_fund_tax

        selector = ".//AltriDatiGestionali[TipoDato[contains(text(),'AswCassPre')]]/RiferimentoTesto"
        reference_tag = self.get_tag(element, selector)
        if reference_tag is None:
            return None

        if match := re.match(r"(?P<kind>TC\d{2}) \((?P<tax_rate>\d+)%\)", reference_tag.text):
            rate = float(match.group("tax_rate"))
            match_kind = (match.group("kind") == pension_fund_tax.l10n_it_pension_fund_type)
            match_rate = (float_compare(rate, pension_fund_tax.amount, precision_digits=2) == 0)
            if match_kind and match_rate:
                return pension_fund_tax

        return None

    def _l10n_it_edi_import_line(self, element, move_line_form, extra_info=None):
        extra_info = extra_info or {}
        messages_to_log = super()._l10n_it_edi_import_line(element, move_line_form, extra_info)

        type_tax_use_domain = extra_info['type_tax_use_domain']

        # Eventually apply withholding
        for withholding_tax in extra_info.get('withholding_taxes', []):
            withholding_tags = element.xpath("Ritenuta")
            if withholding_tags and withholding_tags[0].text == 'SI':
                move_line_form.tax_ids |= withholding_tax

        if extra_info['simplified']:
            return messages_to_log

        price_subtotal = move_line_form.price_unit
        company = move_line_form.company_id

        # Eventually apply pension_fund
        if pension_fund_tax := self._get_pension_fund_tax_for_line(element, extra_info):
            move_line_form.tax_ids |= pension_fund_tax

        # Eventually apply ENASARCO
        for other_data_element in element.xpath('.//AltriDatiGestionali'):
            data_kind_element = other_data_element.xpath("./TipoDato")
            text_element = other_data_element.xpath("./RiferimentoTesto")
            if not data_kind_element or not text_element:
                continue
            data_kind, data_text = data_kind_element[0].text.lower(), text_element[0].text.lower()
            if data_kind == 'cassa-prev' and ('enasarco' in data_text or 'tc07' in data_text):
                number_element = other_data_element.xpath("./RiferimentoNumero")
                if not number_element or not price_subtotal:
                    continue
                enasarco_amount = float(number_element[0].text)
                enasarco_percentage = -self.env.company.currency_id.round(enasarco_amount / price_subtotal * 100)
                domain = [('l10n_it_pension_fund_type', '=', 'TC07')] + type_tax_use_domain
                if enasarco_tax := self._l10n_it_edi_search_tax_for_import(company, enasarco_percentage, domain, vat_only=False):
                    move_line_form.tax_ids |= enasarco_tax
                else:
                    messages_to_log.append(Markup("%s<br/>%s") % (
                        _("Enasarco tax not found for line with description '%s'", move_line_form.name),
                        self.env['account.move']._compose_info_message(other_data_element, '.'),
                    ))

        return messages_to_log

    def _l10n_it_edi_import_invoice(self, invoice, data, is_new):
        """ Handle the case where ENASARCO pension fund contribution should be applied on the invoice globally.
        In this case, there should only be one element with ENASARCO and these conditions should be fulfilled:
         - AliquotaIVA is defined
         - PrezzoUnitario == 0.0
         - a corresponding DatiRiepilogo with the same AliquotaIVA and a ImponibileImporto
        """
        res = super()._l10n_it_edi_import_invoice(invoice=invoice, data=data, is_new=is_new)
        if not res:
            return
        self = res
        tree = data['xml_tree']
        global_enasarco_lines = []
        for additional_data_element in tree.xpath('//AltriDatiGestionali'):
            data_kind = additional_data_element.xpath('./TipoDato')[0].text.lower()
            if data_kind == 'cassa-prev':
                data_text = additional_data_element.xpath('./RiferimentoTesto')[0].text.lower()
                if 'enasarco' in data_text or 'tc07' in data_text:
                    parent_element = additional_data_element.xpath('..')[0]
                    price_unit = get_float(parent_element, './PrezzoUnitario')
                    if price_unit == 0.0:
                        global_enasarco_lines.append(parent_element)

        if len(global_enasarco_lines) == 1:
            parent_element = global_enasarco_lines[0]
            enasarco_amount = get_float(parent_element, './AltriDatiGestionali/RiferimentoNumero')
            price_unit = get_float(parent_element, './PrezzoUnitario')
            base_amount = self._get_l10_it_edi_get_taxable_amount_from_summary_data(parent_element.xpath('..')[0])
            enasarco_percentage = -self.currency_id.round(enasarco_amount / base_amount * 100) if base_amount else 0.0
            type_tax_use_domain = [('type_tax_use', '=', 'purchase' if self.is_outbound(include_receipts=True) else 'sale')]
            domain = [('l10n_it_pension_fund_type', '=', 'TC07')] + type_tax_use_domain
            if enasarco_tax := self._l10n_it_edi_search_tax_for_import(self.company_id, enasarco_percentage, domain, vat_only=False):
                to_remove_index = int(get_float(parent_element, './NumeroLinea')) - 1
                self.invoice_line_ids[to_remove_index].unlink()
                self.invoice_line_ids.tax_ids |= enasarco_tax

        return self

    def _get_l10_it_edi_get_taxable_amount_from_summary_data(self, element):
        taxable_amount = 0.0
        for summary_data_element in element.xpath('.//DatiRiepilogo'):
            taxable_amount += get_float(summary_data_element, './/ImponibileImporto')
        return taxable_amount
