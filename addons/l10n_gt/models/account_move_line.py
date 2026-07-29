# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

VAT_WITHHOLDING_TYPE_TO_TAX = {
    'special_taxpayer': 'tax_vat_withholding_15',
    'public_sector': 'tax_vat_withholding_25',
    'exporter_29_89': 'tax_vat_withholding_65',
}


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_gt_get_withholding_taxes(self):
        """ Return the ISR and VAT withholding taxes the SAT rules make applicable on this line.

        The party issuing the document withholds from the other one, so on a vendor bill the agent
        is the company while on a customer invoice it is the partner.
        """
        self.ensure_one()
        move = self.move_id
        if move.is_purchase_document(include_receipts=True):
            agent, subject, type_tax_use = move.company_id, move.commercial_partner_id, 'purchase'
        elif move.is_sale_document(include_receipts=True):
            agent, subject, type_tax_use = move.commercial_partner_id, move.company_id, 'sale'
        else:
            return self.env['account.tax']

        tax_id_prefixes = []
        if agent.l10n_gt_isr_withholding_agent and not subject.l10n_gt_isr_withholding_agent:
            tax_id_prefixes.append('tax_isr_withholding')
        if self._l10n_gt_is_vat_withholding_due(agent, subject):
            tax_id_prefixes.append(self._l10n_gt_get_vat_withholding_tax_prefix(agent, subject))

        chart_template = self.env['account.chart.template'].with_company(move.company_id)
        taxes = self.env['account.tax']
        for prefix in filter(None, tax_id_prefixes):
            if tax := chart_template.ref(f'{prefix}_{type_tax_use}', raise_if_not_found=False):
                taxes |= tax
        return taxes

    def _l10n_gt_is_vat_withholding_due(self, agent, subject):
        """ Return whether the agent owes a VAT withholding to the SAT on this line."""
        return agent.l10n_gt_vat_withholding_type and not subject.l10n_gt_vat_withholding_type

    def _l10n_gt_get_vat_withholding_tax_prefix(self, agent, subject):
        """ Return the prefix, without its type_tax_use suffix, of the VAT withholding tax to apply."""
        if agent.l10n_gt_vat_withholding_type == 'exporter':
            # Exporters withhold at the higher rate on agricultural goods only.
            return 'tax_vat_withholding_65' if self.product_id.l10n_gt_agricultural_product else 'tax_vat_withholding_15'
        return VAT_WITHHOLDING_TYPE_TO_TAX.get(agent.l10n_gt_vat_withholding_type)
