from odoo import Command, api, fields, models


class RegistrationEditor(models.TransientModel):
    _name = "registration.editor"
    _description = "Edit Attendee Details on Sales Confirmation"

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        required=True,
        ondelete="cascade",
    )
    event_registration_ids = fields.One2many(
        comodel_name="registration.editor.line",
        inverse_name="editor_id",
        string="Registrations to Edit",
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not res.get("sale_order_id"):
            sale_order_id = res.get("sale_order_id", self.env.context.get("active_id"))
            res["sale_order_id"] = sale_order_id
        sale_order = self.env["sale.order"].browse(res.get("sale_order_id"))
        registrations = self.env["event.registration"].search(
            [
                ("sale_order_id", "=", sale_order.id),
                (
                    "event_slot_id",
                    "in",
                    sale_order.mapped("line_ids.event_slot_id").ids or [False],
                ),
                (
                    "event_ticket_id",
                    "in",
                    sale_order.mapped("line_ids.event_ticket_id").ids,
                ),
                ("state", "!=", "cancel"),
            ]
        )

        so_lines = sale_order.line_ids.filtered("event_ticket_id")
        so_line_to_reg = registrations.grouped("sale_order_line_id")
        attendee_list = []
        for so_line in so_lines:
            so_line_registrations = so_line_to_reg.get(
                so_line, self.env["event.registration"]
            )
            # Add existing registrations
            attendee_list += [
                [
                    0,
                    0,
                    {
                        "event_id": reg.event_id.id,
                        "event_slot_id": reg.event_slot_id.id,
                        "event_ticket_id": reg.event_ticket_id.id,
                        "registration_id": reg.id,
                        "name": reg.name,
                        "email": reg.email,
                        "phone_ids": [
                            Command.link(phone.id) for phone in reg.phone_ids
                        ],
                        "sale_order_line_id": so_line.id,
                    },
                ]
                for reg in so_line_registrations
            ]
            # Add new registrations
            attendee_list += [
                [
                    0,
                    0,
                    {
                        "event_id": so_line.event_id.id,
                        "event_slot_id": so_line.event_slot_id.id,
                        "event_ticket_id": so_line.event_ticket_id.id,
                        "sale_order_line_id": so_line.id,
                        "name": so_line.partner_id.name,
                        "email": so_line.partner_id.email,
                        "phone_ids": [
                            Command.link(phone.id)
                            for phone in so_line.partner_id.phone_ids._primary()
                        ],
                    },
                ]
                for _count in range(
                    int(so_line.product_uom_qty) - len(so_line_registrations)
                )
            ]
        res["event_registration_ids"] = attendee_list
        return self._convert_to_write(res)

    def action_make_registration(self):
        self.check_singleton()
        registrations_to_create = []
        for registration_line in self.event_registration_ids:
            if registration_line.registration_id:
                registration_line.registration_id.write(
                    registration_line._prepare_registration_data()
                )
            else:
                registrations_to_create.append(
                    registration_line._prepare_registration_data(
                        include_event_values=True
                    )
                )

        self.env["event.registration"].create(registrations_to_create)
        # Force compute after wizard so seat validation/emails happen now.
        self.event_registration_ids.registration_id._compute_registration_status()
        return {"type": "ir.actions.act_window_close"}


class RegistrationEditorLine(models.TransientModel):
    """Event Registration"""

    _name = "registration.editor.line"
    _description = "Edit Attendee Line on Sales Confirmation"
    _order = "id desc"

    editor_id = fields.Many2one(comodel_name="registration.editor")
    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sales Order Line",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        required=True,
    )
    company_id = fields.Many2one(related="event_id.company_id")
    registration_id = fields.Many2one(
        comodel_name="event.registration",
        string="Original Registration",
    )
    event_slot_id = fields.Many2one(comodel_name="event.slot")
    event_ticket_id = fields.Many2one(comodel_name="event.event.ticket")
    email = fields.Char()
    phone_ids = fields.Many2many(comodel_name="phone.number")
    name = fields.Char()

    def _prepare_registration_data(self, include_event_values=False):
        self.check_singleton()
        registration_data = {
            "partner_id": self.editor_id.sale_order_id.partner_id.id,
            "name": self.name or self.editor_id.sale_order_id.partner_id.name,
            "phone_ids": [
                Command.set(
                    (
                        self.phone_ids
                        or self.editor_id.sale_order_id.partner_id.phone_ids._primary()
                    ).ids
                )
            ],
            "email": self.email or self.editor_id.sale_order_id.partner_id.email,
        }
        if include_event_values:
            registration_data.update(
                {
                    "event_id": self.event_id.id,
                    "event_slot_id": self.event_slot_id.id,
                    "event_ticket_id": self.event_ticket_id.id,
                    "sale_order_id": self.editor_id.sale_order_id.id,
                    "sale_order_line_id": self.sale_order_line_id.id,
                }
            )
        return registration_data
