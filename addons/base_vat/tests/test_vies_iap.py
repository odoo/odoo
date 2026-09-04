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
        # Test methods in this class share one cursor/transaction (savepoint
        # rollback doesn't clear it), so isolate the per-transaction VIES
        # cache between tests.
        self.env.cr.cache.pop('base_vat_vies_status', None)
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

    def test_vies_valid_computed_on_create(self):
        """create() must compute vies_valid too, not only write(): the web
        form relies on this (its onchange already sends vies_valid inside
        the create() vals, so it never depended on the recompute queue),
        but any create() coming from code (API, connectors, controllers)
        has no onchange step and only sets vat/country_id.
        """
        self.mock_return_status = "valid"
        partner = self.env['res.partner'].create({
            'name': 'Created with vat',
            'country_id': self.env.ref('base.be').id,
            'vat': self.RANDOM_VAT,
        })
        self.assertTrue(partner.vies_valid)

    def test_vies_valid_skipped_on_create_import_file(self):
        """Bulk CSV/Excel imports (import_file context) keep skipping it,
        same as write() already does.
        """
        self.mock_return_status = "valid"
        partner = self.env['res.partner'].with_context(import_file=True).create({
            'name': 'Created with vat via import',
            'country_id': self.env.ref('base.be').id,
            'vat': self.RANDOM_VAT,
        })
        self.assertFalse(partner.vies_valid)
        self.mock_post.assert_not_called()

    def test_vies_valid_no_duplicate_iap_call_on_create_company(self):
        """create_company() copies the contact's already-validated VAT to
        the new parent company; restoring the recompute on create() must
        not query IAP a second time for that same VAT number (the exact
        scenario a18b23e7e1 fixed by disabling create()'s recompute
        entirely - this cache achieves the same result without doing so).
        """
        self.mock_return_status = "valid"
        self.partner.write({'company_name': 'My Company'})
        self.partner.vat = self.RANDOM_VAT
        self.assertTrue(self.partner.vies_valid)
        self.mock_post.assert_called_once()

        self.partner.create_company()
        self.assertTrue(self.partner.parent_id.vies_valid)
        self.mock_post.assert_called_once()

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
