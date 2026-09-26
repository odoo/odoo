# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderController(SelfOrderCommonTest):
    def test_order_sanatization(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        params = {
            'company_id': self.env.company.id,
            'uuid': '61f8181c-18e1-4b83-8a7b-21224750fe2f',
            'state': 'draft',
            'session_id': self.pos_config.current_session_id.id,
            'amount_total': 0,
            'amount_paid': 0,
            'account_move': 'test',  # This field should be removed by the _check_pos_order method
            'access_token': 'test',  # This field should be removed by the _check_pos_order method
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [[0, 0, {
                    'product_id': self.cola.id, 'qty': 1,
                    'price_unit': self.cola.lst_price,
                    'price_subtotal': self.cola.lst_price,
                    'tax_ids': [(6, 0, self.cola.taxes_id.ids)],
                    'price_subtotal_incl': 0,
                }],
            ],
        }
        data = self.env['pos.order']._check_pos_order(self.pos_config, params, None)
        self.assertFalse('account_move' in data)  # Do not add it back, if needed contact the PoS team.
        self.assertFalse('access_token' in data)  # Do not add it back, if needed contact the PoS team.
