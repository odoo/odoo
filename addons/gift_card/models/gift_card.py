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
        return '044' + str(uuid4())[4:-8][3:]

    name = fields.Char(compute='_compute_name')
    code = fields.Char(default=lambda x: x._generate_code(), required=True, readonly=True, copy=False)
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

    _sql_constraints = [
        ('unique_gift_card_code', 'UNIQUE(code)', 'The gift card code must be unique.'),
        ('check_amount', 'CHECK(initial_amount >= 0)', 'The initial amount must be positive.')
    ]

    def _compute_name(self):
        for record in self:
            record.name = _("Gift #%s", record.id)

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

    @api.depends("initial_amount")
    def _compute_balance(self):
        for record in self:
            record.balance = record.initial_amount
