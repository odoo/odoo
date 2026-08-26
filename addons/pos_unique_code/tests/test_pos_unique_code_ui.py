# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosUniqueCodeUi(TestPointOfSaleHttpCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_pos_unique_code(self):
        free_code = self.env['pos.unique.code'].create({'unique_code': '11111'})
        used_code = self.env['pos.unique.code'].create({'unique_code': '22222', 'is_used': True})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_pos_unique_code')

        self.assertTrue(free_code.is_used, "The confirmed code should have been consumed.")
        self.assertTrue(used_code.is_used)
        orders = self.main_pos_config.current_session_id.order_ids
        self.assertEqual(len(orders), 2, "Both the code-validated and the forced order are paid.")
        self.assertEqual(set(orders.mapped('state')), {'paid'})
        self.assertEqual(
            set(orders.mapped('unique_code')),
            {'11111', False},
            "The confirmed order keeps its code, the forced one has none.",
        )


@tagged('post_install', '-at_install')
class TestKioskUniqueCode(SelfOrderCommonTest):

    def test_kiosk_unique_code(self):
        free_code = self.env['pos.unique.code'].create({'unique_code': '11111'})
        self.env['pos.unique.code'].create({'unique_code': '22222', 'is_used': True})

        self.pos_config.write({
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [(5, 0)],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_tour(self.pos_config._get_self_order_route(), "test_kiosk_unique_code")

        self.assertTrue(free_code.is_used, "The confirmed code should have been consumed.")
        order = self.env['pos.order'].search([('config_id', '=', self.pos_config.id)])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.unique_code, '11111')
