from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def raise_event_ticket_service_tracking_error(products):
    """Raise the ValidationError shared by product.product's and
    event.type.ticket's _check_event_ticket_service_tracking constraints.

    `products` only needs to be a non-empty product.product recordset;
    fields_get() reads model metadata, not record data.
    """
    service_tracking = products.fields_get(
        ["service_tracking"], ["string", "selection"]
    )["service_tracking"]
    raise ValidationError(
        _(
            'Products linked to an event ticket must have "%(tracking)s" set to "%(event)s".',
            tracking=service_tracking["string"],
            event=dict(service_tracking["selection"])["event"],
        )
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    event_ticket_ids = fields.One2many(
        comodel_name="event.event.ticket",
        inverse_name="product_id",
        string="Event Tickets",
    )

    # Template tickets need the same guard as event tickets: without this the
    # product could leave service_tracking='event' while an event.type still
    # pointed at it, and the failure only surfaced later and elsewhere, when
    # creating an event from that type copied the product onto an
    # event.event.ticket that does carry the guard.
    event_type_ticket_ids = fields.One2many(
        comodel_name="event.type.ticket",
        inverse_name="product_id",
        string="Event Template Tickets",
    )

    @api.constrains("event_ticket_ids", "event_type_ticket_ids", "service_tracking")
    def _check_event_ticket_service_tracking(self):
        if any(
            product.service_tracking != "event"
            for product in self
            if product.event_ticket_ids or product.event_type_ticket_ids
        ):
            raise_event_ticket_service_tracking_error(self)
