from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('service_tracking')
    def _onchange_type_event(self):
        if self.service_tracking == 'event':
            self.invoice_policy = 'order'
