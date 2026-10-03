# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac

import odoo.tests
from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.pos_paymob.controllers.main import (
    PAYMOB_HMAC_FIELDS,
    PosPaymobController,
)


@odoo.tests.tagged('post_install', '-at_install')
class TestPosPaymob(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.paymob_pm = cls.env['pos.payment.method'].sudo().create({
            'name': 'Paymob',
            'journal_id': cls.bank_journal.id,
            'use_payment_terminal': 'paymob',
            'paymob_api_key': 'test_api_key',
            'paymob_terminal_identifier': 'terminal_123',
            'paymob_hmac_secret': 'super_secret',
        })

    def test_provider_in_selection(self):
        selection = self.paymob_pm._get_payment_terminal_selection()
        self.assertIn(('paymob', 'Paymob'), selection)

    def test_base_url_test_mode(self):
        self.paymob_pm.paymob_test_mode = True
        self.assertEqual(self.paymob_pm._get_paymob_base_url(), 'https://accept-alpha.paymob.com')

    def test_base_url_egypt(self):
        self.paymob_pm.paymob_test_mode = False
        self.paymob_pm.company_id.country_id = self.env.ref('base.eg')
        self.assertEqual(self.paymob_pm._get_paymob_base_url(), 'https://accept.paymob.com')

    def test_base_url_uae(self):
        self.paymob_pm.paymob_test_mode = False
        self.paymob_pm.company_id.country_id = self.env.ref('base.ae')
        self.assertEqual(self.paymob_pm._get_paymob_base_url(), 'https://uae.paymob.com')

    def test_base_url_unsupported_country(self):
        self.paymob_pm.paymob_test_mode = False
        self.paymob_pm.company_id.country_id = self.env.ref('base.fr')
        with self.assertRaises(UserError):
            self.paymob_pm._get_paymob_base_url()

    @mute_logger('odoo.sql_db')
    def test_terminal_identifier_uniqueness(self):
        # The DB unique constraint fires on flush, so wrap in a savepoint (which
        # flushes on exit) to catch it without poisoning the test transaction.
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env['pos.payment.method'].sudo().create({
                'name': 'Paymob 2',
                'journal_id': self.bank_journal.id,
                'use_payment_terminal': 'paymob',
                'paymob_api_key': 'another_key',
                'paymob_terminal_identifier': 'terminal_123',  # already used
                'paymob_hmac_secret': 'another_secret',
            })

    def _build_transaction_obj(self):
        return {
            'amount_cents': 1000,
            'created_at': '2026-06-17T10:00:00',
            'currency': 'EGP',
            'error_occured': False,
            'has_parent_transaction': False,
            'id': 7372830,
            'integration_id': 4904870,
            'is_3d_secure': False,
            'is_auth': False,
            'is_capture': False,
            'is_refunded': False,
            'is_standalone_payment': True,
            'is_voided': False,
            'owner': 1867023,
            'pending': False,
            'success': True,
            'order': {'id': 362158785, 'merchant_order_id': '1_2_abcd-1234'},
            'source_data': {'pan': '3770', 'sub_type': 'MasterCard', 'type': 'card'},
            'data': {'message': 'Approved'},
        }

    def _sign(self, obj, secret):
        concatenated = ''.join(
            PosPaymobController._hmac_value(obj, field) for field in PAYMOB_HMAC_FIELDS
        )
        return hmac.new(secret.encode(), concatenated.encode(), hashlib.sha512).hexdigest()

    def test_hmac_valid(self):
        obj = self._build_transaction_obj()
        signature = self._sign(obj, 'super_secret')
        self.assertTrue(PosPaymobController._verify_hmac(obj, signature, 'super_secret'))

    def test_hmac_tampered_amount_fails(self):
        obj = self._build_transaction_obj()
        signature = self._sign(obj, 'super_secret')
        obj['amount_cents'] = 999999  # tamper after signing
        self.assertFalse(PosPaymobController._verify_hmac(obj, signature, 'super_secret'))

    def test_hmac_wrong_secret_fails(self):
        obj = self._build_transaction_obj()
        signature = self._sign(obj, 'super_secret')
        self.assertFalse(PosPaymobController._verify_hmac(obj, signature, 'wrong_secret'))

    def test_hmac_no_secret_fails(self):
        obj = self._build_transaction_obj()
        signature = self._sign(obj, 'super_secret')
        self.assertFalse(PosPaymobController._verify_hmac(obj, signature, False))
