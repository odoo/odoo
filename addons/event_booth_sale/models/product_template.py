from odoo import _, api, fields, models
from odoo.addons import event_sale


class ProductTemplate(event_sale.ProductTemplate):

    service_tracking = fields.Selection(selection_add=[
        ('event_booth', 'Event Booth'),
    ], ondelete={'event_booth': 'set default'})

    def _prepare_service_tracking_tooltip(self):
        if self.service_tracking == 'event_booth':
            return _("Mark the selected Booth as Unavailable.")
        return super()._prepare_service_tracking_tooltip()

    @api.onchange('service_tracking')
    def _onchange_type_event_booth(self):
        if self.service_tracking == 'event_booth':
            self.invoice_policy = 'order'
