from unittest.mock import patch
from freezegun import freeze_time

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from odoo.tools import mute_logger
from datetime import date


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGSTStatusFeature(TransactionCase):
    def setUp(self):
        self.partner1 = self.env["res.partner"].create(
            {"name": "Active GSTIN", "vat": "36AAACM4154G1ZO"}
        )
        self.partner2 = self.env["res.partner"].create(
            {"name": "Cancelled GSTIN", "vat": "19AABCT1332L2ZD"}
        )
        self.partner3 = self.env["res.partner"].create(
            {"name": "Invalid GSTIN", "vat": "19AACCT6304M1ZB"}
        )
        self.partner4 = self.env["res.partner"].create(
            {"name": "No Records GSTIN", "vat": "19AACCT6304M1DB"}
        )
        self.partner5 = self.env["res.partner"].create(
            {
                "name": "Partner Vat Reset",
                "vat": "36AAACM4154G1ZO",
                "country_id": self.env.ref('base.in').id,
                "l10n_in_gstin_verified_status": "active",
                "l10n_in_gstin_verified_date": "2024-06-01",
            }
        )
        self.mock_responses = {
            "active": {
                "data": {"sts": "Active"}
            },
            "cancelled": {
                "data": {"sts": "Cancelled"}
            },
            "invalid": {
                "error": [{"code": "SWEB_9035", "message": "Invalid GSTIN / UID"}],
            },
            "no_records": {
                "error": [{"code": "FO8000", "message": "No records found for the provided GSTIN."}],
            },
        }

    @freeze_time('2024-05-20')
    @mute_logger('odoo.addons.l10n_in_gstin_status.models.res_partner')
    def check_gstin_status(self, partner, expected_status, mock_response, raises_exception=False):
        with patch("odoo.addons.l10n_in.models.iap_account.jsonrpc") as mock_jsonrpc:
            mock_jsonrpc.return_value = mock_response
            if raises_exception:
                with self.assertRaises(UserError):
                    partner.action_l10n_in_verify_gstin_status()
            else:
                partner.action_l10n_in_verify_gstin_status()
                self.assertEqual(partner.l10n_in_gstin_verified_status, expected_status)
                self.assertEqual(partner.l10n_in_gstin_verified_date, date(2024, 5, 20))

    def test_gstin_status(self):
        """Test GSTIN status for various cases"""
        self.check_gstin_status(
            self.partner1,
            expected_status=True,
            mock_response=self.mock_responses["active"]
        )
        self.check_gstin_status(
            self.partner2,
            expected_status=False,
            mock_response=self.mock_responses["cancelled"]
        )
        self.check_gstin_status(
            self.partner3,
            expected_status=False,
            raises_exception=True,
            mock_response=self.mock_responses["invalid"],
        )
        self.check_gstin_status(
            self.partner4,
            expected_status=False,
            raises_exception=True,
            mock_response=self.mock_responses["no_records"],
        )
