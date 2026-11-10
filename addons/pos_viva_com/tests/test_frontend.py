# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_viva_com.models.pos_payment_method import PosPaymentMethod
from unittest.mock import patch
from odoo import Command
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestVivaComHttpCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create Viva.com payment method
        cls.viva_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Viva',
            'journal_id': cls.bank_journal.id,
            'use_payment_terminal': 'viva_com',
            'viva_com_merchant_id': 'test-merchant-id',
            'viva_com_api_key': 'test-api-key',
            'viva_com_client_id': 'test-client-id',
            'viva_com_client_secret': 'test-client-secret',
            'viva_com_terminal_id': '01234543210',
        })
        payment_methods = cls.main_pos_config.payment_method_ids | cls.viva_payment_method
        cls.main_pos_config.write({'payment_method_ids': [Command.set(payment_methods.ids)]})

    def test_viva_payment_and_refund(self):
        viva_session_id = ''
        viva_amount = 0
        currency_iso = self.main_pos_config.currency_id.iso_numeric

        def mocked_call_viva_com_check_post_data(self, endpoint, action, data=None, should_retry=True):
            nonlocal viva_session_id, viva_amount
            if endpoint == 'transactions:sale' and action == 'post':
                if not isinstance(data['amount'], int):
                    raise TypeError(f"Expected 'amount' to be an integer, but got {data['amount']}.")
                if not data['terminalId'] == '01234543210':
                    raise Exception(f"Expected 'terminalId' to be 01234543210, but got {data['terminalId']}")
                if not data.get('sessionId'):
                    raise Exception("Expected 'sessionId' to be present")
                viva_session_id = data['sessionId']
                viva_amount = data['amount'] / 100
            elif endpoint == 'transactions:refund' and action == 'post':
                if not data['parentSessionId'] == viva_session_id:
                    raise Exception(f"Expected 'parentSessionId' to be {viva_session_id}, but got {data['parentSessionId']}")
                if not data.get('sessionId'):
                    raise Exception("Expected 'sessionId' to be present")
                viva_session_id = data['sessionId']
                viva_amount = -data['amount'] / 100
            elif endpoint == 'sessions/123' and action == 'get':
                return {"success": True, "sessionId": viva_session_id, "transactionId": "test-transaction-id"}
            else:
                raise Exception(f"Unexpected Viva request: endpoint='{endpoint}', method='{action}'")
            return {}

        def mocked_get_transactions(self, transaction_id):
            # Viva.com confirms a finalized transaction matching the payment line.
            return [{
                'StatusId': 'F',
                'MerchantTrns': f'{viva_session_id}/{self.env.company.id}',
                'Amount': viva_amount,
                'CurrencyCode': currency_iso,
            }]

        with patch.object(PosPaymentMethod, '_call_viva_com', mocked_call_viva_com_check_post_data), \
             patch.object(PosPaymentMethod, '_viva_com_get_transactions', mocked_get_transactions):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'VivaComTour', login="accountman")

    def test_viva_com_verify_transaction_amount(self):
        """A tip can make a sale larger, a refund must match exactly."""
        self.main_pos_config.open_ui()
        order = self.env['pos.order'].create({
            'config_id': self.main_pos_config.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.main_pos_config.company_id.id,
            'amount_total': 10.0,
            'amount_paid': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })
        cases = [
            (10.0, 10.0, 'valid'),
            (10.0, 12.0, 'valid'),
            (10.0, 9.0, 'mismatch'),
            (-10.0, -10.0, 'valid'),
            (-10.0, -1.0, 'mismatch'),
            (-10.0, -20.0, 'mismatch'),
            (-10.0, 10.0, 'mismatch'),
        ]
        for line_amount, viva_amount, expected in cases:
            transaction = {
                'StatusId': 'F',
                'MerchantTrns': None,
                'Amount': viva_amount,
                'CurrencyCode': order.currency_id.iso_numeric,
            }
            with self.subTest(line_amount=line_amount, viva_amount=viva_amount), \
                 patch.object(PosPaymentMethod, '_viva_com_get_transactions', return_value=[transaction]):
                payment = self.env['pos.payment'].new({
                    'pos_order_id': order.id,
                    'payment_method_id': self.viva_payment_method.id,
                    'amount': line_amount,
                })
                result = payment._viva_com_verify_transactions('test-transaction-id')
                self.assertEqual(result[0]['status'], expected)

    def test_viva_com_get_order_code(self):
        """The order code is returned as a string, it can exceed JavaScript's safe integers."""
        self.main_pos_config.open_ui()
        order = self.env['pos.order'].create({
            'config_id': self.main_pos_config.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.main_pos_config.company_id.id,
            'amount_total': 10.0,
            'amount_paid': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })
        payment = self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': self.viva_payment_method.id,
            'amount': 10.0,
            'transaction_id': 'test-transaction-id',
        }).with_user(self.pos_user)
        # Shape returned by the Viva.com transactions API
        transaction = {'StatusId': 'F', 'Amount': 10.0, 'Order': {'OrderCode': 9315097989016751}}
        with patch.object(PosPaymentMethod, '_viva_com_get_transactions', return_value=[transaction]) as get_transactions:
            self.assertEqual(payment.viva_com_get_order_code(), '9315097989016751')
        get_transactions.assert_called_once_with('test-transaction-id')

        with patch.object(PosPaymentMethod, '_viva_com_get_transactions', return_value=[]):
            self.assertFalse(payment.viva_com_get_order_code())

    def test_viva_com_kiosk_request_data(self):
        """Kiosk: ``cashRegisterId`` must fall back to ``pos.config.name``."""
        config_name = self.main_pos_config.name

        def mocked_call_viva_com_kiosk(self, endpoint, action, data=None):
            if action == 'post' and data is not None:
                cash_register_id = data.get('cashRegisterId')
                if cash_register_id != config_name:
                    raise AssertionError(
                        "Without a cashier, Viva payload must use pos.config.name as cashRegisterId "
                        f"(expected {config_name!r}, got {cash_register_id!r})",
                    )
            return {}

        with patch.object(PosPaymentMethod, '_call_viva_com', mocked_call_viva_com_kiosk):
            self.main_pos_config.open_ui()
            self.start_tour(
                "/pos/ui?config_id=%d" % self.main_pos_config.id,
                'VivaComKioskTour',
                login="accountman",
            )
