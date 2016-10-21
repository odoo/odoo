# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseOrder(models.Model):

    _inherit = 'purchase.order'

    website_url = fields.Char('Website URL', compute='_website_url', help='The full URL to access the document through the website.')

    def _website_url(self):
        for order in self:
            order.website_url = '/my/purchase/%s' % (order.id)


class PurchaseOrderLine(models.Model):

    _inherit = 'purchase.order.line'

    # Non-stored related field to allow portal user to see the image of the product he has ordered
    product_image = fields.Binary('Product Image', related="product_id.image")
