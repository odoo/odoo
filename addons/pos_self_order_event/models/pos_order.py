from odoo import Command, api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line, fiscal_position_id):
        result = super()._check_pos_order_lines(pos_config, order, line, fiscal_position_id)

        if line[0] in (Command.CREATE, Command.UPDATE):
            ticket = self.env["event.event.ticket"].browse(line[2].get("event_ticket_id")).exists()

            if ticket and ticket.product_id.id != line[2].get("product_id"):
                return result

            for field in ("event_ticket_id", "event_registration_ids"):
                if value := line[2].get(field):
                    result[2][field] = value

        return result

    def _compute_line_price(self, line, price=False):
        if line.event_ticket_id and line.event_ticket_id.product_id == line.product_id:
            price = line.event_ticket_id.price
        return super()._compute_line_price(line, price)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if registrations := self.mapped('lines.event_registration_ids'):
            registrations._update_available_seat()
        return res
