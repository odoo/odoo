# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import SQL, float_round
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

    name = fields.Char(string="Name", translate=True, required=True)
    sequence = fields.Integer(required=True, default=10)

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
        compute='_compute_profit_account_id',
        store=True,
        readonly=False,
        company_dependent=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        ondelete='restrict',
    )
    loss_account_id = fields.Many2one(
        'account.account',
        string="Loss Account",
        compute='_compute_loss_account_id',
        store=True,
        readonly=False,
        company_dependent=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        ondelete='restrict',
    )

    # Conditions fields
    currency_ids = fields.Many2many(comodel_name='res.currency', string="Currency")
    partner_category_ids = fields.Many2many(comodel_name='res.partner.category', string="Partner Category")
    payment_method_line_ids = fields.Many2many(comodel_name='account.payment.method.line', string="Payment Method")
    company_id = fields.Many2one('res.company', string="Company", ondelete='cascade')

    def _get_default_accounts(self, internal_group):
        return {
            self.env['res.company'].browse(company_id): account_id
            for company_id, account_id in
            self.env.execute_query(SQL(
                """
                SELECT DISTINCT ON (company.id) company.id, account.id
                  FROM res_company company
                  JOIN account_account_res_company_rel rel
                    ON rel.res_company_id = ANY(STRING_TO_ARRAY(RTRIM(company.parent_path, '/'), '/')::int[])
                  JOIN account_account account
                    ON rel.account_account_id = account.id
                 WHERE account.active
                   AND SPLIT_PART(account.account_type, '_', 1) = %(internal_group)s
                """,
                internal_group=internal_group,
            ))
        }

    @api.depends('strategy', 'company_id')
    def _compute_profit_account_id(self):
        default_accounts = self._get_default_accounts('income')
        need_profit_account = self.filtered(lambda r: r.strategy == 'add_invoice_line' and not r.profit_account_id)
        for record in need_profit_account:
            for company, account_id in default_accounts.items():
                if not record.company_id or record.company_id in company.parent_ids:
                    record.with_company(company).profit_account_id = account_id

    @api.depends('strategy', 'company_id')
    def _compute_loss_account_id(self):
        default_accounts = self._get_default_accounts('expense')
        need_loss_account = self.filtered(lambda r: r.strategy == 'add_invoice_line' and not r.loss_account_id)
        for record in need_loss_account:
            for company, account_id in default_accounts.items():
                if not record.company_id or record.company_id in company.parent_ids:
                    record.with_company(company).loss_account_id = account_id

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
