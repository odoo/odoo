import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    attendee_count = fields.Integer(compute="_compute_attendee_count")

    @api.depends("lines.event_registration_ids")
    def _compute_attendee_count(self):
        for order in self:
            order.attendee_count = len(order.lines.mapped("event_registration_ids"))

    def action_view_attendee_list(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "event.event_registration_action_tree"
        )
        action["domain"] = [("pos_order_id", "in", self.ids)]
        return action

    def read_pos_data(self, data, config):
        results = super().read_pos_data(data, config)
        paid_orders = self.filtered_domain(
            [("state", "in", ["paid", "done", "invoiced"])]
        )

        if not paid_orders:
            return results

        lines_with_event = paid_orders.mapped("lines").filtered(
            lambda line: line.event_ticket_id
        )
        event_registration_ids = lines_with_event.event_registration_ids
        results["event.registration"] = self.env[
            "event.registration"
        ]._load_pos_data_read(event_registration_ids, config)
        results["event.event"] = self.env["event.event"]._load_pos_data_read(
            event_registration_ids.mapped("event_id"), config
        )
        results["event.event.ticket"] = self.env[
            "event.event.ticket"
        ]._load_pos_data_read(event_registration_ids.mapped("event_ticket_id"), config)
        results["event.slot"] = self.env["event.slot"]._load_pos_data_read(
            event_registration_ids.mapped("event_slot_id"), config
        )
        results["event.registration.answer"] = self.env[
            "event.registration.answer"
        ]._load_pos_data_read(
            event_registration_ids.mapped("registration_answer_ids"), config
        )

        for registration in event_registration_ids:
            if registration.email:
                registration.action_send_badge_email()

        return results

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid()
        refunded_orderlines = self.lines.refunded_orderline_id
        event_to_cancel = []

        for refunded_orderline in refunded_orderlines:
            if refunded_orderline.event_registration_ids:
                completed_refunds = refunded_orderline.refund_orderline_ids.filtered(
                    lambda line: line.order_id.state in ("paid", "done")
                )
                refund_qty = -sum(completed_refunds.mapped("qty"))
                already_cancelled_qty = len(
                    refunded_orderline.event_registration_ids.filtered(
                        lambda r: r.state == "cancel"
                    )
                )
                to_cancel_qty = max(int(refund_qty) - already_cancelled_qty, 0)
                _logger.debug(
                    "Refund order %s original line %s: completed quantity=%s already cancelled=%s to cancel=%s",
                    self.id,
                    refunded_orderline.id,
                    refund_qty,
                    already_cancelled_qty,
                    to_cancel_qty,
                )
                event_to_cancel += refunded_orderline.event_registration_ids.filtered(
                    lambda registration: registration.state != "cancel"
                ).ids[:to_cancel_qty]

        if event_to_cancel:
            self.env["event.registration"].browse(event_to_cancel).write(
                {"state": "cancel"}
            )

        return result

    def print_event_tickets(self):
        return self.env.ref(
            "event.action_report_event_registration_full_page_ticket"
        ).report_action(self.lines.event_registration_ids)

    def print_event_badges(self):
        return self.env.ref(
            "event.action_report_event_registration_badge"
        ).report_action(self.lines.event_registration_ids)
