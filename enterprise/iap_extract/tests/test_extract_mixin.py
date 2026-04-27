# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.base.models.ir_cron import ir_cron
from odoo.addons.iap.models.iap_account import IapAccount
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap_extract.models.extract_mixin import ExtractMixin
from odoo.addons.partner_autocomplete.models.iap_autocomplete_api import IapAutocompleteEnrichAPI
from odoo.sql_db import Cursor
from odoo.tests import common


class TestExtractMixin(common.TransactionCase):
    def parse_success_response(self):
        return {'status': 'success', 'document_token': 'some_token'}

    def parse_processing_response(self):
        return {'status': 'processing'}

    def parse_credit_error_response(self):
        return {'status': 'error_no_credit'}

    def validate_success_response(self):
        return {'status': 'success'}

    @classmethod
    def setUpClass(cls):
        super(TestExtractMixin, cls).setUpClass()

        # Freeze time to avoid nondeterminism in the tests.
        # The value of the date and the creation date are checked to know whether we should fill date fields or not.
        # When tests run at around midnight, it can happen that the creation date and the default date don't
        # match, e.g. when one is set at 23:59:59 and the other one at 00:00:00.
        # This issue can of course also occur under normal utilization, but it should be very rare and with negligible consequences.
        cls.startClassPatcher(freeze_time('2019-04-15'))
        cls.env.cr._now = datetime.now()

        # Avoid passing on the iap.account's `get` method to avoid the cr.commit breaking the test transaction.
        partner_autocomplete = cls.env.ref('partner_autocomplete.iap_service_partner_autocomplete')
        invoice_ocr = cls.env.ref('iap_extract.iap_service_ocr')
        cls.env['iap.account'].create([
            {
                'service_id': partner_autocomplete.id,
            },
            {
                'service_id': invoice_ocr.id,
                'account_token': 'test_token',
            }
        ])

    @contextmanager
    def _mock_iap_extract(self, extract_response=None, partner_autocomplete_response=None, assert_params=None):
        def _trigger(self, *args, **kwargs):
            # A call to _trigger will directly run the cron
            self.method_direct_trigger()

        def _mock_autocomplete(*args, **kwargs):
            return partner_autocomplete_response or {}

        def _mock_iap_jsonrpc(*args, **kwargs):
            if assert_params is not None:
                self.assertDictEqual(kwargs['params'], assert_params)
            return extract_response or {}

        def _mock_try_to_check_ocr_status(self, *args, **kwargs):
            """ Remove the `try ... except Exception` of _try_to_check_ocr_status so that it doesn't hide errors"""
            self._check_ocr_status()

        # The module iap is committing the transaction when creating an IAP account, we mock it to avoid that
        with patch.object(iap_tools, 'iap_jsonrpc', side_effect=_mock_iap_jsonrpc),  \
                patch.object(ExtractMixin, '_try_to_check_ocr_status', side_effect=_mock_try_to_check_ocr_status, autospec=True), \
                patch.object(IapAutocompleteEnrichAPI, '_contact_iap', side_effect=_mock_autocomplete), \
                patch.object(IapAccount, 'get_credits', side_effect=lambda *args, **kwargs: 1), \
                patch.object(Cursor, 'commit', side_effect=lambda *args, **kwargs: None), \
                patch.object(ir_cron, '_trigger', side_effect=_trigger, autospec=True):
            yield
