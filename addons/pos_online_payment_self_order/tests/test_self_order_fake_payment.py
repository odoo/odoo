from datetime import timedelta
from urllib.parse import urlsplit

from freezegun import freeze_time

import odoo.tests
from odoo import Command, fields
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import MailCase
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal
from odoo.addons.pos_online_payment_self_order.models.pos_order import (
    PENDING_ONLINE_PAYMENT_HOLD_MINUTES,
    PresetSlotUnavailableError,
)
from odoo.addons.pos_online_payment_self_order.tests.test_self_order_mobile import (
    TestSelfOrderMobile,
)


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFakePayment(TestSelfOrderMobile):

    _test_user_groups = None  # FIXME list needed groups

    def test_online_payment_mobile(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'self_order_online_payment_method_id': self.online_payment_method.id,
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_online_payment_mobile_self_order_preparation_changes")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order.state, 'paid')

    def test_online_payment_mobile_no_confirmation_page(self):
        self._disable_post_process_patcher()
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'self_order_online_payment_method_id': self.online_payment_method.id,
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_online_payment_mobile_self_order_preparation_changes")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=False)
        self.assertEqual(order.state, 'paid')

    def test_online_payment_kiosk(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_service_mode': 'counter',
            'payment_method_ids': [Command.set(self.online_payment_method.ids)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_online_payment_kiosk_qr_code")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order.state, 'paid')

    def test_online_payment_kiosk_no_confirmation_page(self):
        self._disable_post_process_patcher()
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_service_mode': 'counter',
            'payment_method_ids': [Command.set(self.online_payment_method.ids)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_online_payment_kiosk_qr_code")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=False)
        self.assertEqual(order.state, 'paid')

    def _setup_timing_slot_session(self, slots_per_interval):
        """ Open a mobile self order session, paid online, where the takeout
        preset uses 10 minutes timing slots from 10:00 to 14:00.

        :return: the opened session
        """
        calendar = self.env['resource.calendar'].create({
            'name': 'Takeout 10:00 - 14:00',
            'attendance_ids': [Command.create({
                'dayofweek': str(day),
                'hour_from': 10,
                'hour_to': 14,
            }) for day in range(7)],
        })
        self.out_preset.write({
            'use_timing': True,
            'resource_calendar_id': calendar.id,
            'interval_time': 10,
            'slots_per_interval': slots_per_interval,
            'identification': 'none',
            'available_in_self': True,
        })
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'self_order_online_payment_method_id': self.online_payment_method.id,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        session = self.pos_config.current_session_id
        session.set_opening_control(0, "")
        return session

    def _book_pending_order_a(self, session):
        """ A books tomorrow 12:00 and stops on the payment page without paying.

        :return: the pending order of A
        """
        self.start_tour(self.pos_config._get_self_order_route(), "self_online_payment_slot_pending_order_a")
        order_a = session.order_ids
        self.assertEqual(len(order_a), 1)
        self.assertEqual(order_a.state, 'draft')
        self.assertEqual(order_a.preset_id, self.out_preset)
        self.assertTrue(order_a.preset_time)
        return order_a

    def _get_pay_route(self, order):
        """ Payment page opened from the self order app, with a route back to it. """
        return PaymentPortal._get_pay_route(order.id, order.access_token, exit_route=self._get_back_to_cart_route(order))

    def _open_pay_page(self, order):
        """ Open the payment page of the order from the self order app.

        :return: the payment context of the payment form
        """
        return self._get_payment_context(self._fake_http_get_request(self._get_pay_route(order)))

    def _assert_reschedule_route(self, url, order):
        """ `url` sends the customer back to the cart, to select another slot. """
        url = urlsplit(url)
        self.assertEqual(f"{url.path}?{url.query}#{url.fragment}", self._get_reschedule_route(order))

    def _assert_slot_unavailable(self, order, message):
        """ The slot of the order is refused with `message`. """
        with self.assertRaisesRegex(PresetSlotUnavailableError, message):
            order._check_preset_slot_availability()

    def _assert_pay_page_refused(self, order, message):
        """ Opening the payment page of the order sends the customer back to the
        cart, to select another slot, instead of showing the payment form.
        """
        self._assert_slot_unavailable(order, message)
        response = self.url_open(self._get_pay_route(order), allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self._assert_reschedule_route(response.headers['Location'], order)

    def _request_pay_transaction(self, order, payment_context):
        """ Click on "Pay" on a payment page opened with `payment_context`. """
        route_values = {k: payment_context[k] for k in ['amount', 'access_token', 'landing_route']}
        route_values.update({
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'flow': 'direct',
            'tokenization_requested': False,
        })
        # The transaction route of the payment form carries the route back to the self order app
        return self.make_jsonrpc_request(payment_context['transaction_route'], route_values)

    def _start_pay_transaction(self, order, payment_context):
        """ Click on "Pay" on a payment page opened with `payment_context`, the
        payment is then waiting at the payment provider.

        :return: the created transaction
        """
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._request_pay_transaction(order, payment_context)
        tx = self._get_tx(processing_values['reference'])
        self.assertEqual(tx.state, 'draft')
        return tx

    def _assert_pay_transaction_refused(self, order, payment_context, message):
        """ Clicking on "Pay" on a payment page opened with `payment_context` is
        refused, the customer is sent back to the cart to select another slot.
        """
        processing_values = self._request_pay_transaction(order, payment_context)
        self.assertEqual(processing_values['state'], 'error')
        self.assertTrue(processing_values['pos_online_payment_slot_unavailable'])
        self.assertIn(message, processing_values['state_message'])
        self._assert_reschedule_route(processing_values['exit_route'], order)

    def _confirm_pay_transaction(self, order, tx):
        """ The payment provider confirms the payment started with `tx`. """
        tx.action_confirm()
        self._fake_open_pos_order_pay_confirmation_page(order.id, order.access_token, tx.id, exit_route="/")
        self.assertEqual(order.state, 'paid')

    def _set_transaction_create_date(self, tx, create_date):
        """ Simulate a payment started at `create_date`. """
        self.env.cr.execute("UPDATE payment_transaction SET create_date = %s WHERE id = %s", (create_date, tx.id))
        tx.invalidate_recordset(['create_date'])

    def _expire_transaction_hold(self, tx):
        """ Simulate a payment started too long ago, so it no longer holds the slot of its order. """
        self._set_transaction_create_date(tx, fields.Datetime.now() - timedelta(minutes=PENDING_ONLINE_PAYMENT_HOLD_MINUTES + 1))

    def _get_slot_usage(self, slot):
        """ Orders holding the slot, as shown in the slot pickers. """
        return self.out_preset._compute_slots_usage().get(slot.strftime("%Y-%m-%d %H:%M:%S")) or []

    def _get_back_to_cart_route(self, order):
        """ Route the customer is sent back to when leaving the payment page. """
        return f"/pos-self/{self.pos_config.id}/confirmation/{order.access_token}/order?access_token={self.pos_config.access_token}"

    def _get_reschedule_route(self, order):
        """ Route the customer is sent back to when the slot of the order is refused. """
        return f"{self._get_back_to_cart_route(order)}#reschedule"

    def _book_slot_order(self, session):
        """ Another customer books tomorrow 12:00 and stops on the payment page without paying.

        :return: the new pending order
        """
        orders_before = session.order_ids
        self.start_tour(self.pos_config._get_self_order_route(), "self_online_payment_slot_order_b")
        new_order = session.order_ids - orders_before
        self.assertEqual(len(new_order), 1)
        self.assertEqual(new_order.state, 'draft')
        return new_order

    def test_online_payment_pending_order_releases_timing_slot(self):
        """
        An order waiting for its online payment only holds its timing slot
        while its payment is in progress, for a few minutes: after that, other
        customers can book and pay the same slot until it is full, then the
        first payment is refused and the first customer has to pick another
        slot.
        """
        session = self._setup_timing_slot_session(slots_per_interval=2)
        order_a = self._book_pending_order_a(session)
        slot_x = order_a.preset_time

        # A's payment page is still open while the slot gets full
        payment_context_a = self._open_pay_page(order_a)

        # A does not hold its slot before clicking on "Pay"
        self.assertNotIn(order_a.id, self._get_slot_usage(slot_x))

        # A clicks on "Pay": A holds its slot while its payment is in progress
        tx_a = self._start_pay_transaction(order_a, payment_context_a)
        self.assertIn(order_a.id, self._get_slot_usage(slot_x))

        # The hold ends exactly PENDING_ONLINE_PAYMENT_HOLD_MINUTES after the click on "Pay"
        now = fields.Datetime.now().replace(microsecond=0)
        hold = timedelta(minutes=PENDING_ONLINE_PAYMENT_HOLD_MINUTES)
        with freeze_time(now):
            self._set_transaction_create_date(tx_a, now - hold + timedelta(seconds=1))
            self.assertIn(order_a.id, self._get_slot_usage(slot_x), "The slot is held 1 second before the end of the hold")
            self._set_transaction_create_date(tx_a, now - hold)
            self.assertIn(order_a.id, self._get_slot_usage(slot_x), "The slot is held at the end of the hold")
            self._set_transaction_create_date(tx_a, now - hold - timedelta(seconds=1))
            self.assertNotIn(order_a.id, self._get_slot_usage(slot_x), "The slot is released 1 second after the end of the hold")

        # A never completes its payment: A releases its slot
        self._expire_transaction_hold(tx_a)
        self.assertNotIn(order_a.id, self._get_slot_usage(slot_x))

        # B and B bis: book the same slot while A's payment is pending, and pay it
        order_b = self.env['pos.order']
        for _i in range(2):
            new_order = self._book_slot_order(session)
            self.assertEqual(new_order.preset_time, slot_x)
            self._fake_online_payment(new_order.id, new_order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
            self.assertEqual(new_order.state, 'paid')
            order_b |= new_order

        # A's payment is refused: the slot is now full
        # - from the payment page opened before the slot got full
        self._assert_pay_transaction_refused(order_a, payment_context_a, "Full capacity reached for this timing slot")
        # - when opening the payment page again
        self._assert_pay_page_refused(order_a, "Full capacity reached for this timing slot")
        self.assertEqual(order_a.state, 'draft')
        self.assertFalse(order_a.payment_ids)

        # The abandoned payment of A is cancelled, so that A can pay again
        tx_a.with_context(payment_safe_write=True)._set_canceled()

        # C: A is sent back to the cart, the slot selection opens directly, A picks another slot and pays
        self.start_tour(self._get_reschedule_route(order_a), "self_online_payment_slot_order_a_reschedule_full_slot")
        self.assertEqual(session.order_ids, order_a | order_b, "No new order should be created")
        self.assertEqual(order_a.preset_time, slot_x + timedelta(minutes=30))
        self._fake_online_payment(order_a.id, order_a.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)

        # Validation data
        for order in order_a | order_b:
            self.assertEqual(order.state, 'paid')
            self.assertEqual(order.preset_id, self.out_preset)
            self.assertEqual(order.lines.product_id, self.cola)
            self.assertEqual(len(order.payment_ids), 1)
            self.assertEqual(order.payment_ids.payment_method_id, self.online_payment_method)
            self.assertAlmostEqual(order.payment_ids.amount, order.amount_total)
            self.assertAlmostEqual(order.amount_paid, order.amount_total)
        self.assertEqual(set(order_b.mapped('preset_time')), {slot_x})

        usage = self.out_preset._compute_slots_usage()
        self.assertEqual(sorted(usage[slot_x.strftime("%Y-%m-%d %H:%M:%S")]), sorted(order_b.ids))
        self.assertEqual(usage[order_a.preset_time.strftime("%Y-%m-%d %H:%M:%S")], order_a.ids)

    def test_online_payment_timing_slot_lost(self):
        """
        The order of A loses its timing slot in several ways, each time its
        payment is refused and A has to pick another slot:
        - its payment is declined, its slot is released and taken by B
        - its new slot is already in the past at the time of the payment
        """
        session = self._setup_timing_slot_session(slots_per_interval=1)
        order_a = self._book_pending_order_a(session)
        slot_x = order_a.preset_time
        slot_y = slot_x + timedelta(minutes=30)

        # A's payment is declined: A releases its slot at once
        payment_context_a = self._open_pay_page(order_a)
        tx_a = self._start_pay_transaction(order_a, payment_context_a)
        self.assertIn(order_a.id, self._get_slot_usage(slot_x))
        tx_a.with_context(payment_safe_write=True)._set_error("Payment declined")
        self.assertNotIn(order_a.id, self._get_slot_usage(slot_x))

        # B books the released slot and pays it
        order_b = self._book_slot_order(session)
        self.assertEqual(order_b.preset_time, slot_x)
        self._fake_online_payment(order_b.id, order_b.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order_b.state, 'paid')

        # A's payment page is refused: the slot is full
        self._assert_pay_page_refused(order_a, "Full capacity reached for this timing slot")

        # A comes back to the cart, "Pay" asks for another slot
        self.start_tour(self._get_back_to_cart_route(order_a), "self_online_payment_slot_order_a_change_full_slot")
        self.assertEqual(session.order_ids, order_a | order_b, "No new order should be created")
        self.assertEqual(order_a.preset_time, slot_y)

        # Time flies: the new slot of A is now in the past
        order_a.preset_time = fields.Datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=10)

        # A's payment page is refused: the slot is in the past
        self._assert_pay_page_refused(order_a, "This timing slot is already passed")
        self.assertEqual(order_a.state, 'draft')
        self.assertFalse(order_a.payment_ids)
        self.assertEqual(self.env['payment.transaction'].search([('pos_order_id', '=', order_a.id)]), tx_a)

        # A comes back to the cart, "Pay" asks for another slot
        self.start_tour(self._get_back_to_cart_route(order_a), "self_online_payment_slot_order_a_change_slot")
        self.assertEqual(session.order_ids, order_a | order_b, "No new order should be created")
        self.assertEqual(order_a.preset_time, slot_y)

        # A can now pay on its new slot, despite its declined payment
        self._fake_online_payment(order_a.id, order_a.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order_a.state, 'paid')
        self.assertEqual(len(order_a.payment_ids), 1)
        self.assertAlmostEqual(order_a.amount_paid, order_a.amount_total)

        self.assertEqual(self._get_slot_usage(slot_x), order_b.ids)
        self.assertEqual(self._get_slot_usage(slot_y), order_a.ids)

    def test_online_payment_same_slot_first_payment_wins(self):
        """
        A, B and C pick the same slot and reach the payment page at the same
        time: the first ones to click on "Pay" take the slot up to its
        capacity, whatever the order in which they booked it. The next ones
        are refused until a payment in progress is abandoned.
        """
        session = self._setup_timing_slot_session(slots_per_interval=2)
        order_a = self._book_pending_order_a(session)
        slot_x = order_a.preset_time

        # B and C book the same slot: no payment is in progress, the slot is still free
        order_b = self._book_slot_order(session)
        order_c = self._book_slot_order(session)
        self.assertEqual((order_b | order_c).mapped('preset_time'), [slot_x, slot_x])
        self.assertFalse(self._get_slot_usage(slot_x))

        # A, B and C are on their payment page
        payment_context_a = self._open_pay_page(order_a)
        payment_context_b = self._open_pay_page(order_b)
        payment_context_c = self._open_pay_page(order_c)

        # C then A click on "Pay": they take the slot, even though C booked it last
        tx_c = self._start_pay_transaction(order_c, payment_context_c)
        tx_a = self._start_pay_transaction(order_a, payment_context_a)
        self.assertEqual(sorted(self._get_slot_usage(slot_x)), sorted((order_a | order_c).ids))

        # B clicks on "Pay": refused, the slot is full with the payments in progress
        self._assert_pay_transaction_refused(order_b, payment_context_b, "Full capacity reached for this timing slot")
        self._assert_pay_page_refused(order_b, "Full capacity reached for this timing slot")

        # C completes its payment
        self._confirm_pay_transaction(order_c, tx_c)

        # A abandons its payment: B can now pay on the slot
        self._expire_transaction_hold(tx_a)
        self._fake_online_payment(order_b.id, order_b.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order_b.state, 'paid')

        # A is now refused: the slot is full with paid orders
        self._assert_pay_transaction_refused(order_a, payment_context_a, "Full capacity reached for this timing slot")
        self._assert_pay_page_refused(order_a, "Full capacity reached for this timing slot")
        self.assertEqual(order_a.state, 'draft')
        self.assertFalse(order_a.payment_ids)

        for order in order_b | order_c:
            self.assertEqual(len(order.payment_ids), 1)
            self.assertAlmostEqual(order.amount_paid, order.amount_total)
        self.assertEqual(sorted(self._get_slot_usage(slot_x)), sorted((order_b | order_c).ids))


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFakePaymentMail(MailCase, TestSelfOrderMobile):
    _test_user_groups = None  # FIXME list needed groups

    def test_online_payment_mobile_sends_mail_after_payment(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'self_order_online_payment_method_id': self.online_payment_method.id,
            'use_presets': False,
        })
        self.out_preset.mail_template_id = self.env.ref('pos_self_order.takeout_email_template')
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        order = self.env['pos.order'].create({
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'date_order': fields.Datetime.now(),
            'company_id': self.env.company.id,
            'session_id': self.pos_config.current_session_id.id,
            'source': 'mobile',
            'state': 'draft',
            'preset_id': self.out_preset.id,
            'email': 'after.payment.self.order@test.com',
            'lines': [Command.create({
                'product_id': self.cola.id,
                'qty': 1,
                'price_unit': self.cola.lst_price,
                'price_subtotal': self.cola.lst_price,
                'price_subtotal_incl': self.cola.lst_price,
                'tax_ids': [Command.set([self.default_tax15.id])],
            })],
        })
        order.lines._onchange_amount_line_all()
        order._compute_prices()
        order._portal_ensure_token()

        with self.mock_mail_gateway():
            self.assertEqual(len(self._new_mails), 0)
            self._fake_online_payment(
                order.id,
                order.access_token,
                self.payment_provider.id,
                exit_route="/",
                confirmation_page=True,
            )
            order = self.env['pos.order'].browse(order.id)

        self.assertEqual(order.state, 'paid')
        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(self._new_mails.email_to, order.email)
        self.assertIn('receipt', (self._new_mails.subject or '').lower())
