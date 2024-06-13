# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        super().set_values()
        if self.group_project_milestone:
            # Search the milestones containing a SOL and change the qty_delivered_method field of the SOL and the
            # service_policy field set on the product to convert from manual to milestones.
            milestones = self.env['project.milestone'].search_fetch([('sale_line_id', '!=', False)], ['sale_line_id'])
            sale_lines = milestones.sale_line_id.sudo()
            sale_lines.product_id.service_policy = 'delivered_milestones'
        else:
            product_domain = [('type', '=', 'service'), ('service_type', '=', 'milestones')]
            products = self.env['product.product'].search(product_domain)
            products.service_policy = 'delivered_manual'
            self.env['sale.order.line'].sudo().search([('product_id', 'in', products.ids)]).qty_delivered_method = 'manual'
