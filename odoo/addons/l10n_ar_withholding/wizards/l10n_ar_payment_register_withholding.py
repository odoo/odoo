# pylint: disable=protected-access
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class l10nArPaymentRegisterWithholding(models.TransientModel):
    _name = 'l10n_ar.payment.register.withholding'
    _description = 'Payment register withholding lines'
    _check_company_auto = True

    payment_register_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_register_id.company_id')
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    name = fields.Char(string='Number')
    tax_id = fields.Many2one(
        'account.tax', check_company=True, required=True,
        domain="[('l10n_ar_withholding_payment_type', '=', parent.partner_type)]")
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_ar_withholding_sequence_id')
    base_amount = fields.Monetary(required=True)
    amount = fields.Monetary(required=True, compute='_compute_amount', store=True, readonly=False)

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

    @api.depends('base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount, dummy, dummy = line._tax_compute_all_helper()
