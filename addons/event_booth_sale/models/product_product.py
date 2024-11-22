from odoo import api, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('service_tracking')
    def _onchange_type_event_booth(self):
        if self.service_tracking == 'event_booth':
            self.invoice_policy = 'order'

    @api.constrains('service_tracking')
    def _check_service_tracking_for_event_booths(self):
        for product in self:
            if product.service_tracking != 'event_booth':
                booth_category = self.env['event.booth.category'].search([('product_id', '=', product.id)], limit=1)
                if booth_category:
                    raise ValidationError(
                        "You cannot change the service_tracking of this product because it is already assigned "
                        "to an Event Booth Category. The service_tracking must remain 'event_booth'."
                    )
