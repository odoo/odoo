from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_event_sale.controllers.payment import PaymentPortalOnsite
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteEventSalePayment(TestWebsiteEventSaleCommon):
    """Seat availability check run before a cart payment is accepted."""

    def _make_registrations(self, order):
        editor = Form(
            self.env["registration.editor"].with_context(default_sale_order_id=order.id)
        )
        editor.save().action_make_registration()
        self.env.flush_all()

    def _validate(self, order):
        with MockRequest(self.env):
            PaymentPortalOnsite()._validate_transaction_for_order(
                self.env["payment.transaction"], order
            )

    def test_payment_accepted_for_already_reserved_seats(self):
        """An order whose registrations are already reserved can still be paid.

        A salesperson may confirm the quotation before the customer pays; the
        registrations then flip to `open` and are counted as taken seats. The
        check must not ask for those seats a second time.
        """
        cart = self.empty_cart
        cart._cart_add(self.product_event.id, 2, event_ticket_id=self.ticket.id)
        self.ticket.write({"seats_max": 2, "seats_limited": True})
        self._make_registrations(cart)

        cart.action_confirm()
        self.env.flush_all()
        self.assertEqual(cart.state, "done")
        self.assertEqual(set(cart.line_ids.registration_ids.mapped("state")), {"open"})
        self.assertEqual(self.ticket.seats_available, 0)

        self._validate(cart)

    def test_payment_refused_when_pending_seats_overflow(self):
        """Registrations still to be reserved are checked against the seats."""
        cart = self.empty_cart
        cart._cart_add(self.product_event.id, 2, event_ticket_id=self.ticket.id)
        self._make_registrations(cart)
        self.ticket.write({"seats_max": 1, "seats_limited": True})
        self.env.flush_all()

        with self.assertRaisesRegex(ValidationError, "Pycon"):
            self._validate(cart)

    def test_payment_check_is_grouped_per_event(self):
        """An order spanning two events checks each event on its own.

        Only the capped event may refuse the payment; the uncapped one is
        unconstrained and contributes nothing.
        """
        cart = self.empty_cart
        cart._cart_add(self.product_event.id, 2, event_ticket_id=self.ticket.id)
        cart._cart_add(self.product_event.id, 1, event_ticket_id=self.ticket_2.id)
        self._make_registrations(cart)
        self.ticket.write({"seats_max": 1, "seats_limited": True})
        self.env.flush_all()

        self.assertEqual(len(cart.line_ids.registration_ids), 3)
        self.assertEqual(
            cart.line_ids.registration_ids.event_id,
            self.event | self.event_2,
        )
        with self.assertRaisesRegex(ValidationError, "Pycon"):
            self._validate(cart)

        # Without the tighter cap both events are unconstrained: nothing raises.
        self.ticket.write({"seats_max": 0, "seats_limited": False})
        self.env.flush_all()
        self._validate(cart)
