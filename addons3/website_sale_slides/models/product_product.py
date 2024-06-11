# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class Product(models.Model):
    _inherit = "product.product"

    channel_ids = fields.One2many('slide.channel', 'product_id', string='Courses')

    def get_product_multiline_description_sale(self):
        payment_channels = self.channel_ids.filtered(lambda course: course.enroll == 'payment')

        if not payment_channels:
            return super(Product, self).get_product_multiline_description_sale()

        new_line = '' if len(payment_channels) == 1 else '\n'
        return _('Access to: %s%s', new_line, '\n'.join(payment_channels.mapped('name')))
