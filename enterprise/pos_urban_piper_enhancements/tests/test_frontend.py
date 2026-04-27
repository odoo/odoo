# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_urban_piper.tests.test_frontend import TestPosUrbanPiperCommon
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient
from unittest.mock import patch
from odoo.addons.pos_urban_piper_enhancements.controllers.main import PosUrbanPiperEnhancementController


@odoo.tests.tagged('post_install', '-at_install')
class TestPosUrbanPiperEnhancementsCommon(TestPosUrbanPiperCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.up_controller = PosUrbanPiperEnhancementController()


class TestFrontend(TestPosUrbanPiperEnhancementsCommon):

    def test_paid_future_order_creates_session_account_move(self):
        def _mock_make_api_request(self, endpoint, method='POST', data=None, timeout=10):
            return []
        self.urban_piper_config.open_ui()
        with self.MockRequest(self.env):
            self.make_test_order({
                'product_id': self.product_1,
                'quantity': 2,
                'delivery_instruction': 'Leave at door',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat'),
                'delivery_identifier': "order1",
                'delivery_datetime': 30,
                'config_id': self.urban_piper_config,
                'has_tax': False,
                'packaging_charge': 10.0,
                'delivery_charge': 10.0,
                'discount_amount': 10.0
            })
        order = self.env['pos.order'].search([('delivery_identifier', '=', 'order1')])
        self.urban_piper_config._make_order_payment(order)

        session = self.urban_piper_config.current_session_id
        with patch.object(UrbanPiperClient, "_make_api_request", _mock_make_api_request):
            session.action_pos_session_closing_control()
        self.assertEqual(len(session.move_id), 1)
