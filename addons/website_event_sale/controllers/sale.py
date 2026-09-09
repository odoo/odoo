from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteEventSale(WebsiteSale):
    def _prepare_shop_payment_confirmation_values(self, order):
        values = super()._prepare_shop_payment_confirmation_values(order)
        values["events"] = order.line_ids.event_id
        attendee_per_event_read_group = (
            request.env["event.registration"]
            .sudo()
            ._read_group(
                [("sale_order_id", "=", order.id), ("state", "in", ["open", "done"])],
                groupby=["event_id"],
                aggregates=["id:recordset"],
            )
        )
        values["attendee_ids_per_event"] = {
            event.id: regs.grouped("event_slot_id") if event.is_multi_slots else regs
            for event, regs in attendee_per_event_read_group
        }
        values["urls_per_event"] = {
            event.id: {
                slot.id: event._get_event_resource_urls(slot=slot)
                for slot in value.grouped("event_slot_id")
            }
            if event.is_multi_slots
            else event._get_event_resource_urls()
            for event, value in attendee_per_event_read_group
        }

        return values
