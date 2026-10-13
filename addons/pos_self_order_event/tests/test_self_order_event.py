# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import JsonRpcException

from odoo.addons.pos_event.tests.test_frontend import TestUi


@tagged("post_install", "-at_install")
class TestSelfOrderEventPrice(TestUi):

    def test_event_ticket_order_price(self):
        """Ensure event ticket prices are preserved during recomputation."""
        self.main_pos_config.with_user(self.pos_user).open_ui()
        ticket = self.test_event.event_ticket_ids[1]

        order = self.env["pos.order"].create({
            "company_id": self.env.company.id,
            "session_id": self.main_pos_config.current_session_id.id,
            "amount_tax": 0.0,
            "amount_total": ticket.price,
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "lines": [
                Command.create({
                    "qty": 1,
                    "product_id": ticket.product_id.id,
                    "event_ticket_id": ticket.id,
                    "price_unit": ticket.price,
                    "price_subtotal": ticket.price,
                    "price_subtotal_incl": ticket.price,
                }),
            ],
        })

        order.recompute_prices()

        self.assertEqual(
            (order.amount_total, order.lines.price_unit),
            (ticket.price, ticket.price),
            "Use event ticket price, not product price.",
        )

    def test_get_event_registrations_data_access_token(self):
        """Ensure the event registrations endpoint validates the order access token."""
        self.main_pos_config.self_ordering_mode = "mobile"
        self.main_pos_config.with_user(self.pos_user).open_ui()
        ticket = self.test_event.event_ticket_ids[0]

        order = self.env["pos.order"].create({
            "company_id": self.env.company.id,
            "session_id": self.main_pos_config.current_session_id.id,
            "amount_tax": 0.0,
            "amount_total": ticket.price,
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "lines": [
                Command.create({
                    "qty": 1,
                    "product_id": ticket.product_id.id,
                    "event_ticket_id": ticket.id,
                    "price_unit": ticket.price,
                    "price_subtotal": ticket.price,
                    "price_subtotal_incl": ticket.price,
                }),
            ],
        })

        with self.assertRaises(JsonRpcException) as rpc_error:
            self.make_jsonrpc_request(
                "/pos-self-order/get-event-registrations-data",
                {
                    "access_token": self.main_pos_config.access_token,
                    "order_id": order.id,
                    "event_ticket_id": ticket.id,
                    "order_access_token": "wrong-token",
                },
            )

        self.assertEqual(str(rpc_error.exception), "werkzeug.exceptions.Unauthorized")

    def test_event_registration_payload_is_sanitized(self):
        """Registrations are created as superuser from the self-order payload: they must not
        carry commands or fields reaching records outside of the new registration."""
        self.main_pos_config.with_user(self.pos_user).open_ui()
        ticket = self.test_event.event_ticket_ids[0]
        question = self.test_event.question_ids[0]
        victim = self.env["event.registration"].create({
            "event_id": self.test_event.id,
            "event_ticket_id": ticket.id,
            "registration_answer_ids": [Command.create({
                "question_id": question.id,
                "value_answer_id": question.answer_ids[0].id,
            })],
        })
        victim_answer = victim.registration_answer_ids
        other_question = self.env["event.question"].create({
            "title": "Other event question",
            "question_type": "simple_choice",
            "answer_ids": [Command.create({"name": "Other answer"})],
        })

        def check_line(registration_vals):
            line = [Command.CREATE, 0, {
                "product_id": ticket.product_id.id,
                "qty": 1,
                "event_ticket_id": ticket.id,
                "event_registration_ids": [Command.create(registration_vals)],
            }]
            return self.env["pos.order"]._check_pos_order_lines(
                self.main_pos_config, {}, line, self.env["account.fiscal.position"],
            )

        invalid_answer_commands = [
            Command.update(victim_answer.id, {"value_text_box": "Hacked"}),
            Command.delete(victim_answer.id),
            Command.unlink(victim_answer.id),
            Command.link(victim_answer.id),
            Command.set([victim_answer.id]),
            Command.create({"question_id": other_question.id, "value_answer_id": other_question.answer_ids.id}),
            Command.create({"question_id": question.id, "value_answer_id": self.test_event.question_ids[1].answer_ids[0].id}),
        ]
        for answer_command in invalid_answer_commands:
            with self.subTest(answer_command=answer_command), self.assertRaises(ValueError):
                check_line({"name": "Attacker", "registration_answer_ids": [answer_command]})

        result = check_line({
            "name": "Guest",
            "email": "guest@example.com",
            "event_id": self.test_event_registration_not_mandatory.id,
            "event_ticket_id": self.test_event.event_ticket_ids[1].id,
            "state": "done",
            "mail_registration_ids": [Command.clear()],
            "registration_answer_ids": [Command.create({
                "question_id": question.id,
                "value_answer_id": question.answer_ids[1].id,
                "registration_id": victim.id,
                "partner_id": self.partner_a.id,
            })],
        })
        self.assertEqual(result[2]["event_registration_ids"], [Command.create({
            "event_id": self.test_event.id,
            "event_ticket_id": ticket.id,
            "event_slot_id": False,
            "name": "Guest",
            "email": "guest@example.com",
            "phone": None,
            "company_name": None,
            "uuid": None,
            "registration_answer_ids": [Command.create({
                "question_id": question.id,
                "value_answer_id": question.answer_ids[1].id,
                "value_text_box": None,
                "uuid": None,
            })],
        })])
        self.assertEqual(victim.registration_answer_ids, victim_answer)
