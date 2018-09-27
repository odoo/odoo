# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one('sale.order', compute='_compute_last_website_so_id', string='Last Online Sales Order')

    @api.multi
    def _compute_last_website_so_id(self):
        SaleOrder = self.env['sale.order']
        website_team = self.env.ref('sales_team.salesteam_website_sales', raise_if_not_found=False)
        for partner in self:
            if request and hasattr(request, 'website'):
                my_website_so = SaleOrder.search([('partner_id', '=', partner.id), ('team_id', '=', website_team.id)])
                current_website_orders = my_website_so.filtered(lambda so: so.order_line.mapped('product_id.product_tmpl_id').can_access_from_current_website())
                partner.last_website_so_id = current_website_orders and current_website_orders[0]
            else:
                partner.last_website_so_id = False  # Not in a website context
