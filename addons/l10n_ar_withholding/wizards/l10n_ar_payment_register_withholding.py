# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class l10nArPaymentRegisterWithholding(models.TransientModel):
    _name = 'l10n_ar.payment.register.withholding'
    _description = 'Payment register withholding lines'

    payment_register_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_register_id.company_id')
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    name = fields.Char(string='Number')
    tax_id = fields.Many2one('account.tax', check_company=True,  required=True)
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_ar_withholding_sequence_id')
    base_amount = fields.Monetary(required=True, compute='_compute_base_amount', store=True, readonly=False)
    amount = fields.Monetary(required=True, compute='_compute_amount', store=True, readonly=False)

    @api.depends('tax_id', 'payment_register_id.line_ids', 'payment_register_id.amount', 'payment_register_id.currency_id')
    def _compute_base_amount(self):
        base_lines = self.payment_register_id.line_ids.move_id.invoice_line_ids.filtered(lambda x: x.display_type == 'product')
        supplier_recs = self.filtered(lambda x: x.payment_register_id.partner_type == 'supplier')
        for rec in supplier_recs:
            factor = rec.payment_register_id._l10n_ar_get_payment_factor()
            if not rec.tax_id:
                rec.base_amount = 0.0
                continue
            base_amount = rec._get_base_amount(base_lines, factor)
            if base_amount:
                rec.base_amount = base_amount
        # Only supplier compute base tax
        (self - supplier_recs).base_amount = 0.0

    def _get_base_amount(self, base_lines, factor):
        conversion_rate = self.payment_register_id._get_conversion_rate()
        tax_base_lines = base_lines.filtered(lambda x: self.tax_id in x.product_id.l10n_ar_supplier_withholding_taxes_ids)
        if self.tax_id.l10n_ar_withholding_amount_type == 'untaxed_amount':
            base_amount = factor * sum(tax_base_lines.mapped('price_subtotal'))
        else:
            base_amount = factor * sum(tax_base_lines.mapped('price_total'))
        return self.payment_register_id.currency_id.round(base_amount / conversion_rate)

    def _tax_compute_all_helper(self):
        self.ensure_one()
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = self.tax_id.compute_all(
            self.base_amount,
            currency=self.payment_register_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['taxes'][0]['amount']
        tax_account_id = taxes_res['taxes'][0]['account_id']
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']
        return tax_amount, tax_account_id, tax_repartition_line_id

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount, dummy, dummy = line._tax_compute_all_helper()
