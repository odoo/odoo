# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_authorize import const
from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(AuthorizeCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_authorize.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)

        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.webhook_authcapture_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_authorize.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)

        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self.opener.headers["X-ANET-Signature"] = (
                f"sha512={self.webhook_authcapture_data_signature}"
            )
            self._make_json_request(url, data=self.webhook_authcapture_data)
            self.opener.headers.pop("X-ANET-Signature")

            self.assertEqual(
                signature_check_mock.call_args[0][0], self.webhook_authcapture_data_signature
            )
