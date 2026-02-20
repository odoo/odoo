from unittest.mock import patch

import odoo

from odoo.addons.point_of_sale.models.pos_payment_method import PosPaymentMethod
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestBackend(TestPoSCommon):

    def test_onchange_payment_provider(self):
        pm = self.env['pos.payment.method'].create({'name': 'Test PM'})
        with patch.object(PosPaymentMethod, '_get_terminal_provider_selection', return_value=[('terminal_1', 'Terminal 1'), ('terminal_2', 'Terminal 2')]), \
             patch.object(PosPaymentMethod, '_get_external_qr_provider_selection', return_value=[('qr_1', 'QR Code 1'), ('qr_2', 'QR Code 2')]):
            # False --> terminal_1 = terminal
            pm.payment_provider = 'terminal_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_1 --> terminal_2 = terminal
            pm.payment_provider = 'terminal_2'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_2 --> qr_1 = external_qr
            pm.payment_provider = 'qr_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_1 --> qr_2 = external_qr
            pm.payment_provider = 'qr_2'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_2 --> False = external_qr
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # False --> qr_1 = external_qr
            pm.payment_provider = 'qr_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_1 --> terminal_1 = terminal
            pm.payment_provider = 'terminal_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_1 --> False = terminal
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

    def test_onchange_payment_method_type(self):
        pm = self.env['pos.payment.method'].create({'name': 'Test PM'})
        with patch.object(PosPaymentMethod, '_get_terminal_provider_selection', return_value=[('terminal_1', 'Terminal 1'), ('terminal_2', 'Terminal 2')]), \
             patch.object(PosPaymentMethod, '_get_external_qr_provider_selection', return_value=[('qr_1', 'QR Code 1'), ('qr_2', 'QR Code 2')]):
            # (False) none --> terminal = False
            pm.payment_method_type = 'terminal'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> external_qr = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'external_qr'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (qr_1) external_qr --> terminal = False
            pm.payment_provider = 'qr_1'
            pm.payment_method_type = 'terminal'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> none = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'none'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)
