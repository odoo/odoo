# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
            'date_end': datetime.datetime.now() + datetime.timedelta(days=2),
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
                }),
                (0, 0, {
                    'title': 'Question3',
                    'question_type': 'simple_choice',
                    'once_per_order': True,
                    'is_mandatory_answer': True,
                    'answer_ids': [
                        (0, 0, {'name': 'Q3-Answer1'}),
                        (0, 0, {'name': 'Q3-Answer2'})
                    ],
                })
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
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'SellingEventInPos', login="pos_user")

        order = self.env['pos.order'].search([], order='id desc', limit=1)
        event_registration = order.lines[0].event_registration_ids
        event_answer_name = event_registration.registration_answer_ids.value_answer_id.mapped('name')
        self.assertEqual(len(event_registration.registration_answer_ids), 3)
        self.assertEqual(event_answer_name, ['Q1-Answer1', 'Q2-Answer1', 'Q3-Answer1'])

    def test_selling_multiple_ticket_saved(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
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
