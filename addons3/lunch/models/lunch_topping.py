# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.tools import formatLang


class LunchTopping(models.Model):
    _name = 'lunch.topping'
    _description = 'Lunch Extras'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    price = fields.Monetary('Price', required=True)
    supplier_id = fields.Many2one('lunch.supplier', ondelete='cascade')
    topping_category = fields.Integer('Topping Category', required=True, default=1)

    @api.depends('price')
    @api.depends_context('company')
    def _compute_display_name(self):
        currency_id = self.env.company.currency_id
        for topping in self:
            price = formatLang(self.env, topping.price, currency_obj=currency_id)
            topping.display_name = f'{topping.name} {price}'
