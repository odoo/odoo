from markupsafe import Markup

from odoo import Command, _, api, fields, models


class EventBoothRegistration(models.Model):
    """event.booth.registrations are used to allow multiple partners to book the same booth.
    Whenever a partner has paid their registration all the others linked to the booth will be deleted."""

    _name = "event.booth.registration"
    _description = "Event Booth Registration"

    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        index=True,
        required=True,
        ondelete="cascade",
    )
    event_booth_id = fields.Many2one(
        comodel_name="event.booth",
        string="Booth",
        index=True,
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="sale_order_line_id.partner_id",
    )
    contact_name = fields.Char(
        compute="_compute_contact_name",
        store=True,
        readonly=False,
    )
    contact_email = fields.Char(
        compute="_compute_contact_email",
        store=True,
        readonly=False,
    )
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="event_booth_registration_phone_number_rel",
        column1="registration_id",
        column2="phone_number_id",
        string="Contact Phone",
        compute="_compute_phone_ids",
        store=True,
        readonly=False,
    )

    _unique_registration = models.Constraint(
        "unique(sale_order_line_id, event_booth_id)",
        "There can be only one registration for a booth by sale order line",
    )

    @api.depends("partner_id")
    def _compute_contact_name(self):
        for registration in self:
            if not registration.contact_name:
                registration.contact_name = registration.partner_id.name or False

    @api.depends("partner_id")
    def _compute_contact_email(self):
        for registration in self:
            if not registration.contact_email:
                registration.contact_email = registration.partner_id.email or False

    @api.depends("partner_id")
    def _compute_phone_ids(self):
        for registration in self:
            if not registration.phone_ids:
                registration.phone_ids = registration.partner_id.phone_ids._primary()

    @api.model
    def _get_fields_for_booth_confirmation(self):
        return [
            "sale_order_line_id",
            "partner_id",
            "contact_name",
            "contact_email",
            "phone_ids",
        ]

    def action_confirm(self):
        for registration in self:
            values = {
                field: registration._booth_confirmation_value(field)
                for field in self._get_fields_for_booth_confirmation()
            }
            registration.event_booth_id.action_confirm(values)
        self._cancel_pending_registrations()

    def _booth_confirmation_value(self, field):
        value = self[field]
        if not isinstance(value, models.BaseModel):
            return value
        if self._fields[field].type == "many2many":
            return [Command.set(value.ids)]
        return value.id

    def _cancel_pending_registrations(self):
        body = Markup("<p>%(message)s: <ul>%(booth_names)s</ul></p>") % {
            "message": _(
                "Your order has been cancelled because the following booths have been reserved"
            ),
            "booth_names": Markup().join(
                Markup("<li>%s</li>") % booth.display_name
                for booth in self.event_booth_id
            ),
        }
        other_registrations = self.search(
            [
                ("event_booth_id", "in", self.event_booth_id.ids),
                ("id", "not in", self.ids),
            ]
        )
        for order in other_registrations.sale_order_line_id.order_id:
            order.sudo().message_post(
                body=body,
                partner_ids=order.user_id.partner_id.ids,
            )
            order.sudo()._action_cancel()
        other_registrations.unlink()
