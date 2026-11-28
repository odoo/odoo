from itertools import count
from unittest.mock import patch
from uuid import uuid4

from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPineLabsSelfOrderPayment(TestPointOfSaleHttpCommon):
    country_code = 'IN'
    chart_template = 'generic_coa'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pine_labs_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Pine Labs',
            'payment_method_type': 'terminal',
            'payment_provider': 'pine_labs',
            'pine_labs_merchant': 'my_merchant',
            'pine_labs_store': 'my_store',
            'pine_labs_client': 'my_client',
            'pine_labs_security_token': 'my_token',
            'pine_labs_allowed_payment_mode': 'all',
            'pine_labs_test_mode': True,
            'journal_id': cls.bank_journal.id,
            'type': 'bank',
        })
        cls.main_pos_config.write({
            'use_pricelist': False,
            'payment_method_ids': [Command.link(cls.pine_labs_payment_method.id)],
        })

    def setUp(self):
        super().setUp()
        # Fake Pine Labs server: like the real API, it approves the status of any known
        # Plutus reference, whatever transaction number or amount it was issued for.
        transactions = set()
        plutus_ids = count(1000)

        def fake_call_pine_labs(payment_method, endpoint, payload):
            if endpoint == 'UploadBilledTransaction':
                plutus_id = next(plutus_ids)
                transactions.add(plutus_id)
                return {'ResponseCode': 0, 'ResponseMessage': 'APPROVED', 'PlutusTransactionReferenceID': plutus_id}
            if endpoint == 'GetCloudBasedTxnStatus':
                plutus_id = int(payload['PlutusTransactionReferenceID'])
                if plutus_id not in transactions:
                    return {'ResponseCode': 1, 'ResponseMessage': 'INVALID PLUTUS TXN REF ID'}
                return {
                    'ResponseCode': 0,
                    'ResponseMessage': 'TXN APPROVED',
                    'PlutusTransactionReferenceID': plutus_id,
                    'TransactionData': [{'Tag': 'TransactionLogId', 'Value': f'LOG{plutus_id}'}],
                }
            raise NotImplementedError(endpoint)

        self.startPatcher(patch('odoo.addons.pos_pine_labs.models.pos_payment_method.call_pine_labs', fake_call_pine_labs))

    def _pay_on_terminal(self, order, charged_amount=None):
        """ Pay `order` on the terminal as the kiosk frontend does and return the payment values it sends. """
        amount = order['amount_total']
        transaction_number = f"{self.main_pos_config.id}/{order['uuid']}/{self.pine_labs_payment_method.id}/INR/{amount}/1"
        response = self.pine_labs_payment_method.pine_labs_make_payment_request({
            'amount': (charged_amount or amount) * 100,
            'transactionNumber': transaction_number,
            'sequenceNumber': 1,
        })
        return {
            'amount': amount,
            'payment_method_id': self.pine_labs_payment_method.id,
            'payment_ref_no': transaction_number,
            'pine_labs_plutus_transaction_ref': response['plutusTransactionReferenceID'],
            'pine_labs_signature': response['signature'],
        }

    def _is_valid(self, order, payment):
        return self.pine_labs_payment_method._is_valid_self_order_payment(self.main_pos_config, order, payment)

    def test_payment_of_the_order_is_valid(self):
        for amount in (100, 99.5):
            order = {'uuid': str(uuid4()), 'amount_total': amount}
            self.assertTrue(self._is_valid(order, self._pay_on_terminal(order)))

    def test_payment_of_another_order_is_rejected(self):
        cheap_order = {'uuid': str(uuid4()), 'amount_total': 1}
        expensive_order = {'uuid': str(uuid4()), 'amount_total': 5000}
        payment = self._pay_on_terminal(cheap_order)
        self.assertFalse(self._is_valid(expensive_order, {**payment, 'amount': 5000}))

    def test_lower_amount_charged_on_terminal_is_rejected(self):
        order = {'uuid': str(uuid4()), 'amount_total': 5000}
        self.assertFalse(self._is_valid(order, self._pay_on_terminal(order, charged_amount=1)))

    def test_missing_or_forged_signature_is_rejected(self):
        order = {'uuid': str(uuid4()), 'amount_total': 100}
        payment = self._pay_on_terminal(order)
        for signature in (None, '', 'forged', 42):
            self.assertFalse(self._is_valid(order, {**payment, 'pine_labs_signature': signature}))

    def test_reused_transaction_is_rejected(self):
        order = {'uuid': str(uuid4()), 'amount_total': 100}
        payment = self._pay_on_terminal(order)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'amount_total': 100,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
        })
        pos_order.add_payment({
            'amount': 100,
            'payment_method_id': self.pine_labs_payment_method.id,
            'pos_order_id': pos_order.id,
            'pine_labs_plutus_transaction_ref': str(payment['pine_labs_plutus_transaction_ref']),
        })
        self.assertFalse(self._is_valid(order, payment))
