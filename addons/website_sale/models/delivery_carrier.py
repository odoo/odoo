# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import website, delivery


class DeliveryCarrier(delivery.DeliveryCarrier, website.WebsitePublishedMultiMixin):

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )
