# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Channel(models.Model):
    _inherit = 'slide.channel'

    visibility = fields.Selection(selection_add=[('payment', 'On payment')])
    product_id = fields.Many2one('product.product', 'Product', index=True)

    _sql_constraints = [
        ('product_id_check', "CHECK( visibility!='payment' OR product_id IS NOT NULL )", "Product is required for on payment channels.")
    ]

    def _filter_add_member(self, target_user, **member_values):
        """ Overridden to add 'payment' channels to the filtered channels """
        result = super(Channel, self)._filter_add_member(target_user, **member_values)
        return result | self.filtered(lambda channel: channel.visibility == 'payment')
