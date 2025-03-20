# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo.addons.pos_viva_com.models.pos_payment_method import PosPaymentMethod
from unittest.mock import patch
from odoo import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestVivaComHttpCommon(TestPointOfSaleDataHttpCommon):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

        viva_payment_method = self.env['pos.payment.method'].create({
            'name': 'Viva',
            'journal_id': self.bank_journal.id,
            'use_payment_terminal': 'viva_com',
            'viva_com_merchant_id': 'test-merchant-id',
            'viva_com_api_key': 'test-api-key',
            'viva_com_client_id': 'test-client-id',
            'viva_com_client_secret': 'test-client-secret',
            'viva_com_terminal_id': '01234543210',
        })
        self.pos_config.write({'payment_method_ids': [(4, viva_payment_method.id)]})

    def test_vw_request_data(self):
        def mocked_call_viva_com_check_post_data(self, endpoint, action, data=None):
            if not isinstance(data['amount'], int):
                raise TypeError(f"Expected 'amount' to be an integer, but got {data['amount']}.")
            if not data['terminalId'] == '01234543210':
                raise Exception(f"Expected 'terminalId' to be 01234543210, but got {data['terminalId']}")
            return {}

        with patch.object(PosPaymentMethod, '_call_viva_com', mocked_call_viva_com_check_post_data):
            self.start_pos_tour("VivaComTour", login="accountman")
