# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from datetime import datetime
from freezegun import freeze_time

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from unittest.mock import patch

CALL_API_METHOD = 'odoo.addons.ecpay_invoice.utils.EcPayAPI.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTWITestEdiPosOrder(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('tw')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'l10n_tw_edi_ecpay_api_url': 'https://einvoice-stage.ecpay.com.tw/B2CInvoice',
            'l10n_tw_edi_ecpay_merchant_id': '2000132',
            'l10n_tw_edi_ecpay_hashkey': 'ejCk326UnaZWKisg',
            'l10n_tw_edi_ecpay_hashIV': 'q9jcZX8Ib9LM8wYk',
            'l10n_tw_edi_ecpay_seller_identifier': '12345678',
            'phone': '+8860912345678',
        })
        cls.partner_a.write({
            'vat': '21313148',
            'phone': '+8860987654321',
            'contact_address': 'test address',
        })

        # We can reuse this invoice for the flow tests.
        cls.basic_invoice = cls.init_invoice(
            'out_invoice', partner=cls.partner_a, products=cls.product_a,
        )
        cls.basic_invoice.action_post()

        cls.fakenow = datetime(2024, 9, 22, 15, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------
