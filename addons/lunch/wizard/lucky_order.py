# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LunchOrderLineLucky(models.TransientModel):
    _name = 'lunch.order.line.lucky'
    _description = 'Lunch Order Line Lucky'

    def _default_supplier(self):
        suppliers_obj = self.env['lunch.product'].search([]).mapped("supplier")
        return [(4, supplier.id) for supplier in suppliers_obj]

    product_id = fields.Many2one('lunch.product', 'Product', store=True)
    supplier_ids = fields.Many2many(comodel_name='res.partner', string='Vendor', domain=lambda self: [("id", "in", self.env['lunch.product'].search([]).mapped("supplier").ids)])
    is_max_budget = fields.Boolean("I'm not feeling rich", help="Enable this option to set a maximal budget for your lucky order.", store=True)
    max_budget = fields.Float('Max Budget', store=True)

    @api.multi
    def random_pick(self):
        """
        To pick a random product from the selected suppliers, and create an order with this one
        """
        self.ensure_one()
        if self.is_max_budget:
            products_obj = self.env['lunch.product'].search([('supplier', "in", self.supplier_ids.ids), ('price', '<=', self.max_budget)])
        else:
            products_obj = self.env['lunch.product'].search([('supplier', "in", self.supplier_ids.ids)])
        if len(products_obj) != 0:
            random_product_obj = self.env['lunch.product'].browse([random.choice(products_obj.ids)])
            order_line = self.env['lunch.order.line'].create({
                'product_id': random_product_obj.id,
                'order_id': self._context['active_id']
            })
        else:
            raise UserError(_('No product is matching your request. Now you will starve to death.'))




