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
            milestone_read_group = self.env['project.milestone'].read_group(
                [('sale_line_id', '!=', False)],
                ['sale_line_ids:array_agg(sale_line_id)'],
                [],
            )
            sale_line_ids = milestone_read_group[0]['sale_line_ids'] if milestone_read_group else []
            sale_lines = self.env['sale.order.line'].sudo().browse(sale_line_ids)
            sale_lines.product_id.service_policy = 'delivered_milestones'
        else:
            product_domain = [('type', '=', 'service'), ('service_type', '=', 'milestones')]
            products = self.env['product.product'].search(product_domain)
            products.service_policy = 'delivered_manual'
            self.env['sale.order.line'].sudo().search([('product_id', 'in', products.ids)]).qty_delivered_method = 'manual'
