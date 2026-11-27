# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@tagged('post_install', '-at_install')
class TestSelfOrderDeposit(SelfOrderCommonTest):

    def test_self_order_keeps_the_deposit_of_its_product(self):
        self.fanta.is_deposit = True
        self.cola.deposit_product_id = self.fanta
        self.pos_config.write({'module_pos_deposit': True, 'self_ordering_mode': 'mobile'})
        self.pos_config.with_user(self.pos_user).open_ui()

        data = self._create_order_data([{'product': self.cola}, {'product': self.fanta}])
        cola_line, deposit_line = (line[2] for line in data['order']['lines'])
        data['order']['relations_uuid_mapping'] = {
            'pos.order.line': {deposit_line['uuid']: {'deposit_main_line_id': cola_line['uuid']}},
        }
        result = self.make_request_to_controller('/pos-self-order/process-order/mobile', data)

        cola, deposit = self.env['pos.order'].browse(result['pos.order'][0]['id']).lines
        self.assertEqual(deposit.deposit_main_line_id, cola)
