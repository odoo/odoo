from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    event_id = fields.Many2one(
        comodel_name="event.event",
        compute="_compute_event_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        help="Choose an event and it will automatically create a registration for this event.",
    )
    event_slot_id = fields.Many2one(
        comodel_name="event.slot",
        string="Slot",
        compute="_compute_event_related",
        precompute=True,
        store=True,
        readonly=False,
        help="Choose an event slot and it will automatically create a registration for this event slot.",
    )
    event_ticket_id = fields.Many2one(
        comodel_name="event.event.ticket",
        string="Ticket Type",
        compute="_compute_event_related",
        precompute=True,
        store=True,
        readonly=False,
        help="Choose an event ticket and it will automatically create a registration for this event ticket.",
    )
    is_multi_slots = fields.Boolean(related="event_id.is_multi_slots")
    registration_ids = fields.One2many(
        comodel_name="event.registration",
        inverse_name="sale_order_line_id",
        string="Registrations",
    )

    @api.constrains("event_id", "event_slot_id", "event_ticket_id", "product_id")
    def _check_event_registration_ticket(self):
        for so_line in self:
            if so_line.service_tracking == "event" and (
                not so_line.event_id
                or not so_line.event_ticket_id
                or (so_line.is_multi_slots and not so_line.event_slot_id)
            ):
                raise ValidationError(
                    _(
                        "The sale order line with the product %(product_name)s needs an event,"
                        " a ticket and a slot in case the event has multiple time slots.",
                        product_name=so_line.product_id.name,
                    )
                )

    @api.depends("state", "event_id")
    def _compute_product_uom_readonly(self):
        event_lines = self.filtered(lambda line: line.event_id)
        event_lines.update({"product_uom_readonly": True})
        super(SaleOrderLine, self - event_lines)._compute_product_uom_readonly()

    def _init_registrations(self):
        """Create registrations linked to a sales order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line."""
        # Only ever called with one order's own lines (see action_confirm).
        self.order_id.check_singleton()
        registrations_vals = []
        for so_line in self:
            if so_line.service_tracking != "event":
                continue

            for _count in range(
                int(so_line.product_uom_qty) - len(so_line.registration_ids)
            ):
                values = {
                    "sale_order_line_id": so_line.id,
                    "sale_order_id": so_line.order_id.id,
                }
                # Keep paid registrations in draft so attendee details can be
                # filled before confirmation; free ones stay open for seat checks.
                if not so_line.currency_id.is_zero(so_line.price_total):
                    values["state"] = "draft"
                registrations_vals.append(values)

        if registrations_vals:
            self.env["event.registration"].sudo().create(registrations_vals)
        return True

    @api.depends("product_id")
    def _compute_event_id(self):
        event_lines = self.filtered(
            lambda line: line.product_id and line.service_tracking == "event"
        )
        (self - event_lines).event_id = False
        for line in event_lines:
            if line.product_id not in line.event_id.event_ticket_ids.product_id:
                line.event_id = False

    @api.depends("event_id")
    def _compute_event_related(self):
        event_lines = self.filtered("event_id")
        (self - event_lines).event_slot_id = False
        (self - event_lines).event_ticket_id = False
        for line in event_lines:
            if line.event_id != line.event_slot_id.event_id:
                line.event_slot_id = False
            if line.event_id != line.event_ticket_id.event_id:
                line.event_ticket_id = False

    @api.depends("event_ticket_id")
    def _compute_price_and_discount(self):
        super()._compute_price_and_discount()

    @api.depends("event_slot_id", "event_ticket_id")
    def _compute_name(self):
        """Override to add the compute dependency (see _get_line_multiline_description_sale)."""
        super()._compute_name()

    def _get_line_multiline_description_sale(self):
        """Return the ticket-based description when a ticket is set, else defer to the product."""
        if self.event_ticket_id:
            return (
                self.event_ticket_id._get_ticket_multiline_description()
                + (
                    "\n%s" % self.event_slot_id.display_name
                    if self.event_slot_id
                    else ""
                )
                + self._get_line_multiline_description_variants()
            )
        else:
            return super()._get_line_multiline_description_sale()

    def _use_template_name(self):
        """We do not want configured description to get rewritten by template default"""
        if self.event_ticket_id:
            return False
        return super()._use_template_name()

    def _get_price_display(self, pricelist_price=None, base_price=None):
        if self.event_ticket_id and self.event_id:
            event_ticket = self.event_ticket_id
            company = event_ticket.company_id or self.env.company
            if not self.pricelist_item_id._is_discount_shown():
                price = event_ticket.with_context(
                    **self._get_pricelist_price_context()
                ).price_reduce
            else:
                price = event_ticket.price
            return self._convert_to_sol_currency(price, company.currency_id)
        return super()._get_price_display(
            pricelist_price=pricelist_price, base_price=base_price
        )
