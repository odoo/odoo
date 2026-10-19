# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_round, formatLang
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
    _order = 'sequence, id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string="Name", translate=True, inverse='_inverse_name')
    name_placeholder = fields.Char(compute='_compute_name_placeholder')
    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True)

    # Rounding fields
    rounding = fields.Float(
        string="Precision",
        required=True,
        default=1.0,
        help="The smallest value used to round the total amount (e.g., 0.05 or 100).",
    )
    rounding_method = fields.Selection(
        string="Method",
        selection=[
            ('UP', 'Up'),
            ('DOWN', 'Down'),
            ('HALF-UP', 'Nearest'),
        ],
        required=True,
        default='HALF-UP',
        help="The computation rule used to round values (e.g., UP, DOWN, or HALF-UP).",
    )
    strategy = fields.Selection(
        string="Strategy",
        selection=[
            ('biggest_tax', 'Modify tax amount'),
            ('add_invoice_line', 'Add a rounding line'),
        ],
        required=True,
        default='add_invoice_line',
        help="Specify how the rounding difference is applied: add a rounding line or adjust the highest tax amount.",
    )
    profit_account_id = fields.Many2one(
        'account.account',
        string="Profit Account",
        company_dependent=True,
        domain="[('internal_group', '=', 'income')]",
        ondelete='restrict',
        inverse='_inverse_profit_account_id',
    )
    loss_account_id = fields.Many2one(
        'account.account',
        string="Loss Account",
        company_dependent=True,
        domain="[('internal_group', '=', 'expense')]",
        ondelete='restrict',
        inverse='_inverse_loss_account_id',
    )

    # Conditions fields
    currency_ids = fields.Many2many(comodel_name='res.currency', string="Currency")
    partner_category_ids = fields.Many2many(comodel_name='res.partner.category', string="Partner Category")
    payment_method_line_ids = fields.Many2many(comodel_name='account.payment.method.line', string="Payment Method")
    company_id = fields.Many2one('res.company', string="Company", ondelete='cascade')

    def _inverse_name(self):
        for record in self:
            if not record.name:
                for lang in self.env['res.lang'].get_all():
                    record = record.with_context(lang=lang.code)
                    record.name = record.name_placeholder

    def _inverse_profit_account_id(self):
        for record in self:
            if record.profit_account_id and not record.env.company.cash_rounding_profit_account_id:
                record.env.company.cash_rounding_profit_account_id = record.profit_account_id

    def _inverse_loss_account_id(self):
        for record in self:
            if record.loss_account_id and not record.env.company.cash_rounding_loss_account_id:
                record.env.company.cash_rounding_loss_account_id = record.loss_account_id

    @api.depends_context('lang')
    @api.depends('rounding_method', 'rounding', 'strategy')
    def _compute_name_placeholder(self):
        method_labels, strategy_labels = (dict(self._fields[fname]._description_selection(self.env)) for fname in ('rounding_method', 'strategy'))
        for record in self:
            record.name_placeholder = ' '.join(filter(None, [
                method_labels.get(record.rounding_method),
                formatLang(record.env, record.rounding) if record.rounding else None,
                strategy_labels['biggest_tax'] if record.strategy == 'biggest_tax' else None,
            ]))

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
