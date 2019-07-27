# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        """ If the product of an order line is a 'course', we add the client of the sale_order
        as a member of the channel(s) on which this product is configured (see slide.channel.product_id). """
        result = super(SaleOrder, self)._action_confirm()

        so_lines = self.env['sale.order.line'].search(
            [('order_id', 'in', self.ids)]
        )
        products = so_lines.mapped('product_id')
        related_channels = self.env['slide.channel'].search(
            [('product_id', 'in', products.ids)]
        )
        channel_products = related_channels.mapped('product_id')

        channels_per_so = {sale_order: self.env['slide.channel'] for sale_order in self}
        for so_line in so_lines:
            if so_line.product_id in channel_products:
                for related_channel in related_channels:
                    if related_channel.product_id == so_line.product_id:
                        channels_per_so[so_line.order_id] = channels_per_so[so_line.order_id] | related_channel

        for sale_order, channels in channels_per_so.items():
            channels._action_add_members(sale_order.partner_id)

        return result
