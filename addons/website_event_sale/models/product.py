from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    event_ticket_ids = fields.One2many(
        comodel_name="event.event.ticket",
        inverse_name="product_id",
        string="Event Tickets",
    )

    def _can_return_content(self, field_name=None, access_token=None):
        if (
            field_name in ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
            and self.sudo().event_ticket_ids
        ):
            return True
        return super()._can_return_content(field_name, access_token)

    def _get_product_placeholder_filename(self):
        if self.event_ticket_ids:
            return (
                "website_event_sale/static/img/event_ticket_placeholder_thumbnail.png"
            )
        return super()._get_product_placeholder_filename()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["event"]
