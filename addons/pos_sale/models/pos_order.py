# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate applicable at the date of the order')

    @api.depends('pricelist_id.currency_id', 'date_order', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            date_order = order.date_order or fields.Datetime.now()
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.pricelist_id.currency_id, order.company_id, date_order)

    def _prepare_invoice(self):
        invoice_values = super(PosOrder, self)._prepare_invoice()
        if self.session_id.config_id.crm_team_id:
            invoice_values['team_id'] = self.session_id.config_id.crm_team_id.id

        return invoice_values
