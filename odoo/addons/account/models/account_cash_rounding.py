# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_round
from odoo.exceptions import ValidationError


class AccountCashRounding(models.Model):
    """
    In some countries, we need to be able to make appear on an invoice a rounding line, appearing there only because the
    smallest coinage has been removed from the circulation. For example, in Switzerland invoices have to be rounded to
    0.05 CHF because coins of 0.01 CHF and 0.02 CHF aren't used anymore.
    see https://en.wikipedia.org/wiki/Cash_rounding for more details.
    """
    _name = 'account.cash.rounding'
    _description = 'Account Cash Rounding'
    _check_company_auto = True

    name = fields.Char(string='Name', translate=True, required=True)
    rounding = fields.Float(string='Rounding Precision', required=True, default=0.01,
        help='Represent the non-zero value smallest coinage (for example, 0.05).')
    strategy = fields.Selection([('biggest_tax', 'Modify tax amount'), ('add_invoice_line', 'Add a rounding line')],
        string='Rounding Strategy', default='add_invoice_line', required=True,
        help='Specify which way will be used to round the invoice amount to the rounding precision')
    profit_account_id = fields.Many2one(
        'account.account',
        string='Profit Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
    )
    loss_account_id = fields.Many2one(
        'account.account',
        string='Loss Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
    )
    rounding_method = fields.Selection(string='Rounding Method', required=True,
        selection=[('UP', 'Up'), ('DOWN', 'Down'), ('HALF-UP', 'Nearest')],
        default='HALF-UP', help='The tie-breaking rule used for float rounding operations')
    company_id = fields.Many2one('res.company', related='profit_account_id.company_id')

    @api.constrains('rounding')
    def validate_rounding(self):
        for record in self:
            if record.rounding <= 0:
                raise ValidationError(_("Please set a strictly positive rounding value."))

    def round(self, amount):
        """Compute the rounding on the amount passed as parameter.

        :param amount: the amount to round
        :return: the rounded amount depending the rounding value and the rounding method
        """
        return float_round(amount, precision_rounding=self.rounding, rounding_method=self.rounding_method)

    def compute_difference(self, currency, amount):
        """Compute the difference between the base_amount and the amount after rounding.
        For example, base_amount=23.91, after rounding=24.00, the result will be 0.09.

        :param currency: The currency.
        :param amount: The amount
        :return: round(difference)
        """
        amount = currency.round(amount)
        difference = self.round(amount) - amount
        return currency.round(difference)
