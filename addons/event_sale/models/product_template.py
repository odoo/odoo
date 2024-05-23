from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(selection_add=[
        ('event', 'Event Registration'),
    ], ondelete={'event': 'set default'})

    @api.onchange('service_tracking')
    def _onchange_type_event(self):
        if self.service_tracking == 'event':
            self.invoice_policy = 'order'
