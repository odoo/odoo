# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from uuid import uuid4


class GiftCard(models.Model):
    _name = "gift.card"
    _description = "Gift Card"
    _order = 'id desc'
    _check_company_auto = True

    @api.model
    def _generate_code(self):
        return str(uuid4())[4:-8]

    name = fields.Char(compute='_compute_name')
    code = fields.Char(default=_generate_code, required=True, readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', help="If empty, all users can use it")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', readonly=True, related='company_id.currency_id')
    initial_amount = fields.Monetary(required=True, currency_field='currency_id')
    balance = fields.Monetary(compute="_compute_balance")  # in company currency
    expired_date = fields.Date(default=lambda self: fields.Date.add(fields.Date.today(), years=1))
    state = fields.Selection(
        selection=[('valid', 'Valid'), ('expired', 'Expired')],
        default='valid',
        copy=False
    )

    buy_line_id = fields.Many2one("sale.order.line", copy=False, readonly=True,
                                  help="Sale Order line where this gift card has been bought.")
    redeem_line_ids = fields.One2many('sale.order.line', 'gift_card_id', string="Redeems")

    _sql_constraints = [
        ('unique_gift_card_code', 'UNIQUE(code)', 'The gift card code must be unique.'),
        ('check_amount', 'CHECK(initial_amount >= 0)', 'The initial amount must be positive.')
    ]

    @api.depends("balance")
    def _compute_name(self):
        for record in self:
            record.name = _("Gift #%s", self.id)

    @api.depends("initial_amount", "redeem_line_ids")
    def _compute_balance(self):
        for record in self:
            balance = record.initial_amount
            confirmed_line = record.redeem_line_ids.filtered(lambda l: l.state == 'sale')
            if confirmed_line:
                balance -= sum(confirmed_line.mapped(
                    lambda line: line.currency_id._convert(line.price_unit, record.currency_id, record.env.company, line.create_date) * -1
                ))
            record.balance = balance

    @api.autovacuum
    def _gc_mark_expired_gift_card(self):
        self.env['gift.card'].search([
            '&', ('state', '=', 'valid'), ('expired_date', '<', fields.Date.today())
        ]).write({'state': 'expired'})

    def balance_converted(self, currency_id=False):
        # helper to convert the current balance in the currency provided
        return self.currency_id._convert(self.balance, currency_id, self.env.company, fields.Date.today())

    def can_be_used(self):
        # expired state are computed once a day, so can be not synchro
        return self.state == 'valid' and self.balance > 0 and self.expired_date >= fields.Date.today()
