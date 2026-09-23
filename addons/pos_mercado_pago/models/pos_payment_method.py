import hashlib
import hmac
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from .mercado_pago_pos_request import MercadoPagoPosRequest
from odoo.addons.integration.tools.admission import Acknowledged, Refused

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _name = "pos.payment.method"
    _inherit = ["pos.payment.method", "mixin.integration.connected"]

    _MERCADO_PAGO_REFERENCE = re.compile(
        r"(\d+)_(\d+)_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    )

    @api.model
    def _receiver_for_mercado_pago_terminal(self, **path_args):
        headers = request.httprequest.headers
        if not headers.get("X-Request-Id"):
            _logger.warning("POST message received with no X-Request-Id in header")
            raise Refused(400, "X-Request-Id header missing", "bad_request")
        x_signature = headers.get("X-Signature")
        if not x_signature:
            _logger.warning("POST message received with no X-Signature in header")
            raise Refused(400, "X-Signature header missing", "bad_request")
        ts_m = re.search(r"ts=(\d+)", x_signature)
        v1_m = re.search(r"v1=([a-f0-9]+)", x_signature)
        if not ts_m or not v1_m:
            _logger.warning("Webhook bad X-Signature: %s", x_signature)
            raise Refused(400, "X-Signature header malformed", "bad_request")
        data = request.httprequest.get_json(silent=True)
        if not data:
            _logger.warning("POST message received with no data")
            raise Refused(400, "no JSON body", "bad_request")
        # A payment intent's `external_reference` is `<session>_<method>_<order uuid>`
        # (see payment_mercado_pago.js).
        external_reference = data.get("additional_info", {}).get("external_reference")
        match = external_reference and self._MERCADO_PAGO_REFERENCE.fullmatch(
            external_reference
        )
        if not match:
            _logger.warning(
                'POST message received with no or malformed "external_reference" '
                "key: %s",
                external_reference,
            )
            raise Refused(400, "external_reference missing or malformed", "bad_request")
        session_id, payment_method_id, _order_uuid = match.groups()
        pos_session = self.env["pos.session"].sudo().browse(int(session_id))
        if not pos_session.exists() or pos_session.state != "opened":
            _logger.error("Invalid session id: %s", session_id)
            # Not Mercado Pago's mistake: acknowledge its message.
            raise Acknowledged("OK")
        method = pos_session.config_id.payment_method_ids.filtered(
            lambda p: p.id == int(payment_method_id)
        )
        if not method or method.use_payment_terminal != "mercado_pago":
            _logger.error("Invalid payment method id: %s", payment_method_id)
            raise Acknowledged("OK")
        return method, {
            "data": data,
            "session": pos_session,
            "ts": ts_m.group(1),
            "v1": v1_m.group(1),
        }

    def _inbound_gate_owner(self):
        return self, f"{self.name} notifications", None

    def _verify_inbound_request(self, headers, body):
        if self.use_payment_terminal != "mercado_pago":
            return super()._verify_inbound_request(headers, body)
        x_signature = headers.get("X-Signature") or ""
        ts_m = re.search(r"ts=(\d+)", x_signature)
        v1_m = re.search(r"v1=([a-f0-9]+)", x_signature)
        data = request.httprequest.get_json(silent=True) or {}
        if not ts_m or not v1_m or "id" not in data:
            return False
        signed_template = (
            f"id:{data['id']};request-id:{headers.get('X-Request-Id')};"
            f"ts:{ts_m.group(1)};"
        )
        cyphed_signature = hmac.new(
            (self.mp_webhook_secret_key or "").encode(),
            signed_template.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(cyphed_signature, v1_m.group(1))

    def _integration_connection_service(self):
        if self.use_payment_terminal == "mercado_pago":
            return (
                "pos_mercado_pago",
                self.env._("Point of Sale: Mercado Pago"),
                "payment",
            )
        return super()._integration_connection_service()

    _CREDENTIAL_FIELDS = {
        "mp_bearer_token": "mp_bearer_token",
        "mp_webhook_secret_key": "mp_webhook_secret_key",
    }

    mp_bearer_token = fields.Char(
        string="Production user token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
        groups="point_of_sale.group_pos_manager",
        help="Mercado Pago customer production user token: https://www.mercadopago.com.mx/developers/en/reference",
    )
    mp_webhook_secret_key = fields.Char(
        string="Production secret key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
        groups="point_of_sale.group_pos_manager",
        help="Mercado Pago production secret key from integration application: https://www.mercadopago.com.mx/developers/panel/app",
    )
    mp_id_point_smart = fields.Char(
        string="Terminal S/N",
        help="Enter your Point Smart terminal serial number written on the back of your terminal (after the S/N:)",
    )
    mp_id_point_smart_complet = fields.Char()

    def _selection_payment_terminals(self):
        return super()._selection_payment_terminals() + [
            ("mercado_pago", "Mercado Pago")
        ]

    def _check_special_access(self):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                self.env._("Do not have access to fetch token from Mercado Pago")
            )

    def force_pdv(self):
        """
        Triggered in debug mode when the user wants to force the "PDV" mode.
        It calls the Mercado Pago API to set the terminal mode to "PDV".
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self, self.sudo().mp_bearer_token)
        _logger.info('Calling Mercado Pago to force the terminal mode to "PDV"')

        mode = {"operating_mode": "PDV"}
        resp = mercado_pago.call_mercado_pago(
            "patch",
            f"/point/integration-api/devices/{self.mp_id_point_smart_complet}",
            mode,
        )
        if resp.get("operating_mode") != "PDV":
            raise UserError(self.env._("Unexpected Mercado Pago response: %s", resp))
        _logger.debug("Successfully set the terminal mode to 'PDV'.")

    def mp_payment_intent_create(self, infos):
        """
        Called from frontend for creating a payment intent in Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self, self.sudo().mp_bearer_token)
        # Call Mercado Pago for payment intend creation
        resp = mercado_pago.call_mercado_pago(
            "post",
            f"/point/integration-api/devices/{self.mp_id_point_smart_complet}/payment-intents",
            infos,
        )
        _logger.debug(
            "mp_payment_intent_create(), response from Mercado Pago: %s", resp
        )
        return resp

    def mp_payment_intent_get(self, payment_intent_id):
        """
        Called from frontend to get the last payment intend from Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self, self.sudo().mp_bearer_token)
        # Call Mercado Pago for payment intend status
        resp = mercado_pago.call_mercado_pago(
            "get", f"/point/integration-api/payment-intents/{payment_intent_id}", {}
        )
        _logger.debug("mp_payment_intent_get(), response from Mercado Pago: %s", resp)
        return resp

    def mp_get_payment_status(self, payment_id):
        """
        Called from frontend to get the payment status from Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self, self.sudo().mp_bearer_token)

        resp = mercado_pago.call_mercado_pago("get", f"/v1/payments/{payment_id}", {})
        _logger.debug("mp_get_payment_status(), response from Mercado Pago: %s", resp)
        return resp

    def mp_payment_intent_cancel(self, payment_intent_id):
        """
        Called from frontend to cancel a payment intent in Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self, self.sudo().mp_bearer_token)
        # Call Mercado Pago for payment intend cancelation
        resp = mercado_pago.call_mercado_pago(
            "delete",
            f"/point/integration-api/devices/{self.mp_id_point_smart_complet}/payment-intents/{payment_intent_id}",
            {},
        )
        _logger.debug(
            "mp_payment_intent_cancel(), response from Mercado Pago: %s", resp
        )
        return resp

    def _find_terminal(self, token, point_smart):
        mercado_pago = MercadoPagoPosRequest(self, token)
        data = mercado_pago.call_mercado_pago(
            "get", "/point/integration-api/devices", {}
        )
        if "devices" in data:
            # Search for a device id that contains the serial number entered by the user
            found_device = next(
                (device for device in data["devices"] if point_smart in device["id"]),
                None,
            )

            if not found_device:
                raise UserError(
                    self.env._(
                        "The terminal serial number is not registered on Mercado Pago"
                    )
                )

            return found_device.get("id", "")
        else:
            raise UserError(
                self.env._(
                    "Please verify your production user token as it was rejected"
                )
            )

    def write(self, vals):
        records = super().write(vals)

        if "mp_id_point_smart" in vals or "mp_bearer_token" in vals:
            self.mp_id_point_smart_complet = self._find_terminal(
                self.mp_bearer_token, self.mp_id_point_smart
            )

        return records

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.mp_bearer_token:
                record.mp_id_point_smart_complet = record._find_terminal(
                    record.mp_bearer_token, record.mp_id_point_smart
                )

        return records
