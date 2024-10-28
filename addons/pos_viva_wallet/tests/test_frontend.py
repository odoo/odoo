# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_viva_wallet.models.pos_payment_method import PosPaymentMethod
from unittest.mock import patch
from odoo import Command
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestVivaWalletHttpCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create viva wallet payment method
        viva_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Viva',
            'journal_id': cls.bank_journal.id,
            'use_payment_terminal': 'viva_wallet',
            'viva_wallet_merchant_id': 'test-merchant-id',
            'viva_wallet_api_key': 'test-api-key',
            'viva_wallet_client_id': 'test-client-id',
            'viva_wallet_client_secret': 'test-client-secret',
            'viva_wallet_terminal_id': '01234543210',
        })
        payment_methods = cls.main_pos_config.payment_method_ids | viva_payment_method
        cls.main_pos_config.write({'payment_method_ids': [Command.set(payment_methods.ids)]})

    def test_vw_request_data(self):
        def mocked_call_viva_wallet_check_post_data(self, endpoint, action, data=None):
            if not isinstance(data['amount'], int):
                raise TypeError(f"Expected 'amount' to be an integer, but got {data['amount']}.")
            if not data['terminalId'] == '01234543210':
                raise Exception(f"Expected 'terminalId' to be 01234543210, but got {data['terminalId']}")
            return {}

        with patch.object(PosPaymentMethod, '_call_viva_wallet', mocked_call_viva_wallet_check_post_data):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'VivaWalletTour', login="accountman")
