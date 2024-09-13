# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _name = 'account.payment.register.withholding.line'
    _description = 'Payment register withholding line'
    _check_company_auto = True

    # ------------------
    # Fields declaration
    # ------------------

    payment_register_id = fields.Many2one(
        comodel_name='account.payment.register',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='payment_register_id.company_id')
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    name = fields.Char(string='Number')
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        required=True,
        domain="[('l10n_account_withholding_type', '=', parent.partner_type)]"
    )
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_account_withholding_sequence_id')
    base_amount = fields.Monetary(required=True)
    amount = fields.Monetary(compute='_compute_amount', store=True, readonly=False)

    # ----------------
    # Business methods
    # ----------------

    def _get_withholding_tax_values(self):
        """ Helper that uses compute_all in order to return the detail

        :returns: a dict with the amount, account and tax_repartition_line keys.
        """
        self.ensure_one()
        # One line will always have a single tax.
        tax_values = self.tax_id.compute_all(price_unit=self.base_amount, currency=self.payment_register_id.currency_id)['taxes'][0]
        return {
            'amount': tax_values['amount'],
            'account': tax_values['account_id'],
            'tax_repartition_line': tax_values['tax_repartition_line_id'],
            'tax_name': tax_values['name'],
            'tax_base_amount': tax_values['base'],
        }

    @api.depends('base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = line._get_withholding_tax_values()['amount']
