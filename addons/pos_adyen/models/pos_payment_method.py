import json
import logging
import pprint
from urllib.parse import parse_qs

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.http import request
from odoo.tools import consteq, hmac

from odoo.addons.integration.tools.admission import Acknowledged

_logger = logging.getLogger(__name__)

UNPREDICTABLE_ADYEN_DATA = object()  # sentinel


class PosPaymentMethod(models.Model):
    _name = "pos.payment.method"
    _inherit = ["pos.payment.method", "mixin.integration.connected"]

    @api.model
    def _receiver_for_adyen_terminal(self, **path_args):
        data = request.get_json_data()
        if not isinstance(data, dict) or not data.get("SaleToPOIResponse"):
            # Not a response to a sales request.
            raise Acknowledged.json(None)
        msg_header = data["SaleToPOIResponse"].get("MessageHeader") or {}
        if (
            msg_header.get("ProtocolVersion") != "3.0"
            or msg_header.get("MessageClass") != "Service"
            or msg_header.get("MessageType") != "Response"
            or msg_header.get("MessageCategory") != "Payment"
            or not msg_header.get("POIID")
        ):
            _logger.warning("Received an unexpected Adyen notification")
            raise Acknowledged.json(None)
        terminal_identifier = msg_header["POIID"]
        method = self.sudo().search(
            [("adyen_terminal_identifier", "=", terminal_identifier)], limit=1
        )
        if not method:
            _logger.warning(
                "Received an Adyen event notification for a terminal not registered "
                "in Odoo: %s",
                terminal_identifier,
            )
            request.env["integration.exchange"]._record_unknown_caller(
                self._name,
                f"Adyen terminal {terminal_identifier}"[:64],
                request.httprequest.remote_addr,
                user_agent=request.httprequest.headers.get("User-Agent"),
                status_code=200,
            )
            raise Acknowledged.json(None)
        return method, {"data": data}

    def _inbound_gate_owner(self):
        return self, f"{self.name} notifications", None

    @staticmethod
    def _adyen_additional_data(adyen_additional_response, data_key):
        values = parse_qs(adyen_additional_response).get(data_key)
        return values[0] if values and len(values) == 1 else None

    def _verify_inbound_request(self, headers, body):
        if self.use_payment_terminal != "adyen":
            return super()._verify_inbound_request(headers, body)
        data = request.get_json_data()
        try:
            response = data["SaleToPOIResponse"]["PaymentResponse"]
            msg_header = data["SaleToPOIResponse"]["MessageHeader"]
            pos_hmac = self._adyen_additional_data(
                response["Response"]["AdditionalResponse"], "metadata.pos_hmac"
            )
            expected = self._get_hmac(
                msg_header["SaleID"],
                msg_header["ServiceID"],
                msg_header["POIID"],
                response["SaleData"]["SaleTransactionID"]["TransactionID"],
            )
        except KeyError, TypeError:
            return False
        return bool(pos_hmac) and consteq(pos_hmac, expected)

    def _integration_connection_service(self):
        if self.use_payment_terminal == "adyen":
            return "pos_adyen", self.env._("Point of Sale: Adyen"), "payment"
        return super()._integration_connection_service()

    _CREDENTIAL_FIELDS = {
        "adyen_api_key": "adyen_api_key",
    }

    def _selection_payment_terminals(self):
        return super()._selection_payment_terminals() + [("adyen", "Adyen")]

    # Adyen
    adyen_api_key = fields.Char(
        string="Adyen API key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_erp_manager",
        help="Used when connecting to Adyen: https://docs.adyen.com/user-management/how-to-get-the-api-key/#description",
    )
    adyen_terminal_identifier = fields.Char(
        copy=False,
        help="[Terminal model]-[Serial number], for example: P400Plus-123456789",
    )
    adyen_test_mode = fields.Boolean(
        groups="base.group_erp_manager",
        help="Run transactions in the test environment.",
    )

    adyen_latest_response = fields.Char(
        copy=False,
        groups="base.group_erp_manager",
    )  # used to buffer the latest asynchronous notification from Adyen.
    adyen_event_url = fields.Char(
        string="Event URL",
        default=lambda self: f"{self.get_base_url()}/pos_adyen/notification",
        store=False,
        readonly=True,
        help="This URL needs to be pasted on Adyen's portal terminal settings.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ["adyen_terminal_identifier"]
        return params

    @api.constrains("adyen_terminal_identifier")
    def _check_adyen_terminal_identifier(self):
        for payment_method in self:
            if not payment_method.adyen_terminal_identifier:
                continue
            # sudo() to search all companies
            existing_payment_method = self.sudo().search(  # noqa: E8507 - one probe per method, on its own terminal identifier
                [
                    ("id", "!=", payment_method.id),
                    (
                        "adyen_terminal_identifier",
                        "=",
                        payment_method.adyen_terminal_identifier,
                    ),
                ],
                limit=1,
            )
            if existing_payment_method:
                if existing_payment_method.company_id == payment_method.company_id:
                    raise ValidationError(
                        self.env._(
                            "Terminal %(terminal)s is already used on payment method %(payment_method)s.",
                            terminal=payment_method.adyen_terminal_identifier,
                            payment_method=existing_payment_method.display_name,
                        )
                    )
                raise ValidationError(
                    self.env._(
                        "Terminal %(terminal)s is already used in company %(company)s on payment method %(payment_method)s.",
                        terminal=payment_method.adyen_terminal_identifier,
                        company=existing_payment_method.company_id.name,
                        payment_method=existing_payment_method.display_name,
                    )
                )

    def _get_adyen_endpoints(self):
        return {
            "terminal_request": "https://terminal-api-%s.adyen.com/async",
        }

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {"adyen_latest_response"})

    def get_latest_adyen_status(self):
        self.check_singleton()
        if not self.env.su and not self.env.user.has_group(
            "point_of_sale.group_pos_user"
        ):
            raise AccessDenied

        latest_response = self.sudo().adyen_latest_response
        return json.loads(latest_response) if latest_response else False

    def proxy_adyen_request(self, data, operation=False):
        """Necessary because Adyen's endpoints don't have CORS enabled"""
        self.check_singleton()
        if not self.env.su and not self.env.user.has_group(
            "point_of_sale.group_pos_user"
        ):
            raise AccessDenied
        if not data:
            raise UserError(self.env._("Invalid Adyen request"))

        if (
            "SaleToPOIRequest" in data
            and data["SaleToPOIRequest"]["MessageHeader"]["MessageCategory"]
            == "Payment"
            and "PaymentRequest" in data["SaleToPOIRequest"]
        ):  # Clear only if it is a payment request
            self.sudo().adyen_latest_response = (
                ""  # avoid handling old responses multiple times
            )

        if not operation:
            operation = "terminal_request"

        # These checks are not optimal. This RPC method should be changed.

        is_capture_data = (
            operation == "capture"
            and hasattr(self, "adyen_merchant_account")
            and self._is_valid_adyen_request_data(
                data,
                {
                    "originalReference": UNPREDICTABLE_ADYEN_DATA,
                    "modificationAmount": {
                        "value": UNPREDICTABLE_ADYEN_DATA,
                        "currency": UNPREDICTABLE_ADYEN_DATA,
                    },
                    "merchantAccount": self.adyen_merchant_account,
                },
            )
        )

        is_adjust_data = (
            operation == "adjust"
            and hasattr(self, "adyen_merchant_account")
            and self._is_valid_adyen_request_data(
                data,
                {
                    "originalReference": UNPREDICTABLE_ADYEN_DATA,
                    "modificationAmount": {
                        "value": UNPREDICTABLE_ADYEN_DATA,
                        "currency": UNPREDICTABLE_ADYEN_DATA,
                    },
                    "merchantAccount": self.adyen_merchant_account,
                    "additionalData": {
                        "industryUsage": "DelayedCharge",
                    },
                },
            )
        )

        is_cancel_data = (
            operation == "terminal_request"
            and self._is_valid_adyen_request_data(
                data,
                {
                    "SaleToPOIRequest": {
                        "MessageHeader": self._get_expected_message_header("Abort"),
                        "AbortRequest": {
                            "AbortReason": "MerchantAbort",
                            "MessageReference": {
                                "MessageCategory": "Payment",
                                "SaleID": UNPREDICTABLE_ADYEN_DATA,
                                "ServiceID": UNPREDICTABLE_ADYEN_DATA,
                            },
                        },
                    },
                },
            )
        )

        is_payment_request_with_acquirer_data = (
            operation == "terminal_request"
            and self._is_valid_adyen_request_data(
                data, self._get_expected_payment_request(True)
            )
        )

        if is_payment_request_with_acquirer_data:
            parsed_sale_to_acquirer_data = parse_qs(
                data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                    "SaleToAcquirerData"
                ]
            )
            valid_acquirer_data = self._prepare_acquirer_data()
            is_payment_request_with_acquirer_data = len(
                parsed_sale_to_acquirer_data.keys()
            ) <= len(valid_acquirer_data.keys())
            if is_payment_request_with_acquirer_data:
                for key, values in parsed_sale_to_acquirer_data.items():
                    if len(values) != 1:
                        is_payment_request_with_acquirer_data = False
                        break
                    value = values[0]
                    valid_value = valid_acquirer_data.get(key)
                    if valid_value == UNPREDICTABLE_ADYEN_DATA:
                        continue
                    if value != valid_value:
                        is_payment_request_with_acquirer_data = False
                        break

        is_payment_request_without_acquirer_data = (
            operation == "terminal_request"
            and self._is_valid_adyen_request_data(
                data, self._get_expected_payment_request(False)
            )
        )

        if (
            not is_payment_request_without_acquirer_data
            and not is_payment_request_with_acquirer_data
            and not is_adjust_data
            and not is_cancel_data
            and not is_capture_data
        ):
            raise UserError(self.env._("Invalid Adyen request"))

        if (
            is_payment_request_with_acquirer_data
            or is_payment_request_without_acquirer_data
        ):
            acquirer_data = data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"].get(
                "SaleToAcquirerData"
            )
            msg_header = data["SaleToPOIRequest"]["MessageHeader"]
            metadata = "metadata.pos_hmac=" + self._get_hmac(
                msg_header["SaleID"],
                msg_header["ServiceID"],
                msg_header["POIID"],
                data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                    "SaleTransactionID"
                ]["TransactionID"],
            )

            data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                "SaleToAcquirerData"
            ] = acquirer_data + "&" + metadata if acquirer_data else metadata

        return self._proxy_adyen_request_direct(data, operation)

    @api.model
    def _is_valid_adyen_request_data(self, provided_data, expected_data):
        if not isinstance(provided_data, dict) or set(provided_data.keys()) != set(
            expected_data.keys()
        ):
            return False

        for provided_key, provided_value in provided_data.items():
            expected_value = expected_data[provided_key]
            if expected_value == UNPREDICTABLE_ADYEN_DATA:
                continue
            if isinstance(expected_value, dict):
                if not self._is_valid_adyen_request_data(
                    provided_value, expected_value
                ):
                    return False
            elif provided_value != expected_value:
                return False
        return True

    def _get_expected_message_header(self, expected_message_category):
        return {
            "ProtocolVersion": "3.0",
            "MessageClass": "Service",
            "MessageType": "Request",
            "MessageCategory": expected_message_category,
            "SaleID": UNPREDICTABLE_ADYEN_DATA,
            "ServiceID": UNPREDICTABLE_ADYEN_DATA,
            "POIID": self.adyen_terminal_identifier,
        }

    def _get_expected_payment_request(self, with_acquirer_data):
        res = {
            "SaleToPOIRequest": {
                "MessageHeader": self._get_expected_message_header("Payment"),
                "PaymentRequest": {
                    "SaleData": {
                        "SaleTransactionID": {
                            "TransactionID": UNPREDICTABLE_ADYEN_DATA,
                            "TimeStamp": UNPREDICTABLE_ADYEN_DATA,
                        },
                    },
                    "PaymentTransaction": {
                        "AmountsReq": {
                            "Currency": UNPREDICTABLE_ADYEN_DATA,
                            "RequestedAmount": UNPREDICTABLE_ADYEN_DATA,
                        },
                    },
                },
            },
        }

        if with_acquirer_data:
            res["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                "SaleToAcquirerData"
            ] = UNPREDICTABLE_ADYEN_DATA
        return res

    @api.model
    def _prepare_acquirer_data(self):
        return {"tenderOption": "AskGratuity", "authorisationType": "PreAuth"}

    @api.model
    def _get_hmac(self, sale_id, service_id, poi_id, sale_transaction_id):
        return hmac(
            env=self.env(su=True),
            scope="pos_adyen_payment",
            message=(sale_id, service_id, poi_id, sale_transaction_id),
        )

    def _proxy_adyen_request_direct(self, data, operation):
        self.check_singleton()
        TIMEOUT = 10

        _logger.info(
            "Request to Adyen by user #%d:\n%s", self.env.uid, pprint.pformat(data)
        )

        environment = "test" if self.sudo().adyen_test_mode else "live"
        endpoint = self._get_adyen_endpoints()[operation] % environment
        headers = {
            "x-api-key": self.sudo().adyen_api_key,
        }
        req = self._get_integration_connection()._egress_request(
            "POST",
            endpoint,
            purpose="pos_adyen",
            json=data,
            headers=headers,
            timeout=TIMEOUT,
        )

        # Authentication error doesn't return JSON
        if req.status_code == 401:
            return {"error": {"status_code": req.status_code, "message": req.text}}

        if req.text == "ok":
            return True

        return req.json()
