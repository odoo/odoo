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
            agent, subject, type_tax_use = move.company_id.partner_id, move.commercial_partner_id, 'purchase'
        elif move.is_sale_document(include_receipts=True):
            agent, subject, type_tax_use = move.commercial_partner_id, move.company_id.partner_id, 'sale'
        else:
            return self.env['account.tax']

        taxes = self.env['account.tax']
        if self._l10n_gt_is_isr_withholding_due(agent, subject):
            taxes |= self._l10n_gt_get_isr_withholding_taxes(type_tax_use)
        if self._l10n_gt_is_vat_withholding_due(agent, subject):
            taxes |= self._l10n_gt_get_vat_withholding_tax(agent, subject, type_tax_use)
        return taxes.filtered('active')

    def _l10n_gt_is_isr_withholding_due(self, agent, subject):
        """ Return whether the agent owes an ISR withholding to the SAT on this line."""
        return agent.l10n_gt_isr_withholding_agent and not subject.l10n_gt_isr_withholding_agent

    def _l10n_gt_is_vat_withholding_due(self, agent, subject):
        """ Return whether the agent owes a VAT withholding to the SAT on this line."""
        return agent.l10n_gt_vat_withholding_type and not subject.l10n_gt_vat_withholding_type

    def _l10n_gt_get_isr_withholding_taxes(self, type_tax_use):
        """ Return the ISR withholding taxes, one per bracket of the scale."""
        return self._l10n_gt_get_tax('tax_isr_withholding_5', type_tax_use) | self._l10n_gt_get_tax('tax_isr_withholding_7', type_tax_use)

    def _l10n_gt_get_vat_withholding_tax(self, agent, subject, type_tax_use):
        """ Return the VAT withholding tax matching the regime of the agent."""
        if agent.l10n_gt_vat_withholding_type == 'exporter':
            # Exporters withhold at the higher rate on agricultural goods only.
            prefix = 'tax_vat_withholding_65' if self.product_id.l10n_gt_agricultural_product else 'tax_vat_withholding_15'
        else:
            prefix = VAT_WITHHOLDING_TYPE_TO_TAX[agent.l10n_gt_vat_withholding_type]
        return self._l10n_gt_get_tax(prefix, type_tax_use)

    def _l10n_gt_get_tax(self, prefix, type_tax_use):
        """ Return the tax of the chart template with the given prefix, or nothing if it was deleted."""
        chart_template = self.env['account.chart.template'].with_company(self.move_id.company_id)
        return chart_template.ref(f'{prefix}_{type_tax_use}', raise_if_not_found=False) or self.env['account.tax']
