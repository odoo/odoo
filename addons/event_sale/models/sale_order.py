from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class SaleOrder(models.Model):
    _inherit = "sale.order"

    attendee_count = fields.Integer(compute="_compute_attendee_count")

    def write(self, vals):
        """Synchronize partner from SO to registrations. This is done notably
        in website_sale controller shop/address that updates customer, but not
        only."""
        result = super().write(vals)
        if any(line.service_tracking == "event" for line in self.line_ids) and vals.get(
            "partner_id"
        ):
            registrations_toupdate = (
                self.env["event.registration"]
                .sudo()
                .search([("sale_order_id", "in", self.ids)])
            )
            registrations_toupdate.write({"partner_id": vals["partner_id"]})
        return result

    def action_confirm(self):
        res = super().action_confirm()

        for so in self:
            if not any(line.service_tracking == "event" for line in so.line_ids):
                continue
            so_lines_missing_events = so.line_ids.filtered(
                lambda line: line.service_tracking == "event" and not line.event_id
            )
            if so_lines_missing_events:
                so_lines_descriptions = "".join(
                    f"\n- {so_line_description.name}"
                    for so_line_description in so_lines_missing_events
                )
                raise ValidationError(
                    _(
                        "Please make sure all your event related lines are configured before confirming this order:%s",
                        so_lines_descriptions,
                    )
                )
            so.line_ids._init_registrations()
            if len(self) == 1:
                return (
                    self.env["ir.actions.act_window"]
                    .with_context(default_sale_order_id=so.id)
                    ._get_action_dict_by_xml_id(
                        "event_sale.action_sale_order_event_registration"
                    )
                )
        return res

    def action_view_attendee_list(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "event.event_registration_action_tree"
        )
        action["domain"] = [("sale_order_id", "in", self.ids)]
        return action

    def _compute_attendee_count(self):
        sale_orders_data = self.env["event.registration"]._read_group(
            [("sale_order_id", "in", self.ids), ("state", "!=", "cancel")],
            ["sale_order_id"],
            ["__count"],
        )
        attendee_count_data = {
            sale_order.id: count for sale_order, count in sale_orders_data
        }
        for sale_order in self:
            sale_order.attendee_count = attendee_count_data.get(sale_order.id, 0)

    def _get_domain_product_catalog(self):
        return super()._get_domain_product_catalog() & Domain(
            "service_tracking", "!=", "event"
        )
