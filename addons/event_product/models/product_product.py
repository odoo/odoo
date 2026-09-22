from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def raise_event_ticket_service_tracking_error(products):
    """Raise the ValidationError shared by product.product's and
    event.type.ticket's _check_event_ticket_service_tracking constraints.

    `products` must be the offending product.product records, not the whole
    batch being written: they are named in the message, so a multi-record
    write says which product to go and fix.
    """
    service_tracking = products.fields_get(
        ["service_tracking"], ["string", "selection"]
    )["service_tracking"]
    raise ValidationError(
        _(
            'Products linked to an event ticket must have "%(tracking)s" set to '
            '"%(event)s":\n%(products)s',
            tracking=service_tracking["string"],
            event=dict(service_tracking["selection"])["event"],
            products="\n".join(f"- {name}" for name in products.mapped("display_name")),
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
        bad = self.filtered(
            lambda product: (
                (product.event_ticket_ids or product.event_type_ticket_ids)
                and product.service_tracking != "event"
            )
        )
        if bad:
            raise_event_ticket_service_tracking_error(bad)
