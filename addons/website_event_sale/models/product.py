# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


# defined for access rules
class ProductProduct(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    def _can_return_content(self, field_name=None, access_token=None):
        """ Override of `orm` to give public users access to the unpublished product image.

        Give access to the public users to the unpublished product images if they are linked to an
        event ticket.

        :param field_name: The name of the field to check.
        :param access_token: The access token.
        :return: Whether to allow the access to the image.
        :rtype: bool
        """
        if (
            field_name in ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
            and self.sudo().event_ticket_ids
        ):
            return True
        return super()._can_return_content(field_name, access_token)

    def _get_product_placeholder_filename(self):
        if self.event_ticket_ids:
            return 'website_event_sale/static/img/event_ticket_placeholder_thumbnail.png'
        return super()._get_product_placeholder_filename()

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["event"]
