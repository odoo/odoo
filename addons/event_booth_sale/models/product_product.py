from odoo import api, models
from odoo.addons import product


class ProductProduct(models.Model, product.ProductProduct):

    @api.onchange('service_tracking')
    def _onchange_type_event_booth(self):
        if self.service_tracking == 'event_booth':
            self.invoice_policy = 'order'
