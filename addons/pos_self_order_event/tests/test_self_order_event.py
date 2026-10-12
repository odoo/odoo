# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

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
