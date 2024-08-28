# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from markupsafe import Markup
from odoo import _, api, fields, models

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
            totals = {None: 0.0, 'vat':0.0, 'withholding': 0.0, 'pension_fund': 0.0}
            if move.is_invoice(True):
                for line in [line for line in move.line_ids if line.tax_line_id]:
                    kind = line.tax_line_id._l10n_it_get_tax_kind()
                    totals[kind] -= line.balance
            move.l10n_it_amount_vat_signed = totals['vat']
            move.l10n_it_amount_withholding_signed = totals['withholding']
            move.l10n_it_amount_pension_fund_signed = totals['pension_fund']
            move.l10n_it_amount_before_withholding_signed = move.amount_untaxed_signed + totals['vat'] + totals['pension_fund']

    @api.model
    def _l10n_it_edi_grouping_function_base_lines(self, base_line, tax_data):
        # EXTENDS 'l10n_it_edi'
        grouping_key = super()._l10n_it_edi_grouping_function_base_lines(base_line, tax_data)
        tax = tax_data['tax']
        is_withholding = tax._l10n_it_filter_kind('withholding')
        is_pension_fund = tax._l10n_it_filter_kind('pension_fund')
        grouping_key['skip'] = grouping_key['skip'] or is_withholding or is_pension_fund
        return grouping_key

    @api.model
    def _l10n_it_edi_grouping_function_tax_lines(self, base_line, tax_data):
        # EXTENDS 'l10n_it_edi'
        grouping_key = super()._l10n_it_edi_grouping_function_tax_lines(base_line, tax_data)
        tax = tax_data['tax']
        is_withholding = tax._l10n_it_filter_kind('withholding')
        is_pension_fund = tax._l10n_it_filter_kind('pension_fund')
        grouping_key['skip'] = grouping_key['skip'] or is_withholding or is_pension_fund
        return grouping_key

    @api.model
    def _l10n_it_edi_grouping_function_total(self, base_line, tax_data):
        # EXTENDS 'l10n_it_edi'
        skip = not super()._l10n_it_edi_grouping_function_total(base_line, tax_data)
        tax = tax_data['tax']
        is_withholding = tax._l10n_it_filter_kind('withholding')
        is_pension_fund = tax._l10n_it_filter_kind('pension_fund')
        return not (skip or is_withholding or is_pension_fund)

    def _l10n_it_edi_get_values(self, pdf_values=None):
        # EXTENDS 'l10n_it_edi'
        template_values = super()._l10n_it_edi_get_values(pdf_values)
        base_lines = template_values['base_lines']

        # Withholding tax amounts.

        def grouping_function_withholding(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'tax_amount_field': -23.0 if tax.amount == -11.5 else tax.amount,
                'l10n_it_withholding_type': tax.l10n_it_withholding_type,
                'l10n_it_withholding_reason': tax.l10n_it_withholding_reason,
                'skip': not tax._l10n_it_filter_kind('withholding'),
            }

        AccountTax = self.env['account.tax']
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_withholding)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        withholding_values = []
        for values in values_per_grouping_key.values():
            grouping_key = values['grouping_key']
            if not grouping_key or grouping_key['skip']:
                continue

            withholding_values.append({
                'tipo_ritenuta': grouping_key['l10n_it_withholding_type'],
                'importo_ritenuta': -values['tax_amount'],
                'aliquota_ritenuta': -grouping_key['tax_amount_field'],
                'causale_pagamento': grouping_key['l10n_it_withholding_reason'],
            })

        # Pension fund.

        def grouping_function_pension_funds(base_line, tax_data):
            tax = tax_data['tax']
            flatten_taxes = base_line['tax_ids'].flatten_taxes_hierarchy()
            vat_tax = flatten_taxes.filtered(lambda t: t._l10n_it_filter_kind('vat') and t.amount >= 0)[:1]
            withholding_tax = flatten_taxes.filtered(lambda t: t._l10n_it_filter_kind('withholding') and t.sequence > tax.sequence)[:1]
            return {
                'tax_amount_field': -23.0 if tax.amount == -11.5 else tax.amount,
                'vat_tax_amount_field': -23.0 if vat_tax.amount == -11.5 else vat_tax.amount,
                'has_withholding': bool(withholding_tax),
                'l10n_it_pension_fund_type': tax.l10n_it_pension_fund_type,
                'l10n_it_exempt_reason': vat_tax.l10n_it_exempt_reason,
                'description': vat_tax.description,
                'skip': not tax._l10n_it_filter_kind('pension_fund') or tax.l10n_it_pension_fund_type == 'TC07',
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_pension_funds)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        pension_fund_values = []
        for values in values_per_grouping_key.values():
            grouping_key = values['grouping_key']
            if not grouping_key or grouping_key['skip']:
                continue

            pension_fund_values.append({
                'tipo_cassa': grouping_key['l10n_it_pension_fund_type'],
                'al_cassa': grouping_key['tax_amount_field'],
                'importo_contributo_cassa': values['tax_amount'],
                'imponibile_cassa': values['base_amount'],
                'aliquota_iva': grouping_key['vat_tax_amount_field'],
                'ritenuta': 'SI' if grouping_key['has_withholding'] else None,
                'natura': grouping_key['l10n_it_exempt_reason'],
                'riferimento_amministrazione': grouping_key['description'],
            })

        # Enasarco values.
        for base_line in base_lines:
            taxes_data = base_line['tax_details']['taxes_data']
            it_values = base_line['it_values']
            other_data_list = it_values['altri_dati_gestionali_list']

            # Withholding
            if any(x for x in taxes_data if x['tax']._l10n_it_filter_kind('withholding')):
                it_values['ritenuta'] = 'SI'

            # Enasarco
            enasarco_taxes_data = [x for x in taxes_data if x['tax'].l10n_it_pension_fund_type == 'TC07']
            for enasarco_tax_data in enasarco_taxes_data:
                percentage_str = round(abs(enasarco_tax_data['tax'].amount), 1)
                other_data_list.append({
                    'tipo_dato': 'CASSA-PREV',
                    'riferimento_testo': f'TC07 - ENASARCO ({percentage_str}%)',
                    'riferimento_numero': -enasarco_tax_data['tax_amount'],
                    'riferimento_data': None,
                })

            # Pension Fund
            if not enasarco_taxes_data:
                pension_fund_taxes_data = [x for x in taxes_data if x['tax']._l10n_it_filter_kind('pension_fund')]
                for pension_fund_tax_data in pension_fund_taxes_data:
                    pension_type = pension_fund_tax_data['tax'].l10n_it_pension_fund_type
                    percentage_str = round(abs(pension_fund_tax_data['tax'].amount))
                    other_data_list.append({
                        'tipo_dato': 'AswCassPre',
                        'riferimento_testo': f'{pension_type} ({percentage_str}%)',
                        'riferimento_numero': None,
                        'riferimento_data': None,
                    })

        # Update the template_values that will be read while rendering
        template_values.update({
            'withholding_values': withholding_values,
            'pension_fund_values': pension_fund_values,
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
                ([('l10n_it_pension_fund_type', '=', pension_fund_type)]
                 + type_tax_use_domain),
                vat_only=False)
            if pension_fund_tax:
                pension_fund_taxes.append(pension_fund_tax)
            else:
                message_to_log.append(Markup("%s<br/>%s") % (
                    _("Pension Fund tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                ))
        extra_info["pension_fund_taxes"] = pension_fund_taxes

        return extra_info, message_to_log

    def _l10n_it_edi_import_line(self, element, move_line_form, extra_info=None):
        messages_to_log = super()._l10n_it_edi_import_line(element, move_line_form, extra_info)

        type_tax_use_domain = extra_info['type_tax_use_domain']

        for withholding_tax in extra_info.get('withholding_taxes', []):
            withholding_tags = element.xpath("Ritenuta")
            if withholding_tags and withholding_tags[0].text == 'SI':
                move_line_form.tax_ids |= withholding_tax

        if extra_info['simplified']:
            return messages_to_log

        price_subtotal = move_line_form.price_unit
        company = move_line_form.company_id

        # Pension Funds applied on line level and ENASARCO Pension Fund tax (works as a withholding)
        for other_data_element in element.xpath('.//AltriDatiGestionali'):
            data_kind_element = other_data_element.xpath("./TipoDato")
            text_element = other_data_element.xpath("./RiferimentoTesto")
            if not data_kind_element or not text_element:
                continue
            data_kind, data_text = data_kind_element[0].text.lower(), text_element[0].text.lower()
            if data_kind == 'cassa-prev' and ('enasarco' in data_text or 'tc07' in data_text):
                number_element = other_data_element.xpath("./RiferimentoNumero")
                if not number_element:
                    continue
                enasarco_amount = float(number_element[0].text)
                enasarco_percentage = -self.env.company.currency_id.round(enasarco_amount / price_subtotal * 100)
                enasarco_tax = self._l10n_it_edi_search_tax_for_import(
                    company,
                    enasarco_percentage,
                    [('l10n_it_pension_fund_type', '=', 'TC07')] + type_tax_use_domain,
                    vat_only=False)
                if enasarco_tax:
                    move_line_form.tax_ids |= enasarco_tax
                else:
                    messages_to_log.append(Markup("%s<br/>%s") % (
                        _("Enasarco tax not found for line with description '%s'", move_line_form.name),
                        self.env['account.move']._compose_info_message(other_data_element, '.'),
                    ))
            elif data_kind == 'aswcasspre' and 'tc' in data_text:
                for pension_fund_tax in extra_info.get('pension_fund_taxes', []):
                    if pension_fund_tax.l10n_it_pension_fund_type.lower() in data_text:
                        move_line_form.tax_ids |= pension_fund_tax

        return messages_to_log
