import logging
from uuid import uuid4

import requests

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    viva_com_merchant_id = fields.Char(
        string="Merchant ID", help="Log into Viva.com then navigate to Settings > API Access > Access credentials",
    )
    viva_com_api_key = fields.Char(
        string="API Key", help="Log into Viva.com then navigate to Settings > API Access > Access credentials", groups="pos_payment_method.group_payment_method_admin",
    )
    viva_com_client_id = fields.Char(
        string="Client ID", help="Log into Viva.com then navigate to Settings > API Access > POS APIs Credentials",
    )
    viva_com_client_secret = fields.Char(
        string="Client Secret", help="Log into Viva.com then navigate to Settings > API Access > POS APIs Credentials", groups="pos_payment_method.group_payment_method_admin",
    )
    viva_com_terminal_id = fields.Char(string="Terminal ID", help="[ID of the Viva.com terminal], e.g. 16002169")
    viva_com_bearer_token = fields.Char(default="Bearer Token")
    viva_com_webhook_verification_key = fields.Char(groups="pos_payment_method.group_payment_method_admin")
    viva_com_test_mode = fields.Boolean(string="Test mode", help="Run transactions in the test environment.")
    viva_com_webhook_endpoint = fields.Char(string="Webhook Endpoint", compute="_compute_viva_com_webhook_endpoint", readonly=True)

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("viva_com", "Viva.com")]

    def _viva_com_account_get_endpoint(self):
        if self.viva_com_test_mode:
            return "https://demo-accounts.vivapayments.com"
        return "https://accounts.vivapayments.com"

    def _viva_com_api_get_endpoint(self):
        if self.viva_com_test_mode:
            return "https://demo-api.vivapayments.com"
        return "https://api.vivapayments.com"

    def _viva_com_webhook_get_endpoint(self):
        if self.viva_com_test_mode:
            return "https://demo.vivapayments.com"
        return "https://www.vivapayments.com"

    def _compute_viva_com_webhook_endpoint(self):
        for record in self:
            web_base_url = record.get_base_url()
            record.viva_com_webhook_endpoint = (
                f"{web_base_url}/pos_viva_com/notification"
                f"?token={record.viva_com_webhook_verification_key}"
            )

    def _refresh_viva_bearer_token(self, session: requests.Session):
        self.ensure_one()

        data = {"grant_type": "client_credentials"}
        auth = requests.auth.HTTPBasicAuth(self.viva_com_client_id, self.sudo().viva_com_client_secret)
        try:
            resp = session.post(f"{self._viva_com_account_get_endpoint()}/connect/token", auth=auth, data=data, timeout=TIMEOUT_SECONDS)
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call viva_com_bearer_token endpoint")
            return {}

        access_token = resp.json().get("access_token")
        if access_token:
            self.sudo().write({"viva_com_bearer_token": access_token})
            return {"Authorization": f"Bearer {access_token}"}

        raise UserError(_(
            "Unable to retrieve Viva.com Bearer Token: Please verify that the Client ID "
            "and Client Secret are correct",
        ))

    def _call_viva_com(self, endpoint: str, action: str, data=None):
        session = get_viva_com_session()
        session.headers.update({"Authorization": f"Bearer {self.sudo().viva_com_bearer_token}"})
        endpoint = f"{self._viva_com_api_get_endpoint()}/ecr/v1/{endpoint}"
        try:
            resp = session.request(action, endpoint, json=data, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 401:
                session.headers.update(self._refresh_viva_bearer_token(session))
                resp = session.request(action, endpoint, json=data, timeout=TIMEOUT_SECONDS)
        except requests.exceptions.RequestException as e:
            return {"error": _("There are some issues between us and Viva.com, try again later. %s)", e)}

        if resp.ok:
            if resp.text:
                return resp.json()
            return {"success": resp.status_code}

        return {"error": resp.json().get("detail")}

    def _make_viva_transaction_data(self, amount: float, currency, extra_args: dict, original_transaction_id: str | None = None):
        transaction_id = f"Odoo-{uuid4().hex}"
        data = {
            "sessionId": transaction_id,
            "terminalId": self.viva_com_terminal_id,
            "cashRegisterId": f"Odoo-{self.id}",
            "amount": self._convert_amount_to_units(amount, currency),
            "currencyCode": currency.iso_numeric,
            "merchantReference": transaction_id,
            "tipAmount": 0,
        }

        if original_transaction_id:
            data["parentSessionId"] = original_transaction_id

        partner = self.env["res.partner"].browse(extra_args.get("partner_id"))
        if partner.exists():
            data["customerTrns"] = f"{partner.name} - {partner.email}"

        return transaction_id, data

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "viva_com":
            return super()._start_payment(amount, currency, extra_args)
        transaction_id, data = self._make_viva_transaction_data(amount, currency, extra_args)
        result = self._call_viva_com("transactions:sale", "post", data)
        if not result.get("success"):
            return {"error": result["error"]}
        return {"transaction_id": transaction_id}

    def _start_refund(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "viva_com":
            return super()._start_refund(amount, currency, extra_args)
        transaction_id, data = self._make_viva_transaction_data(amount, currency, extra_args)
        result = self._call_viva_com("transactions:unreferenced-refund", "post", data)
        if not result.get("success"):
            return {"error": result["error"]}
        return {"transaction_id": transaction_id}

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict):
        if self.payment_provider != "viva_com":
            return super()._start_reversal(amount, currency, original_transaction_id, extra_args)
        transaction_id, data = self._make_viva_transaction_data(amount, currency, extra_args, original_transaction_id)
        result = self._call_viva_com("transactions:refund", "post", data)
        if not result.get("success"):
            return {"error": result["error"]}
        return {"transaction_id": transaction_id}

    def _cancel_transaction(self, transaction_id: str):
        if self.payment_provider != "viva_com":
            return super()._cancel_transaction(transaction_id)
        endpoint = f"sessions/{transaction_id}?cashRegisterId=Odoo-{self.id}"
        result = self._call_viva_com(endpoint, "delete")
        if not result.get("success"):
            return {"error": result["error"]}
        return {}

    def _get_transaction_status(self, transaction_id: str):
        if self.payment_provider != "viva_com":
            return super()._get_transaction_status(transaction_id)

        response = self._call_viva_com(f"sessions/{transaction_id}", "get")
        if "error" in response:
            return {"status": "unknown", "error": response["error"]}
        if "success" not in response:
            return {"status": "pending"}
        if not response["success"]:
            return {"status": "failed", "error": response["message"]}
        return {
            "status": "paid",
            "card_type": response["cardType"],
            "card_brand": response["applicationLabel"],
            "card_no": response["primaryAccountNumberMasked"],
        }

    def write(self, vals):
        record = super().write(vals)

        if vals.get("viva_com_merchant_id") and vals.get("viva_com_api_key"):
            self.viva_com_webhook_verification_key = get_verification_key(
                self._viva_com_webhook_get_endpoint(),
                self.viva_com_merchant_id,
                self.viva_com_api_key,
            )
            if not self.viva_com_webhook_verification_key:
                raise UserError(_("Can't update payment method. Please check the data and update it."))

        return record

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.viva_com_merchant_id and record.viva_com_api_key:
                record.viva_com_webhook_verification_key = get_verification_key(
                    record._viva_com_webhook_get_endpoint(),
                    record.viva_com_merchant_id,
                    record.viva_com_api_key,
                )
                if not record.viva_com_webhook_verification_key:
                    raise UserError(_("Can't create payment method. Please check the data and update it."))

        return records


def get_viva_com_session():
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
    )))
    return session


def get_verification_key(endpoint: str, viva_com_merchant_id: str, viva_com_api_key: str):
    """Get a key to configure the webhook.
    This key need to be the response when we receive a notification.
    Do not execute this query in test mode.

    :param endpoint: The endpoint to get the verification key from
    :param viva_com_merchant_id: The merchant ID
    :param viva_com_api_key: The API
    :return: The verification key
    """
    if modules.module.current_test:
        return "viva_com_test"

    try:
        response = requests.get(
            f"{endpoint}/api/messages/config/token",
            auth=(viva_com_merchant_id, viva_com_api_key),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("Key")
    except requests.exceptions.RequestException:
        _logger.exception("Failed to call https://%s/api/messages/config/token endpoint", endpoint)
