# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from uuid import uuid4

import odoo.tests
from odoo import Command, fields
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_viva_com.models.pos_payment_method import PosPaymentMethod


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKioskVivaCom(SelfOrderCommonTest):

    def setUp(self):
        super().setUp()
        self.viva_payment_method = self.env['pos.payment.method'].create({
            'name': 'Viva',
            'journal_id': self.bank_journal.id,
            'use_payment_terminal': 'viva_com',
            'viva_com_merchant_id': 'test-merchant-id',
            'viva_com_api_key': 'test-api-key',
            'viva_com_client_id': 'test-client-id',
            'viva_com_client_secret': 'test-client-secret',
            'viva_com_terminal_id': '01234543210',
        })
        self.pos_config.write({
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [Command.clear()],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'payment_method_ids': [Command.set(self.viva_payment_method.ids)],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_session = self.pos_config.current_session_id
        self.pos_session.set_opening_control(0, "")
        self.viva_session = {}

        # Fake Viva.com: the session started on the terminal is paid in full
        def call_viva_com(payment_method, endpoint, action, data=None, should_retry=True):
            if endpoint == 'transactions:sale' and action == 'post':
                self.viva_session.update(id=data['sessionId'], amount=data['amount'])
                return {}
            if endpoint == f"sessions/{self.viva_session.get('id')}" and action == 'get':
                return {
                    'success': True,
                    'sessionId': self.viva_session['id'],
                    'transactionId': 'test-transaction-id',
                }
            raise AssertionError(f"Unexpected Viva.com request: {action} {endpoint}")

        def get_transactions(payment_method, transaction_id):
            return [{
                'StatusId': 'F',
                'MerchantTrns': f"{self.viva_session['id']}/{self.pos_session.id}",
                'Amount': self.viva_session['amount'] / 100,
                'CurrencyCode': self.pos_config.currency_id.iso_numeric,
            }]

        self.startPatcher(patch.object(PosPaymentMethod, '_call_viva_com', call_viva_com))
        self.startPatcher(patch.object(PosPaymentMethod, '_viva_com_get_transactions', get_transactions))

    def test_kiosk_viva_com_payment(self):
        self.start_tour(self.pos_config._get_self_order_route(), "kiosk_viva_com_payment")

        order = self.pos_session.order_ids
        self.assertRecordValues(order, [{'state': 'paid', 'amount_total': 2.53}])
        self.assertEqual(self.viva_session['amount'], 253)
        self.assertRecordValues(order.payment_ids, [{
            'payment_method_id': self.viva_payment_method.id,
            'amount': 2.53,
            'transaction_id': 'test-transaction-id',
            'viva_com_session_id': self.viva_session['id'],
        }])

    def test_kiosk_viva_com_webhook_without_payment_line(self):
        # What the kiosk leaves on the server before paying: a draft order without payment line
        order = self.env['pos.order'].create({
            'session_id': self.pos_session.id,
            'company_id': self.env.company.id,
            'date_order': fields.Datetime.now(),
            'amount_total': 2.53,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [Command.create({
                'product_id': self.cola.id,
                'qty': 1,
                'price_unit': 2.53,
                'price_subtotal': 2.53,
                'price_subtotal_incl': 2.53,
            })],
        })
        self.viva_session.update(id=f"{order.uuid} - {uuid4()}", amount=253)

        send_notification = self.startPatcher(patch.object(PosPaymentMethod, '_send_notification', autospec=True))

        self.viva_payment_method.sudo()._retrieve_session_id({
            'MerchantTrns': f"{self.viva_session['id']}/{self.pos_session.id}",
        })

        send_notification.assert_called_once()
        notification = send_notification.call_args.args[1]
        self.assertTrue(notification.get('success'))
        self.assertEqual(notification.get('sessionId'), self.viva_session['id'])
