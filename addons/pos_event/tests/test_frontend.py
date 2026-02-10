# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import Command
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.quick_ref('event.group_event_manager')

        cls.event_category = cls.env['pos.category'].create({
            'name': 'Events',
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
            'question_ids': [
                (0, 0, {
                    'title': 'Question1',
                    'question_type': 'simple_choice',
                    'once_per_order': False,
                    'answer_ids': [
                        (0, 0, {'name': 'Q1-Answer1'}),
                        (0, 0, {'name': 'Q1-Answer2'})
                    ],
                }),
                (0, 0, {
                    'title': 'Question2',
                    'question_type': 'simple_choice',
                    'once_per_order': True,
                    'answer_ids': [
                        (0, 0, {'name': 'Q2-Answer1'}),
                        (0, 0, {'name': 'Q2-Answer2'})
                    ],
                })
            ]
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
                    'once_per_order': False,
                }),
                (0, 0, {
                    'title': 'Email',
                    'question_type': 'email',
                    'once_per_order': False,
                }),
            ]
        })

    def test_selling_event_in_pos(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        self.main_pos_config.write({
            "limit_categories": True,
            "iface_available_categ_ids": [(6, 0, [self.event_category.id])],
        })
        self.test_event.write({
            'question_ids': [Command.create({
                'title': 'Question3',
                'question_type': 'simple_choice',
                'once_per_order': True,
                'is_mandatory_answer': True,
                'answer_ids': [
                    (0, 0, {'name': 'Q3-Answer1'}),
                    (0, 0, {'name': 'Q3-Answer2'})
                ]
            })]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'SellingEventInPos', login="pos_user")

        order = self.env['pos.order'].search([], order='id desc', limit=1)
        event_registration = order.lines[0].event_registration_ids
        event_answer_name = event_registration.registration_answer_ids.value_answer_id.mapped('name')
        self.assertEqual(len(event_registration.registration_answer_ids), 3)
        self.assertEqual(event_answer_name, ['Q1-Answer1', 'Q2-Answer1', 'Q3-Answer1'])

    def test_selling_multislot_event_in_pos(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        self.main_pos_config.write({
            "limit_categories": True,
            "iface_available_categ_ids": [(6, 0, [self.event_category.id])],
        })

        slots_day = self.test_event.date_begin.date() + datetime.timedelta(days=2)
        slot_1, slot_2 = self.env['event.slot'].create([
            {
                'date': slots_day,
                'start_hour': 8,
                'end_hour': 9,
                'event_id': self.test_event.id,
            },
            {
                'date': slots_day,
                'start_hour': 10,
                'end_hour': 11,
                'event_id': self.test_event.id,
            }
        ])
        self.test_event.write({
            'is_multi_slots': True,
            'event_slot_ids': [(6, 0, (slot_1 + slot_2).ids)],
        })
        # Reduce first slot availability by one
        registration_1_basic = self.env['event.registration'].create([{
            'event_id': self.test_event.id,
            'event_slot_id': slot_1.id,
            'state': 'open',
            'event_ticket_id': self.test_event.event_ticket_ids[0].id,
        }])
        self.assertEqual(registration_1_basic.event_ticket_id.name, 'Ticket Basic')
        self.assertEqual(slot_1.seats_available, 1)
        self.assertEqual(slot_2.seats_available, 2)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'SellingMultiSlotEventInPos', login="pos_user")

        order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(len(order.lines), 1)

        registrations = order.lines.event_registration_ids
        self.assertEqual(len(registrations), 1)
        self.assertEqual(registrations.event_slot_id.id, slot_1.id)

        self.assertEqual(slot_1.seats_available, 0)

        self.assertEqual(len(registrations.registration_answer_ids), 2)
        event_answer_names = registrations.registration_answer_ids.value_answer_id.mapped('name')
        self.assertEqual(event_answer_names, ['Q1-Answer1', 'Q2-Answer1'])

    def test_selling_multiple_ticket_saved(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_selling_multiple_ticket_saved', login="pos_user")

        order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertTrue(order.lines[0].event_registration_ids)
        self.assertTrue(order.lines[1].event_registration_ids)

    def test_orderline_price_remain_same_as_ticket_price(self):
        """ Test that the order line price remains the same as the ticket price when the customer added to the order. """
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        self.main_pos_config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [self.event_category.id])],
        })
        self.env['res.partner'].search([('name', '=', 'Partner Test 1')]).write({
            'property_product_pricelist': self.main_pos_config.available_pricelist_ids.filtered(lambda pl: pl.item_ids)[0],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_orderline_price_remain_same_as_ticket_price')
        order = self.main_pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.amount_total, 200)
        self.assertEqual(order.lines[0].event_ticket_id.event_id.id, self.test_event.id)

    def test_pos_event_registration_not_mandatory(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })

        event_partner = self.env['res.partner'].create([{
            'name': 'Event Parter',
            'email': "event@partner.com",
            'is_company': False,
        }])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_pos_event_registration_not_mandatory', login="pos_user")

        registrations = self.env['event.registration'].search([('event_id', "=", self.test_event_registration_not_mandatory.id)])
        self.assertEqual(len(registrations), 4)

        # No customer during order, filled registration information
        no_partner_registration = registrations.filtered(lambda r: not r.partner_id)
        self.assertEqual(len(no_partner_registration), 1)
        self.assertEqual(no_partner_registration.name, "Name 1")
        self.assertEqual(no_partner_registration.email, "1@test.com")

        partner_registrations = registrations.filtered(lambda r: r.partner_id == event_partner)
        self.assertEqual(len(partner_registrations), 3)

        # Customer during order, filled registration information
        r2 = partner_registrations.filtered(lambda r: r.name == "Name 2")
        self.assertEqual(len(r2), 1)
        self.assertEqual(r2.email, "2@test.com")

        # Customer during order, partial registration information
        r3 = partner_registrations.filtered(lambda r: r.name == "Name 3")
        self.assertEqual(len(r3), 1)
        self.assertEqual(r3.email, "event@partner.com")

        # Customer during order, no registration information
        r_empty = partner_registrations.filtered(lambda r: r.name == "Event Parter")
        self.assertEqual(len(r_empty), 1)
        self.assertEqual(r_empty.email, "event@partner.com")
