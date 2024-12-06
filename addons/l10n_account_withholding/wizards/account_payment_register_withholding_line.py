# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _name = 'account.payment.withholding.line'
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
    partner_type = fields.Selection(related='payment_register_id.partner_type')
    name = fields.Char(string='Sequence Number')
    type_tax_use = fields.Char(compute='_compute_type_tax_use')
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        required=True,
        domain="[('type_tax_use', '=', type_tax_use)]"
    )
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_account_withholding_sequence_id')
    base_amount = fields.Monetary(required=True)
    amount = fields.Monetary(
        string='Withheld Amount',
        compute='_compute_amount',
        store=True,
        readonly=False
    )

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
            'tag_ids': tax_values['tag_ids'],
        }

    def _get_withholding_tax_base_tag_ids(self):
        tag_ids = set()
        for line in self:
            tax_values = line.tax_id.compute_all(price_unit=line.base_amount, currency=line.payment_register_id.currency_id)
            tag_ids.update(tax_values['base_tags'])
        return tag_ids

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = line._get_withholding_tax_values()['amount']

    @api.depends('payment_register_id')
    def _compute_type_tax_use(self):
        for line in self:
            line.type_tax_use = 'sales_wth' if line.partner_type == 'customer' else 'purchases_wth'
