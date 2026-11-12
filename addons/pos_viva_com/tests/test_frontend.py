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
        viva_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Viva',
            'journal_id': cls.bank_journal.id,
            'payment_provider': 'viva_com',
            'viva_com_merchant_id': 'test-merchant-id',
            'viva_com_api_key': 'test-api-key',
            'viva_com_client_id': 'test-client-id',
            'viva_com_client_secret': 'test-client-secret',
            'viva_com_terminal_id': '01234543210',
        })
        payment_methods = cls.main_pos_config.payment_method_ids | viva_payment_method
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
                viva_amount = data['amount'] / 100
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

    def test_viva_app_to_app_callback_amount_paid(self):
        """The order paid by the app-to-app callback must count the Viva payment
        in its amount_paid, otherwise closing with cash rounding books the whole
        payment as a rounding loss."""
        rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding 0.05',
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
        })
        self.main_pos_config.write({
            'cash_rounding': True,
            'rounding_method': rounding.id,
            'only_round_cash_method': True,
        })
        self.main_pos_config.open_ui()
        session = self.main_pos_config.current_session_id
        viva_pm = self.main_pos_config.payment_method_ids.filtered(lambda pm: pm.payment_provider == 'viva_com')
        product = self.desk_pad.product_variant_id
        viva_session_id = 'viva-session-1'

        # The order is synced as draft while the terminal still waits for the card
        self.env['pos.order'].sync_from_ui([{
            'amount_paid': 0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 1.98,
            'pricelist_id': self.main_pos_config.pricelist_id.id,
            'session_id': session.id,
            'state': 'draft',
            'uuid': 'viva-order-uuid',
            'user_id': self.env.uid,
            'lines': [Command.create({
                'product_id': product.id,
                'price_unit': 1.98,
                'price_subtotal': 1.98,
                'price_subtotal_incl': 1.98,
                'qty': 1,
                'tax_ids': [],
            })],
            'payment_ids': [Command.create({
                'amount': 1.98,
                'payment_method_id': viva_pm.id,
                'payment_status': 'waiting',
                'viva_com_session_id': viva_session_id,
            })],
        }])
        order = self.env['pos.order'].search([('uuid', '=', 'viva-order-uuid')])
        self.assertEqual(order.state, 'draft')

        def mocked_get_transactions(self, transaction_id):
            return [{
                'StatusId': 'F',
                'MerchantTrns': f'{viva_session_id}/{self.env.company.id}',
                'Amount': 1.98,
                'CurrencyCode': self.env.company.currency_id.iso_numeric,
            }]

        with patch.object(PosPaymentMethod, '_viva_com_get_transactions', mocked_get_transactions):
            self.url_open(
                f'/pos_viva_com/{self.main_pos_config.id}/payment/viva-order-uuid'
                f'?status=success&transactionId=tx-1&clientTransactionId={viva_session_id}',
                allow_redirects=False,
            )

        order.invalidate_recordset()
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.payment_ids.payment_status, 'done')
        self.assertAlmostEqual(order.amount_paid, 1.98)

        session.action_pos_session_closing_control()
        self.assertEqual(session.state, 'closed')
        self.assertFalse(session.move_id.line_ids.filtered(lambda l: l.name == 'Rounding line'))
