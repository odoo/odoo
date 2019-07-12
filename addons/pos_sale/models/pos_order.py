# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _default_crm_team(self):
        return self._default_session().config_id.crm_team_id

    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate applicable at the date of the order')
    crm_team_id = fields.Many2one('crm.team', string="Sales Team", default=_default_crm_team)

    @api.depends('pricelist_id.currency_id', 'date_order', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            date_order = order.date_order or fields.Datetime.now()
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.pricelist_id.currency_id, order.company_id, date_order)

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(PosOrder, self)._prepare_invoice()
        invoice_vals['team_id'] = self.crm_team_id
        return invoice_vals
