# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)
class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_amount_split_payment = fields.Monetary(string='Split Payment', compute='_compute_amount_split_payment')

    def _compute_amount_split_payment(self):
        for move in self:
            amount = 0.0
            if move.is_invoice(True):
                for line in [line for line in move.line_ids if line.tax_line_id]:
                    tax = line.tax_line_id
                    if tax._l10n_it_get_tax_kind() == 'split_payment':
                        amount -= line.balance
            move.l10n_it_amount_split_payment = amount

    def _l10n_it_edi_filter_tax_details(self, line, tax_values):
        """Filters tax details to only include the positive amounted lines regarding VAT taxes."""
        repartition_line = tax_values['tax_repartition_line']
        tax = repartition_line.tax_id
        kind = tax._l10n_it_get_tax_kind()
        if kind == 'vat' and self.l10n_it_amount_split_payment != 0:
            split_payment_line = self.line_ids.filtered(lambda l: l.tax_line_id._l10n_it_filter_kind('split_payment'))
            if split_payment_line and self.currency_id.compare_amounts(tax_values['tax_amount'], split_payment_line.balance) == 0:
                return False
        return (super()._l10n_it_edi_filter_tax_details(line, tax_values)
                or kind == 'split_payment' and repartition_line.factor_percent >= 0)

    def _l10n_it_edi_prepare_line_details(self, reverse_charge_refund=False, is_downpayment=False, convert_to_euros=True):
        invoice_lines = super()._l10n_it_edi_prepare_fatturapa_line_details(reverse_charge_refund, is_downpayment, convert_to_euros)
        if self.l10n_it_amount_split_payment != 0:
            for i, line_values in enumerate(invoice_lines):
                line = line_values['line']
                line_tax = line.tax_ids
                if line_tax.l10n_it_vat_due_date == 'S' and line_tax.amount_type == 'group':
                    invoice_lines[i]['vat_tax'] = line.tax_ids.children_tax_ids._l10n_it_filter_kind('split_payment')
        return invoice_lines

    def _l10n_it_edi_get_values(self):
        """Add Split Payment features to the XML export values."""
        template_values = super()._l10n_it_edi_get_values()

        if amount_split_payment := self.l10n_it_amount_split_payment:
            document_total = template_values['document_total'] + amount_split_payment

            # Substitute the Split Payment group as a VAT tax
            # with the negative Split Payment child tax id
            # The amount will be turned into its absolute by the template
            for line in template_values['invoice_lines']:
                vat_tax = line['vat_tax']
                if (vat_tax._l10n_it_get_tax_kind() == 'split_payment'
                    and vat_tax.amount_type == 'group'):
                    line['vat_tax'] = vat_tax.children_tax_ids._l10n_it_filter_kind('split_payment')
                    line['vat_tax_amount'] = abs(vat_tax.amount)

        template_values['document_total'] = document_total
        return template_values
