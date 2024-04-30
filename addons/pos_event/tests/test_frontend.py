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

        cls.product_event_basic = cls.env['product.product'].create({
            'name': 'Event Ticket Basic',
            'type': 'service',
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, cls.event_category.id)],
        })

        cls.product_event_vip = cls.env['product.product'].create({
            'name': 'Event Ticket VIP',
            'type': 'service',
            'list_price': 200,
            'taxes_id': False,
            'available_in_pos': True,
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
                'product_id': cls.product_event_basic.id,
                'seats_max': 1,
                'price': 100,
            }), (0, 0, {
                'name': 'Ticket VIP',
                'seats_max': 1,
                'product_id': cls.product_event_vip.id,
                'price': 200,
            })],
        })

        cls.main_pos_config.write({
            'iface_start_categ_id': cls.event_category.id,
        })

    def test_selling_event_in_pos(self):
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'SellingEventInPos', login="pos_user")
