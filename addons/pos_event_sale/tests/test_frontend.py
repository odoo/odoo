# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.pos_event.tests.test_frontend import TestUi


@tagged('post_install', '-at_install')
class TestPoSEventSale(TestUi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_sale_status_event_in_pos(self):
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_sale_status_event_in_pos', login="pos_user")

        sale_status = self.env['event.registration'].search([]).mapped("sale_status")
        self.assertIn('sold', sale_status)
        self.assertIn('to_pay', sale_status)
