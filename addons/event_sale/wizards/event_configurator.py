from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventEventConfigurator(models.TransientModel):
    _name = "event.event.configurator"
    _description = "Event Configurator"

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    event_id = fields.Many2one(comodel_name="event.event")
    event_slot_id = fields.Many2one(
        comodel_name="event.slot",
        string="Slot",
        compute="_compute_event_slot_id",
        store=True,
        readonly=False,
        domain="[('event_id', '=', event_id)]",
    )
    event_ticket_id = fields.Many2one(
        comodel_name="event.event.ticket",
        string="Ticket Type",
        compute="_compute_event_ticket_id",
        store=True,
        readonly=False,
        domain="[('event_id', '=', event_id)]",
    )
    is_multi_slots = fields.Boolean(related="event_id.is_multi_slots")
    has_available_tickets = fields.Boolean(compute="_compute_has_available_tickets")

    @api.constrains("event_id", "event_slot_id", "event_ticket_id")
    def check_event_id(self):
        error_messages = []
        for record in self:
            # guard on the ticket being set, as the slot branch below does:
            # otherwise a not-yet-chosen ticket is reported as a wrong one and
            # the message renders the empty recordset's name
            if (
                record.event_ticket_id
                and record.event_id.id != record.event_ticket_id.event_id.id
            ):
                error_messages.append(
                    _(
                        'Invalid ticket choice "%(ticket_name)s" for event "%(event_name)s".',
                        ticket_name=record.event_ticket_id.display_name,
                        event_name=record.event_id.display_name,
                    )
                )
            if (
                record.event_slot_id
                and record.event_id.id != record.event_slot_id.event_id.id
            ):
                error_messages.append(
                    _(
                        'Invalid slot choice "%(slot_name)s" for event "%(event_name)s".',
                        slot_name=record.event_slot_id.display_name,
                        event_name=record.event_id.display_name,
                    )
                )
        if error_messages:
            raise ValidationError("\n".join(error_messages))

    @api.depends("product_id")
    def _compute_has_available_tickets(self):
        product_ticket_data = self.env["event.event.ticket"]._read_group(
            [
                ("product_id", "in", self.product_id.ids),
                ("event_id.date_end", ">=", fields.Date.today()),
            ],
            ["product_id"],
            ["__count"],
        )
        mapped_data = dict(product_ticket_data)
        for configurator in self:
            configurator.has_available_tickets = bool(
                mapped_data.get(configurator.product_id)
            )

    @api.depends("is_multi_slots")
    def _compute_event_slot_id(self):
        """Pre-select the slot of the multi slots event selected if it is the only one"""
        multi_slot_configurators = self.filtered("is_multi_slots")
        (self - multi_slot_configurators).event_slot_id = False
        slots_by_event = (
            self.env["event.slot"]
            .search([("event_id", "in", multi_slot_configurators.event_id.ids)])
            .grouped("event_id")
        )
        for configurator in multi_slot_configurators:
            event_slots = slots_by_event.get(
                configurator.event_id, self.env["event.slot"]
            )
            configurator.event_slot_id = event_slots if len(event_slots) == 1 else False

    @api.depends("event_id")
    def _compute_event_ticket_id(self):
        """Pre-select the ticket of the event selected if it is the only one"""
        tickets_by_pair = (
            self.env["event.event.ticket"]
            .search(
                [
                    ("event_id", "in", self.event_id.ids),
                    ("product_id", "in", self.product_id.ids),
                ]
            )
            .grouped(lambda ticket: (ticket.event_id.id, ticket.product_id.id))
        )
        for configurator in self:
            event_tickets = tickets_by_pair.get(
                (configurator.event_id.id, configurator.product_id.id),
                self.env["event.event.ticket"],
            )
            configurator.event_ticket_id = (
                event_tickets if len(event_tickets) == 1 else False
            )
