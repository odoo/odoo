# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import Command
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.quick_ref('event.group_event_manager')
        cls.pos_user.group_ids += cls.quick_ref('event.group_event_user')
        cls.event_category = cls.env['pos.category'].create({
            'name': 'Events',
        })

        cls.main_pos_config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [cls.event_category.id])],
        })

        cls.product_event = cls.env['product.product'].create({
            'name': 'Event Ticket',
            'type': 'service',
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
            'service_tracking': 'event',
            'pos_categ_ids': [(4, cls.event_category.id)],
        })

        cls.test_event = cls.env['event.event'].create({
            'name': 'My Awesome Event',
            'user_id': cls.pos_admin.id,
            'date_begin': datetime.datetime.now() + datetime.timedelta(days=1),
            'date_end': datetime.datetime.now() + datetime.timedelta(days=4),
            'seats_limited': True,
            'seats_max': 2,
            'event_ticket_ids': [(0, 0, {
                'name': 'Ticket Basic',
                'product_id': cls.product_event.id,
                'seats_max': 1,
                'price': 100,
            }), (0, 0, {
                'name': 'Ticket VIP',
                'seats_max': 1,
                'product_id': cls.product_event.id,
                'price': 200,
            })],
            'question_ids': [],  # No question by default
        })

        cls.test_event_registration_not_mandatory = cls.env['event.event'].create({
            'name': 'Event regitration not mandatory',
            'user_id': cls.pos_admin.id,
            'date_begin': datetime.datetime.now() + datetime.timedelta(days=1),
            'date_end': datetime.datetime.now() + datetime.timedelta(days=2),
            'seats_limited': True,
            'seats_max': 10,
            'event_ticket_ids': [(0, 0, {
                'name': 'Ticket Basic',
                'product_id': cls.product_event.id,
                'seats_max': 10,
                'price': 100,
            })],
            'question_ids': [
                (0, 0, {
                    'title': 'Name',
                    'question_type': 'name',
                }),
                (0, 0, {
                    'title': 'Email',
                    'question_type': 'email',
                }),
                (0, 0, {
                    'title': 'Phone',
                    'question_type': 'phone',
                }),
            ]
        })

        # pass the tickets explicitly, otherwise copy() suffixes their names with "(copy)"
        cls.test_multislot_event = cls.test_event.copy({
            'event_ticket_ids': [Command.create({
                'name': ticket.name,
                'product_id': ticket.product_id.id,
                'seats_max': ticket.seats_max,
                'price': ticket.price,
            }) for ticket in cls.test_event.event_ticket_ids],
        })
        slots_day = cls.test_multislot_event.date_begin.date() + datetime.timedelta(days=2)
        slot_1, slot_2 = cls.env['event.slot'].create([
            {
                'date': slots_day,
                'start_hour': start_hour,
                'end_hour': start_hour + 1,
                'event_id': cls.test_multislot_event.id,
            }
            for start_hour in [8, 10]
        ])
        cls.test_multislot_event.write({
            'name': 'My Awesome MultiSlot Event',
            'is_multi_slots': True,
            'event_slot_ids': [(6, 0, (slot_1 + slot_2).ids)],
        })

    def test_pos_event_availability(self):
        """Test that event, slot and ticket availabilities are respected in the PoS.

        - Event 'seats_max' = Seats limit for the event, or per slot if multiple slots.
        - Ticket 'seats_max': Ticket seats limit for the event, or per slot if multiple slots.
        - Ticket 'limit_max_per_order': Maximum quantity of the ticket that can be selected at once.

        A registration that would exceed any of these limits must be prevented, and an event, slot or ticket
        with no seats left must be correctly flagged as sold out.
        """
        # --- Event without slots ---
        # Ticket limit: Basic = unlimited (3 max per order), VIP = 1 max
        basic_ticket, _ = self.test_event.event_ticket_ids
        basic_ticket.seats_max = 0
        basic_ticket.limit_max_per_order = 3
        # Event limited (seats max = 2)
        event_limited = self.test_event.copy()
        event_limited.name = "Event Limited"
        # Event not limited
        event_unlimited = self.test_event.copy()
        event_unlimited.name = "Event Unlimited"
        event_unlimited.seats_limited = False
        event_unlimited.seats_max = 0

        # --- Event with slots ---
        # Ticket limit: Basic = unlimited (3 max per order), VIP = 1 max per slot
        basic_ticket, _ = self.test_multislot_event.event_ticket_ids
        basic_ticket.seats_max = 0
        basic_ticket.limit_max_per_order = 3
        # Slots limited (seats max = 2 per slot)
        multislot_event_limited = self.test_multislot_event.copy()
        multislot_event_limited.name = "MultiSlot Event Limited"
        # Slots not limited
        multislot_event_unlimited = self.test_multislot_event.copy()
        multislot_event_unlimited.name = "MultiSlot Event Unlimited"
        multislot_event_unlimited.seats_limited = False
        multislot_event_unlimited.seats_max = 0

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'EventAvailabilityInPos', login="pos_user")

        order = self.env['pos.order'].search([], order='id desc', limit=1)
        event_registrations = order.lines.event_registration_ids
        self.assertEqual(len(event_registrations), 16)
        self.assertTrue(event_limited.event_registrations_sold_out)
        self.assertFalse(event_unlimited.event_registrations_sold_out)
        self.assertTrue(multislot_event_limited.event_registrations_sold_out)
        self.assertFalse(multislot_event_unlimited.event_registrations_sold_out)

    def test_pos_event_questions(self):
        """Test that the registration answers are correctly saved with the order.

        - Mandatory answers are required before the registration popup can be confirmed.
        - Global (once per order) and per-ticket answers are saved on each registration.
        - Editing the answers with a long press on the orderline replaces the previous answers.
        - An order with several event lines (event and multi slot event) saves the registrations,
          the slot and the answers of every line independently.
        - The ticket price must remain the same after setting a customer with a pricelist: the
          pricelist must not recompute the price of an event line.
        """
        self.test_event.write({
            'seats_max': 4,
            'event_ticket_ids': [(1, self.test_event.event_ticket_ids[1].id, {'seats_max': 3})],
            'question_ids': [
                Command.set(self.test_event._default_question_ids()),  # Name, Email, Phone
                Command.create({'title': 'Text Q1', 'question_type': 'text_box', 'once_per_order': True}),
                Command.create({'title': 'Text Q2', 'question_type': 'text_box'}),
                Command.create({
                    'title': 'Choice Q3',
                    'question_type': 'simple_choice',
                    'once_per_order': True,
                    'is_mandatory_answer': True,
                    'answer_ids': [
                        (0, 0, {'name': 'Q3-Answer1'}),
                        (0, 0, {'name': 'Q3-Answer2'})
                    ],
                }),
                Command.create({
                    'title': 'Choice Q4',
                    'question_type': 'simple_choice',
                    'is_mandatory_answer': True,
                    'answer_ids': [
                        (0, 0, {'name': 'Q4-Answer1'}),
                        (0, 0, {'name': 'Q4-Answer2'})
                    ],
                }),
            ],
        })
        self.test_multislot_event.question_ids = [Command.set(self.test_event.question_ids.ids)]
        # Customer with a pricelist
        self.env['res.partner'].search([('name', '=', 'Partner Test 1')]).write({
            'property_product_pricelist': self.main_pos_config.available_pricelist_ids.filtered(lambda pl: pl.item_ids)[1],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('EventQuestionsInPos')

        order = self.main_pos_config.session_ids.order_ids[:1]
        self.assertEqual(len(order.lines), 3)

        # One order line per ticket, each one has a single registration.
        expected_lines = [
            (
                self.test_event, 'Ticket Basic',
                ('Name 1 edited', 'email1@example.com', 'Q1-Answer', 'Q2-Answer1 edited', 'Q3-Answer1', 'Q4-Answer1'),
            ),
            (
                self.test_event, 'Ticket VIP',
                ('Name 2', 'email2@example.com', 'Q1-Answer', 'Q2-Answer2', 'Q3-Answer1', 'Q4-Answer2'),
            ),
            (
                self.test_multislot_event, 'Ticket Basic',
                ('Name 3', 'email3@example.com', 'Q1-Answer', 'Q2-Answer3', 'Q3-Answer2', 'Q4-Answer1'),
            ),
        ]
        for line, (event, ticket_name, answers) in zip(order.lines.sorted('id'), expected_lines):
            registration = line.event_registration_ids
            self.assertEqual(len(registration), 1)
            self.assertEqual(registration.event_id, event)
            self.assertEqual(line.event_ticket_id.name, ticket_name)
            self.assertEqual(registration.name, answers[0], 'Registration name should be propagated from question.')
            self.assertEqual(registration.email, answers[1], 'Registration email should be propagated from question.')
            self.assertEqual(
                set(registration.registration_answer_ids.mapped('display_name')),
                set(answers),
                'Registration answers should correctly be saved. Long press edition should have replaced the original answer.'
            )

    def test_pos_event_registration_not_mandatory(self):
        """Test that when an event's questions (name, email, phone) are not mandatory,
        the registration falls back on the customer's details to fill in any missing information.
        """
        event_partner = self.env['res.partner'].create([{
            'name': 'Event Partner',
            'email': "event@partner.com",
            'is_company': False,
        }])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'EventRegistrationNotMandatoryInPos', login="pos_user")

        registrations = self.env['event.registration'].search([('event_id', "=", self.test_event_registration_not_mandatory.id)])
        self.assertEqual(len(registrations), 4)

        # No customer during order, filled registration information
        # The registration has no partner and keeps the information filled in the popup
        no_partner_registration = registrations.filtered(lambda r: not r.partner_id)
        self.assertEqual(len(no_partner_registration), 1)
        self.assertEqual(no_partner_registration.name, "TEST")
        self.assertEqual(no_partner_registration.email, "2@test.com")
        self.assertEqual(no_partner_registration.phone, "1234567890")
        partner_registrations = registrations.filtered(lambda r: r.partner_id == event_partner)
        self.assertEqual(len(partner_registrations), 3)

        # Customer during order, filled registration information
        # The registration is linked to the customer and keeps the information filled in the popup, not the customer's.
        r2 = partner_registrations.filtered(lambda r: r.name == "Name 2")
        self.assertEqual(len(r2), 1)
        self.assertEqual(r2.email, "2@test.com")
        self.assertEqual(r2.phone, "+99999999")

        # Customer during order, partial registration information
        # The missing email is completed with the customer's.
        r3 = partner_registrations.filtered(lambda r: r.name == "Name 3")
        self.assertEqual(len(r3), 1)
        self.assertEqual(r3.email, "event@partner.com")

        # Customer during order, no registration information
        # The name and email are completed with the customer's.
        r_empty = partner_registrations.filtered(lambda r: r.name == "Event Partner")
        self.assertEqual(len(r_empty), 1)
        self.assertEqual(r_empty.email, "event@partner.com")
