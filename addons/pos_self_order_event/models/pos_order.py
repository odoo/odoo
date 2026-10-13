from odoo import Command, api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line, fiscal_position_id):
        result = super()._check_pos_order_lines(pos_config, order, line, fiscal_position_id)

        if line[0] in (Command.CREATE, Command.UPDATE):
            line_data = line[2]
            ticket = self.env["event.event.ticket"].browse(line_data.get("event_ticket_id")).exists()

            if ticket and ticket.product_id.id != line_data.get("product_id"):
                return result

            if line[0] == Command.CREATE:
                result[2]["event_ticket_id"] = ticket.id

            if commands := line_data.get("event_registration_ids"):
                line_ticket = ticket if line[0] == Command.CREATE else pos_config.env["pos.order.line"].browse(result[1]).event_ticket_id

                if not line_ticket:
                    raise ValueError("Event registrations require an event ticket.")

                result[2]["event_registration_ids"] = []
                for command in commands:
                    if command[0] != Command.CREATE:
                        raise ValueError("Event ticket and registration cannot be edited or removed once set.")

                    result[2]["event_registration_ids"].append(
                        Command.create(self._check_event_registration_vals(
                            line_ticket,
                            command[2],
                        ))
                    )

        return result

    @api.model
    def _check_event_registration_vals(self, ticket, vals):
        # Registrations are written as superuser: only keep known fields, and force the event
        # and ticket from the line, so the payload cannot reach any other record.
        event = ticket.event_id
        event_slot_id = vals.get("event_slot_id")
        slot = self.env["event.slot"].browse(event_slot_id).exists()
        answers = []

        if slot and slot.event_id != event:
            raise ValueError("Invalid event slot.")

        for command in vals.get("registration_answer_ids") or []:
            if command[0] != Command.CREATE:
                raise ValueError("Event ticket and registration cannot be edited or removed once set.")

            answer_vals = command[2]
            question_id = answer_vals.get("question_id")
            value_answer_id = answer_vals.get("value_answer_id")
            question = self.env["event.question"].browse(question_id).exists()
            value_answer = self.env["event.question.answer"].browse(value_answer_id).exists()

            if question not in event.question_ids or (value_answer and value_answer.question_id != question):
                raise ValueError("Invalid event question answer.")

            answers.append(Command.create({
                "question_id": question.id,
                "value_answer_id": value_answer.id,
                "value_text_box": answer_vals.get("value_text_box"),
                "uuid": answer_vals.get("uuid"),
            }))

        return {
            "event_id": event.id,
            "event_ticket_id": ticket.id,
            "event_slot_id": slot.id,
            "registration_answer_ids": answers,
            "name": vals.get("name"),
            "email": vals.get("email"),
            "phone": vals.get("phone"),
            "company_name": vals.get("company_name"),
            "uuid": vals.get("uuid"),
        }

    def _compute_line_price(self, line, price=False):
        if line.event_ticket_id and line.event_ticket_id.product_id == line.product_id:
            price = line.event_ticket_id.price
        return super()._compute_line_price(line, price)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if registrations := self.mapped('lines.event_registration_ids'):
            registrations._update_available_seat()
        return res
