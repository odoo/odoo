import logging
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestEventOrderSync(CommonPosTest):
    def setUp(self):
        super().setUp()
        self.env.user.group_ids += self.env.ref("event.group_event_manager")
        self.pos_config_usd.open_ui()
        self.session = self.pos_config_usd.current_session_id
        self.event = self.env["event.event"].create(
            {
                "name": "Refund synchronization",
                "date_begin": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + timedelta(days=1),
            }
        )

    def _create_order(self, **values):
        return self.env["pos.order"].create(
            {
                "session_id": self.session.id,
                "amount_tax": 0,
                "amount_total": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "qty": 1,
                            "price_unit": 0,
                            "price_subtotal": 0,
                            "price_subtotal_incl": 0,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
                **values,
            }
        )

    def test_saved_refund_cancels_original_event_registration(self):
        original = self._create_order(state="paid")
        registration = self.env["event.registration"].create(
            {
                "name": "Ticket holder",
                "event_id": self.event.id,
                "pos_order_line_id": original.lines.id,
            }
        )
        refund = self._create_order(is_refund=True)
        self.assertEqual(registration.state, "open")

        self.env["pos.order"].sync_from_ui(
            [
                {
                    "uuid": refund.uuid,
                    "session_id": self.session.id,
                    "state": "paid",
                    "lines": [
                        Command.update(
                            refund.lines.id,
                            {"qty": -1, "refunded_orderline_id": original.lines.id},
                        )
                    ],
                }
            ]
        )

        _logger.debug(
            "Refund %s registration state=%s", refund.uuid, registration.state
        )
        self.assertEqual(refund.state, "paid")
        self.assertEqual(registration.state, "cancel")

    def test_backend_refund_payment_wizard_cancels_ticket(self):
        original = self._create_order(state="paid")
        registration = self.env["event.registration"].create(
            {
                "name": "Backend refund ticket",
                "event_id": self.event.id,
                "pos_order_line_id": original.lines.id,
            }
        )
        refund = original._refund()
        wizard = (
            self.env["pos.make.payment"]
            .with_context(active_model="pos.order", active_id=refund.id)
            .create({})
        )

        wizard.action_make_payment()

        _logger.debug(
            "Backend refund %s state=%s ticket=%s",
            refund.id,
            refund.state,
            registration.state,
        )
        self.assertEqual(refund.state, "paid")
        self.assertEqual(registration.state, "cancel")

    def test_repeated_settlement_cancels_each_refunded_ticket_once(self):
        original = self._create_order(state="paid")
        original.lines.qty = 2
        registrations = self.env["event.registration"].create(
            [
                {
                    "name": name,
                    "event_id": self.event.id,
                    "pos_order_line_id": original.lines.id,
                }
                for name in ("One", "Two")
            ]
        )
        for expected_cancelled in (1, 2):
            refund = self._create_order(is_refund=True)
            refund.lines.write({"qty": -1, "refunded_orderline_id": original.lines.id})
            refund.action_pos_order_paid()
            refund.action_pos_order_paid()
            self.assertEqual(
                len(registrations.filtered(lambda ticket: ticket.state == "cancel")),
                expected_cancelled,
            )

    def test_failed_settlement_keeps_registration_and_draft(self):
        original = self._create_order(state="paid")
        registration = self.env["event.registration"].create(
            {
                "name": "Unpaid refund ticket",
                "event_id": self.event.id,
                "pos_order_line_id": original.lines.id,
            }
        )
        refund = self._create_order(is_refund=True, amount_total=-10)
        refund.lines.write({"qty": -1, "refunded_orderline_id": original.lines.id})
        with self.assertRaises(UserError):
            refund.action_pos_order_paid()
        self.assertEqual(refund.state, "draft")
        self.assertEqual(registration.state, "open")

    def test_fractional_refunds_cancel_ticket_when_quantity_reaches_one(self):
        original = self._create_order(state="paid")
        registration = self.env["event.registration"].create(
            {
                "name": "Accumulated refund ticket",
                "event_id": self.event.id,
                "pos_order_line_id": original.lines.id,
            }
        )
        for qty, expected in ((0.1, "open"), (0.7, "open"), (0.2, "cancel")):
            refund = self._create_order(is_refund=True)
            refund.lines.write(
                {"qty": -qty, "refunded_orderline_id": original.lines.id}
            )
            refund.action_pos_order_paid()
            _logger.debug(
                "Accumulated refund qty=%s ticket=%s",
                original.lines.refunded_qty,
                registration.state,
            )
            self.assertEqual(registration.state, expected)

    def test_finalizing_saved_refund_without_line_commands_cancels_ticket(self):
        original = self._create_order(state="paid")
        registration = self.env["event.registration"].create(
            {
                "name": "Stored refund ticket",
                "event_id": self.event.id,
                "pos_order_line_id": original.lines.id,
            }
        )
        refund = self._create_order(is_refund=True)
        refund.lines.write({"qty": -1, "refunded_orderline_id": original.lines.id})

        self.env["pos.order"].sync_from_ui(
            [
                {
                    "uuid": refund.uuid,
                    "session_id": self.session.id,
                    "state": "paid",
                }
            ]
        )

        self.assertEqual(registration.state, "cancel")

    def test_draft_refund_does_not_cancel_ticket(self):
        original = self._create_order(state="paid")
        registration = self.env["event.registration"].create(
            {
                "name": "Pending refund ticket",
                "event_id": self.event.id,
                "pos_order_line_id": original.lines.id,
            }
        )
        refund = self._create_order(is_refund=True)

        self.env["pos.order"].sync_from_ui(
            [
                {
                    "uuid": refund.uuid,
                    "session_id": self.session.id,
                    "state": "draft",
                    "lines": [
                        Command.update(
                            refund.lines.id,
                            {
                                "qty": -1,
                                "refunded_orderline_id": original.lines.id,
                            },
                        )
                    ],
                }
            ]
        )

        _logger.debug(
            "Pending refund %s leaves registration %s", refund.id, registration.state
        )
        self.assertEqual(registration.state, "open")

    def test_cancelled_and_draft_refunds_do_not_inflate_ticket_cancellation(self):
        original = self._create_order(state="paid")
        original.lines.qty = 3
        registrations = self.env["event.registration"].create(
            [
                {
                    "name": name,
                    "event_id": self.event.id,
                    "pos_order_line_id": original.lines.id,
                }
                for name in ("First", "Second", "Third")
            ]
        )
        for state in ("cancel", "draft"):
            prior = self._create_order(is_refund=True, state=state)
            prior.lines.write({"qty": -1, "refunded_orderline_id": original.lines.id})
        refund = self._create_order(is_refund=True)

        self.env["pos.order"].sync_from_ui(
            [
                {
                    "uuid": refund.uuid,
                    "session_id": self.session.id,
                    "state": "paid",
                    "lines": [
                        Command.update(
                            refund.lines.id,
                            {
                                "qty": -1,
                                "refunded_orderline_id": original.lines.id,
                            },
                        )
                    ],
                }
            ]
        )

        self.assertEqual(
            len(registrations.filtered(lambda ticket: ticket.state == "cancel")), 1
        )

    def test_refund_from_multiple_orders_is_rejected(self):
        first = self._create_order(state="paid")
        second = self._create_order(state="paid")
        refund = self._create_order(is_refund=True)
        commands = [
            Command.update(refund.lines.id, {"refunded_orderline_id": first.lines.id}),
            Command.create({"refunded_orderline_id": second.lines.id}),
        ]

        with self.assertRaises(ValidationError):
            self.env["pos.order"].sync_from_ui(
                [
                    {
                        "uuid": refund.uuid,
                        "session_id": self.session.id,
                        "lines": commands,
                    }
                ]
            )

        self.assertFalse(refund.lines.refunded_orderline_id)
