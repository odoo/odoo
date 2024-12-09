# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


# defined for access rules
class ProductProduct(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    def _get_product_placeholder_filename(self):
        if self.event_ticket_ids:
            return 'website_event_sale/static/img/event_ticket_placeholder_thumbnail.png'
        return super()._get_product_placeholder_filename()

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["event"]
