from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    @api.constrains('event_ticket_ids', 'service_tracking')
    def _check_event_ticket_service_tracking(self):
        if any(product.service_tracking != 'event' for product in self if product.event_ticket_ids):
            service_tracking = self.fields_get(['service_tracking'], ['string', 'selection'])['service_tracking']
            raise ValidationError(_(
                'Products linked to an event ticket must have "%(tracking)s" set to "%(event)s".',
                tracking=service_tracking['string'],
                event=dict(service_tracking['selection'])['event'],
            ))
