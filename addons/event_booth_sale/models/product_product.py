from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('service_tracking')
    def _onchange_type_event_booth(self):
        if self.service_tracking == 'event_booth':
            self.invoice_policy = 'order'

    @api.constrains('service_tracking')
    def _check_service_tracking_for_event_booths(self):
        if product_not_event_booth := self.filtered(lambda p: p.service_tracking != 'event_booth'):
            booth_category = self.env['event.booth.category'].search([('product_id', 'in', product_not_event_booth.ids)], limit=1)
            if booth_category:
                raise ValidationError(
                    _(
                        "You cannot change the service_tracking of the product %(product_name)s because it is already assigned "
                        "to %(booth_category_name)s. The service_tracking must remain 'event_booth'.",
                        product_name=product_not_event_booth.name,
                        booth_category_name=booth_category.name,
                    )
                )
