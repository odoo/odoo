# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import website, delivery

from odoo import fields, models


class DeliveryCarrier(models.Model, delivery.DeliveryCarrier, website.WebsitePublishedMultiMixin):

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )
