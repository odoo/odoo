from odoo import _, api, models
from odoo.addons import event_product


class ProductTemplate(event_product.ProductTemplate):

    def _prepare_service_tracking_tooltip(self):
        if self.service_tracking == 'event':
            return _("Create an Attendee for the selected Event.")
        return super()._prepare_service_tracking_tooltip()

    @api.onchange('service_tracking')
    def _onchange_type_event(self):
        if self.service_tracking == 'event':
            self.invoice_policy = 'order'
