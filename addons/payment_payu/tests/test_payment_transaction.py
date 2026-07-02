# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payu import const
from odoo.addons.payment_payu.tests.common import PayuCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PayuCommon, PaymentHttpCommon):
    def test_no_item_missing_from_rendering_values(self):
        tx = self._create_transaction(flow="redirect")
        base_url = tx.provider_id.get_base_url()
        return_url = urljoin(base_url, const.PAYMENT_RETURN_ROUTE)
        webhook_url = urljoin(base_url, const.WEBHOOK_ROUTE)
        first_name, last_name = payment_utils.split_partner_name(tx.partner_name)
        payload = {
            "key": tx.provider_id.payu_key_id,
            "txnid": tx.reference,
            "amount": str(tx.amount),
            "productinfo": "Odoo Payment",
            "firstname": first_name,
            "lastname": last_name,
            "email": tx.partner_email,
            "phone": tx.partner_phone,
            "surl": return_url,
            "furl": return_url,
            "partner_webhook_success": webhook_url,
            "partner_webhook_failure": webhook_url,
            "enforce_paymethod": const.PAYMENT_METHODS_MAPPING.get(tx.payment_method_code, ""),
        }
        payload["hash"] = tx.provider_id._payu_generate_signature(payload)
        expected_rendering_values = {
            "api_url": tx.provider_id._build_request_url("_payment"),
            "url_params": payload,
        }
        self.assertDictEqual(tx._get_specific_rendering_values(None), expected_rendering_values)

    def test_extract_reference_finds_reference(self):
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference("payu", self.payment_data)
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        tx = self._create_transaction(flow="redirect")
        amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(
            amount_data, {"amount": self.amount, "currency_code": tx.currency_id.name}
        )

    def test_apply_updates_sets_provider_reference(self):
        tx = self._create_transaction(flow="redirect")
        tx._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["mihpayid"])

    def test_apply_updates_confirms_transaction(self):
        tx = self._create_transaction("redirect")
        tx._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_errors_transaction(self):
        tx = self._create_transaction("redirect")
        tx._apply_updates({"status": "failure"})
        self.assertEqual(tx.state, "error")
