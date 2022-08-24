# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
import logging


_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_it_edi_check_taxes_configuration(self, invoice):
        """
            Override to also allow pension_fund, withholding taxes.
            Needs not to call super, because super checks for one tax only per line.
        """
        errors = []
        for invoice_line in invoice.invoice_line_ids.filtered(lambda x: not x.display_type):
            vat_taxes, withholding_taxes, pension_fund_taxes = [invoice_line.tax_ids._filter_kind(kind) for kind in ('vat', 'withholding', 'pension_fund')]
            if not invoice_line.display_type:
                if len(vat_taxes) != 1:
                    errors.append(_("Bad tax configuration for line %s, there must be one and only one VAT tax per line", invoice_line.name))
                if len(pension_fund_taxes) > 1 or len(withholding_taxes) > 1:
                    errors.append(_("Bad tax configuration for line %s, there must be one Withholding tax and one Pension Fund tax at max.", invoice_line.name))
        return errors

    def _l10n_it_edi_get_extra_info(self, company, document_type, body_tree, extra_info):
        message_to_log = super()._l10n_it_edi_get_extra_info(company, document_type, body_tree, extra_info)

        withholding_elements = body_tree.xpath('.//DatiGeneraliDocumento/DatiRitenuta')
        withholding_taxes = []
        for withholding in (withholding_elements or []):
            tipo_ritenuta = withholding.find("TipoRitenuta")
            reason = withholding.find("CausalePagamento")
            percentage = withholding.find('AliquotaRitenuta')
            withholding_type = tipo_ritenuta.text if tipo_ritenuta is not None else "RT02"
            withholding_reason = reason.text if reason is not None else "A"
            withholding_percentage = -float(percentage.text if percentage is not None else "0.0")
            withholding_tax = self._l10n_it_edi_import_search_tax(company, withholding_percentage,
                [('l10n_it_withholding_type', '=', withholding_type),
                 ('l10n_it_withholding_reason', '=', withholding_reason)])
            if withholding_tax:
                withholding_taxes.append(withholding_tax)
            else:
                message_to_log.append("%s<br/>%s",
                    _("Withholding tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                )
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
            pension_fund_tax = self._l10n_it_edi_import_search_tax(company, tax_factor_percent,
                [('l10n_it_pension_fund_type', '=', pension_fund_type)])
            if pension_fund_tax:
                pension_fund_taxes.append(pension_fund_tax)
            else:
                message_to_log.append("%s<br/>%s",
                    _("Pension Fund tax not found"),
                    self.env['account.move']._compose_info_message(body_tree, '.'),
                )
        extra_info["pension_fund_taxes"] = pension_fund_taxes

        return message_to_log

    def _import_fattura_pa_line(self, element, invoice_line_form, extra_info):
        messages_to_log = super()._import_fattura_pa_line(element, invoice_line_form, extra_info)
        for withholding_tax in extra_info.get('withholding_taxes', []):
            withholding_tags = element.xpath("Ritenuta")
            if withholding_tags and withholding_tags[0].text == 'SI':
                invoice_line_form.tax_ids.add(withholding_tax)
        for pension_fund_tax in extra_info.get('pension_fund_taxes', []):
            invoice_line_form.tax_ids.add(pension_fund_tax)
        return messages_to_log
