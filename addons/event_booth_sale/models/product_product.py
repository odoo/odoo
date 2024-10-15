from odoo import api, models
from odoo.addons import event_product


class ProductProduct(event_product.ProductProduct):

    @api.onchange('service_tracking')
    def _onchange_type_event_booth(self):
        if self.service_tracking == 'event_booth':
            self.invoice_policy = 'order'
