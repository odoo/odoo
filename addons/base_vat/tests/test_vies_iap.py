import logging
import requests

from unittest.mock import patch, Mock

from odoo.exceptions import UserError
from odoo.tools import hash_sign

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestViesIAP(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.fr')
        cls.env.company.vat_check_vies = True
        cls.RANDOM_VAT = 'BE0477472701'

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'GAGA',
        })
        self.original_post = requests.post
        self.mock_return_status = None
        patcher = patch('requests.post', side_effect=self.patched_requests_post)
        self.mock_post = patcher.start()
        self.addCleanup(patcher.stop)

    def patched_requests_post(self, *args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        if args[0].endswith("/api/vies/1/check_validity"):
            mock_response.json.return_value = {"status": self.mock_return_status}
            return mock_response
        elif args[0].endswith("/api/vies/1/check_update"):
            mock_response.json.return_value = {self.RANDOM_VAT: 'valid'}
            return mock_response
        raise Exception("Shouldn't reach here")

    def test_vies_iap_invalid_vat(self):
        # Don't even call IAP if the local check doesn't pass
        with self.assertRaisesRegex(UserError, 'does not seem to be valid'):
            self.partner.vat = 'BE1234'

    def test_vies_iap_valid_vat(self):
        self.mock_return_status = "valid"
        with (
            self.assertLogs('odoo.addons.base_vat.models.res_partner', logging.INFO) as log_catcher,
        ):
            self.partner.vat = self.RANDOM_VAT
            self.partner.flush_recordset()  # trigger computes
        self.assertTrue(self.partner.vies_valid)
        self.assertIn('VIES status updated to valid for partner', log_catcher.output[-1])
        self.assertIn('The Intra-Community validity has been updated to: valid.', self.partner.message_ids[0].body)

    def test_vies_iap_unassigned_vat(self):
        self.mock_return_status = "unassigned"
        with (
            self.assertLogs('odoo.addons.base_vat.models.res_partner', logging.INFO) as log_catcher,
        ):
            self.partner.vat = self.RANDOM_VAT
            self.partner.flush_recordset()  # trigger computes
        self.assertFalse(self.partner.vies_valid)
        self.assertIn('VIES status updated to unassigned for partner', log_catcher.output[-1])
        self.assertIn('The Intra-Community validity has been updated to: unassigned.', self.partner.message_ids[0].body)

    def test_vies_iap_pending_vat(self):
        """Check test_vies_iap_controller and test_vies_iap_cron"""
        self.mock_return_status = "pending"
        with (
            self.assertLogs('odoo.addons.base_vat.models.res_partner', logging.INFO) as log_catcher,
        ):
            self.partner.vat = self.RANDOM_VAT
            self.partner.flush_recordset()  # trigger computes
        self.assertFalse(self.partner.vies_valid)
        self.assertIn('VIES status updated to pending for partner', log_catcher.output[-1])
        self.assertIn('The VIES check is pending. The status will be updated soon.', self.partner.message_ids[0].body)

    def test_vies_iap_fault_vat(self):
        self.mock_return_status = "fault"
        with (
            self.assertLogs('odoo.addons.base_vat.models.res_partner', logging.INFO) as log_catcher,
        ):
            self.partner.vat = self.RANDOM_VAT
            self.partner.flush_recordset()  # trigger computes
        self.assertFalse(self.partner.vies_valid)
        self.assertIn('VIES status updated to fault for partner', log_catcher.output[-1])
        self.assertIn('The VIES check failed. Please check the Tax ID manually.', self.partner.message_ids[0].body)

    def test_vies_iap_controller(self):
        """
        If IAP doesn't have the lookup status yet, it returns pending and will retry later.
        Upon having a new lookup status, it will call the Odoo client db with the updated status
        """
        self.mock_return_status = "pending"
        self.partner.vat = self.RANDOM_VAT
        self.partner.flush_recordset()  # trigger computes
        self.assertFalse(self.partner.vies_valid)

        # At this point, the Odoo db is passively waiting for an update coming from IAP via the webhook
        # Let's simulate IAP calling back the db
        # First with an invalid webhook_token
        self.authenticate(None, None)
        webhook_token_incorrect = hash_sign(self.env, 'fakeee', 'randomm', expiration_hours=24)
        with (
            self.assertLogs('odoo.addons.base_vat.controllers.webhook', level="WARNING") as log_catcher,
        ):
            self.url_open(
                '/base_vat/1/webhook_update_vies',
                data={
                    'webhook_token': webhook_token_incorrect,
                    'status': 'valid',
                },
            )
        self.assertIn('VIES update failed: webhook_token does not match.', log_catcher.output[-1])
        self.assertFalse(self.partner.vies_valid)

        # Now with the valid webhook token
        webhook_token_correct = hash_sign(self.env, 'vies_check', self.RANDOM_VAT, expiration_hours=24)
        self.url_open(
            '/base_vat/1/webhook_update_vies',
            data={
                'webhook_token': webhook_token_correct,
                'status': 'valid',
            },
        )
        self.assertTrue(self.partner.vies_valid)

    def test_vies_iap_cron(self):
        """
        Same as previous test, but for cases where the Odoo client db is unreachable (invalid
        webhook URL, firewall, localhost, ...). In those cases, a cron runs and calls IAP itself
        (pull updates from IAP instead of letting IAP push the updates).
        """
        self.mock_return_status = "pending"
        self.partner.vat = self.RANDOM_VAT
        self.partner.flush_recordset()  # trigger computes
        self.assertFalse(self.partner.vies_valid)

        self.env.ref('base_vat.vies_iap_check_update').method_direct_trigger()
        self.assertTrue(self.partner.vies_valid)
