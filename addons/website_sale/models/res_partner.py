# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one('sale.order', compute='_compute_last_website_so_id', string='Last Online Sales Order')

    @api.multi
    def _compute_last_website_so_id(self):
        SaleOrder = self.env['sale.order']
        for partner in self:
            current_website_so = SaleOrder.search([('partner_id', '=', partner.id)]).filtered(lambda so: so.order_line.mapped('product_id.product_tmpl_id').can_access_from_current_website())
            partner.last_website_so_id = current_website_so and current_website_so[0]
