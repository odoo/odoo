import base64
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged


def _jwt(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    return f"header.{payload.decode()}.signature"


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nRoEdiTokenRefresh(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write(
            {
                "l10n_ro_edi_client_id": "ro-client",
                "l10n_ro_edi_client_secret": "ro-secret",
                "l10n_ro_edi_access_token": "old-access",
                "l10n_ro_edi_refresh_token": "old-refresh",
            }
        )

    def test_the_held_refresh_token_is_spent_and_the_new_pair_stored(self):
        expiry = datetime(2030, 1, 1, 12)
        response = MagicMock(ok=True, status_code=200)
        response.json.return_value = {
            "access_token": _jwt({"exp": int(expiry.timestamp())}),
            "refresh_token": "new-refresh",
        }
        with patch.object(GuardedSession, "request", return_value=response) as sent:
            self.company._l10n_ro_edi_refresh_access_token()

        data = sent.call_args.kwargs["data"]
        self.assertEqual(
            (data["grant_type"], data["refresh_token"]),
            ("refresh_token", "old-refresh"),
        )
        self.assertEqual(
            (data["client_id"], data["client_secret"]), ("ro-client", "ro-secret")
        )
        self.assertEqual(self.company.l10n_ro_edi_refresh_token, "new-refresh")
        self.assertEqual(self.company.l10n_ro_edi_access_expiry_date, expiry.date())

    def test_without_a_refresh_token_nothing_is_sent(self):
        self.company.l10n_ro_edi_refresh_token = False

        with (
            patch.object(GuardedSession, "request") as sent,
            self.assertRaises(UserError),
        ):
            self.company._l10n_ro_edi_refresh_access_token()

        sent.assert_not_called()
