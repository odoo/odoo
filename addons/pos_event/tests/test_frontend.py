# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.env.user.group_ids |= self.env.ref('event.group_event_user')
        self.event_category = self.env['pos.category'].create({
            'name': 'Events',
        })
        self.product_event = self.env['product.product'].create({
            'name': 'Event Ticket',
            'type': 'service',
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
            'service_tracking': 'event',
            'pos_categ_ids': [(4, self.event_category.id)],
        })
        self.test_event = self.env['event.event'].create({
            'name': 'My Awesome Event',
            'user_id': self.pos_admin.id,
            'date_begin': datetime.datetime.now() + datetime.timedelta(days=1),
            'date_end': datetime.datetime.now() + datetime.timedelta(days=2),
            'seats_limited': True,
            'seats_max': 2,
            'event_ticket_ids': [(0, 0, {
                'name': 'Ticket Basic',
                'product_id': self.product_event.id,
                'seats_max': 1,
                'price': 100,
            }), (0, 0, {
                'name': 'Ticket VIP',
                'seats_max': 1,
                'product_id': self.product_event.id,
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

    def test_selling_event_in_pos(self):
        self.pos_user.group_ids |= self.env.ref('event.group_event_user')
        self.pos_config.write({
            "limit_categories": True,
            "iface_available_categ_ids": [(6, 0, [self.event_category.id])],
        })
        self.start_pos_tour('SellingEventInPos')
        order = self.env['pos.order'].search([], order='id desc', limit=1)
        event_registration = order.lines[0].event_registration_ids
        event_answer_name = event_registration.registration_answer_ids.value_answer_id.mapped('name')
        self.assertEqual(len(event_registration.registration_answer_ids), 2)
        self.assertEqual(event_answer_name, ['Q1-Answer1', 'Q2-Answer1'])
