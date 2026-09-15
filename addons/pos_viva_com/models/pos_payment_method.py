import logging

import requests

from odoo import _, api, fields, models, modules
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)
TIMEOUT = 10


class PosPaymentMethod(models.Model):
    _inherit = ["pos.payment.method", "mixin.integration.connected"]

    def _integration_connection_service(self):
        if self.use_payment_terminal == "viva_com":
            return "pos_viva_com", self.env._("Point of Sale: Viva.com"), "payment"
        return super()._integration_connection_service()

    _CREDENTIAL_FIELDS = {
        "viva_com_api_key": "viva_com_api_key",
        "viva_com_client_secret": "viva_com_client_secret",
        "viva_com_bearer_token": "viva_com_bearer_token",
        "viva_com_webhook_verification_key": "viva_com_webhook_verification_key",
    }

    # Viva.com
    viva_com_merchant_id = fields.Char(
        string="Merchant ID",
        help="Log into Viva.com then navigate to Settings > API Access > Access credentials",
    )
    viva_com_api_key = fields.Char(
        string="API Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
        help="Log into Viva.com then navigate to Settings > API Access > Access credentials",
    )
    viva_com_client_id = fields.Char(
        string="Client ID",
        help="Log into Viva.com then navigate to Settings > API Access > POS APIs Credentials",
    )
    viva_com_client_secret = fields.Char(
        string="Client secret",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
        help="Log into Viva.com then navigate to Settings > API Access > POS APIs Credentials",
    )
    viva_com_terminal_id = fields.Char(
        string="Terminal ID",
        help="[ID of the Viva.com terminal], e.g. 16002169",
    )
    viva_com_bearer_token = fields.Char(
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        default="Bearer Token",
        copy=True,
    )
    viva_com_webhook_verification_key = fields.Char(
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
    )
    viva_com_latest_response = fields.Json()  # not used anymore, to remove in master
    viva_com_test_mode = fields.Boolean(
        string="Test mode",
        help="Run transactions in the test environment.",
    )
    viva_com_webhook_endpoint = fields.Char(
        compute="_compute_viva_com_webhook_endpoint",
        readonly=True,
    )

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
        web_base_url = self.get_base_url()
        self.viva_com_webhook_endpoint = (
            f"{web_base_url}/pos_viva_com/notification?company_id={self.company_id.id}"
            f"&token={self.viva_com_webhook_verification_key}"
        )

    def _is_write_forbidden(self, fields):
        # Allow the modification of these fields even if a pos_session is open
        whitelisted_fields = {
            "viva_com_bearer_token",
            "viva_com_webhook_verification_key",
            "viva_com_latest_response",
        }
        return super()._is_write_forbidden(fields - whitelisted_fields)

    def _selection_payment_terminals(self):
        return super()._selection_payment_terminals() + [("viva_com", "Viva.com")]

    def _bearer_token(self, session):
        self.check_singleton()

        data = {"grant_type": "client_credentials"}
        auth = requests.auth.HTTPBasicAuth(
            self.viva_com_client_id, self.viva_com_client_secret
        )
        try:
            resp = session.post(
                f"{self._viva_com_account_get_endpoint()}/connect/token",
                auth=auth,
                data=data,
                timeout=TIMEOUT,
            )
            access_token = resp.json().get("access_token")
        except requests.exceptions.RequestException, ValueError:
            _logger.exception("Failed to call viva_com_bearer_token endpoint")
            access_token = False
        if access_token:
            self.viva_com_bearer_token = access_token
            return {"Authorization": f"Bearer {access_token}"}
        else:
            raise UserError(
                _(
                    "Unable to retrieve Viva.com Bearer Token: Please verify that the Client ID "
                    "and Client Secret are correct"
                )
            )

    def _call_viva_com(self, endpoint, action, data=None, should_retry=True):
        with self._viva_com_session(should_retry) as session:
            return self._call_viva_com_with(session, endpoint, action, data)

    def _viva_com_session(self, should_retry=True):
        options = {}
        if should_retry:
            options["max_retries"] = requests.adapters.Retry(
                total=5,
                backoff_factor=2,
                status_forcelist=[202, 500, 502, 503, 504],
            )
        return self._get_integration_connection()._egress_session(
            "pos_viva_com", **options
        )

    def _viva_com_verification_key(self):
        """Get the key Viva.com signs its webhook notifications with.

        Not called in tests: Viva.com answers only real merchant credentials.
        """
        self.check_singleton()
        if modules.module.current_test:
            return "viva_com_test"
        endpoint = self._viva_com_webhook_get_endpoint()
        try:
            response = self._get_integration_connection()._egress_request(
                "GET",
                f"{endpoint}/api/messages/config/token",
                purpose="pos_viva_com",
                auth=(self.viva_com_merchant_id, self.viva_com_api_key),
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            return response.json().get("Key")
        except requests.exceptions.RequestException, ValueError:
            _logger.exception(
                "Failed to call https://%s/api/messages/config/token endpoint", endpoint
            )
            return None

    def _call_viva_com_with(self, session, endpoint, action, data=None):
        session.headers.update(
            {"Authorization": f"Bearer {self.viva_com_bearer_token}"}
        )
        endpoint = f"{self._viva_com_api_get_endpoint()}/ecr/v1/{endpoint}"
        try:
            resp = session.request(action, endpoint, json=data, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            return {
                "error": _(
                    "There are some issues between us and Viva.com, try again later.%s)",
                    e,
                )
            }
        if resp.text and resp.json().get("detail") == "Could not validate credentials":
            session.headers.update(self._bearer_token(session))
            resp = session.request(action, endpoint, json=data, timeout=TIMEOUT)

        if resp.status_code == 200:
            if resp.text:
                return resp.json()
            return {"success": resp.status_code}
        else:
            return {
                "error": _(
                    "There are some issues between us and Viva.com, try again later. %s",
                    resp.json().get("detail"),
                )
            }

    def _notify_session_status(self, data_webhook):
        # Send a request to confirm the status of the sesions_id
        # Need wait to the status of sesions_id is updated setted in session headers; code 202

        MerchantTrns = data_webhook.get("MerchantTrns")
        if not MerchantTrns:
            return self._send_notification(
                {
                    "error": _(
                        "Your transaction with Viva.com failed. Please try again later."
                    )
                }
            )
        session_id, pos_session_id = MerchantTrns.split(
            "/"
        )  # Split to retrieve pos_sessions_id
        endpoint = f"sessions/{session_id}"
        data = self._call_viva_com(endpoint, "get")

        if data.get("success"):
            data.update(
                {"pos_session_id": pos_session_id, "data_webhook": data_webhook}
            )
            self._send_notification(data)
        else:
            self._send_notification(
                {
                    "error": _(
                        "There are some issues between us and Viva.com, try again later. %s",
                        data.get("detail"),
                    )
                }
            )

    def _send_notification(self, data):
        # Send a notification to the point of sale channel to indicate that the transaction are finish
        pos_session_sudo = self.env["pos.session"].browse(
            int(data.get("pos_session_id", False))
        )
        if pos_session_sudo:
            pos_session_sudo.config_id._notify(
                "VIVA_COM_LATEST_RESPONSE",
                {
                    "config_id": pos_session_sudo.config_id.id,
                    "session_id": data.get("sessionId"),
                    "success": data.get("success", False),
                    "transaction_id": data.get("transactionId"),
                    "card_type": data.get("applicationLabel"),
                    "cardholder_name": data.get("FullName", ""),
                },
            )

    def _load_pos_data_fields(self, config):
        return [*super()._load_pos_data_fields(config), "viva_com_terminal_id"]

    def viva_com_send_payment_request(self, data):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _(
                    "Only 'group_pos_user' are allowed to send a Viva.com payment request"
                )
            )

        endpoint = "transactions:sale"
        return self._call_viva_com(endpoint, "post", data)

    def viva_com_send_refund_request(self, data):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _("Only 'group_pos_user' are allowed to send a Viva.com refund request")
            )

        endpoint = (
            "transactions:refund"
            if data.get("parentSessionId")
            else "transactions:unreferenced-refund"
        )
        return self._call_viva_com(endpoint, "post", data)

    def viva_com_send_payment_cancel(self, data):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _("Only 'group_pos_user' are allowed to cancel a Viva.com payment")
            )

        session_id = data.get("sessionId")
        cash_register_id = data.get("cashRegisterId")
        endpoint = f"sessions/{session_id}?cashRegisterId={cash_register_id}"
        return self._call_viva_com(endpoint, "delete")

    def viva_com_get_payment_status(self, session_id):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _(
                    "Only 'group_pos_user' are allowed to get the payment status from Viva.com"
                )
            )

        endpoint = f"sessions/{session_id}"
        return self._call_viva_com(endpoint, "get", should_retry=False)

    def write(self, vals):
        record = super().write(vals)

        if vals.get("viva_com_merchant_id") and vals.get("viva_com_api_key"):
            self.viva_com_webhook_verification_key = self._viva_com_verification_key()
            if not self.viva_com_webhook_verification_key:
                raise UserError(
                    _(
                        "Can't update payment method. Please check the data and update it."
                    )
                )

        return record

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.viva_com_merchant_id and record.viva_com_api_key:
                record.viva_com_webhook_verification_key = (
                    record._viva_com_verification_key()
                )
                if not record.viva_com_webhook_verification_key:
                    raise UserError(
                        _(
                            "Can't create payment method. Please check the data and update it."
                        )
                    )

        return records

    def get_latest_viva_com_status(self):
        # Not used anymore, to remove in master
        return {"error": "Your POS is out of date, please refresh the page."}

    @api.constrains("use_payment_terminal")
    def _check_viva_com_credentials(self):
        for record in self:
            if record.use_payment_terminal == "viva_com" and not all(
                record[f]
                for f in [
                    "viva_com_merchant_id",
                    "viva_com_api_key",
                    "viva_com_client_id",
                    "viva_com_client_secret",
                    "viva_com_terminal_id",
                ]
            ):
                raise UserError(
                    _("It is essential to provide API key for the use of Viva.com")
                )
