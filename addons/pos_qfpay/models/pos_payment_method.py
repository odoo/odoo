import base64
import hashlib
import json
import logging

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.integration.tools.admission import Acknowledged

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _receiver_for_qfpay_notification(self, **path_args):
        raw_body = request.httprequest.get_data(cache=True)
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except ValueError, UnicodeDecodeError:
            _logger.warning("QFPay notification is not JSON")
            raise Acknowledged.json(None) from None
        # The trade number is `<payment uuid>--<session>--<method>`; the
        # signature is checked against the method it names, once resolved.
        trade_no = data.get("orig_out_trade_no", data.get("out_trade_no")) or ""
        try:
            payment_uuid, session_id, pm_id = trade_no.split("--")
            pm_id = int(pm_id)
            session_id = int(session_id)
        except ValueError:
            _logger.warning("QFpay invalid out_trade_no format")
            raise Acknowledged.json(None) from None
        method = self.sudo().browse(pm_id).exists()
        if not method or not method.qfpay_notification_key:
            _logger.warning("QFPay payment method does not have a notification key set")
            raise Acknowledged.json(None)
        return method, {
            "data": data,
            "payment_uuid": payment_uuid,
            "session_id": session_id,
        }

    def _inbound_gate_owner(self):
        return self, f"{self.name} notifications", None

    def _verify_inbound_request(self, headers, body):
        if self.use_payment_terminal != "qfpay":
            return super()._verify_inbound_request(headers, body)
        sign_str = (body or b"") + self.qfpay_notification_key.encode()
        computed_sign = hashlib.md5(sign_str).hexdigest().upper()
        return consteq(computed_sign, headers.get("X-QF-SIGN") or "")

    _CREDENTIAL_FIELDS = {
        "qfpay_pos_key": "qfpay_pos_key",
        "qfpay_notification_key": "qfpay_notification_key",
    }

    def _selection_payment_terminals(self):
        return super()._selection_payment_terminals() + [("qfpay", "QFPay")]

    qfpay_terminal_ip_address = fields.Char(
        string="QFPay Terminal IP Address",
        copy=False,
    )
    qfpay_pos_key = fields.Char(
        string="QFPay POS Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="point_of_sale.group_pos_manager",
    )
    qfpay_notification_key = fields.Char(
        string="QFPay Notification Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="point_of_sale.group_pos_manager",
    )
    qfpay_latest_response = fields.Char(
        copy=False,
        groups="point_of_sale.group_pos_manager",
    )
    qfpay_payment_type = fields.Selection(
        selection=[
            ("card_payment", "Visa/Mastercard"),
            ("wx", "WeChat Pay"),
            ("alipay", "Alipay"),
            ("payme", "PayMe"),
            ("union", "UnionPay QuickPass"),
            ("fps", "FPS"),
            ("octopus", "Octopus"),
            ("unionpay_card", "Unionpay Card"),
            ("amex_card", "American Express Card"),
        ],
        string="QFPay Payment Type",
        copy=False,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ["qfpay_terminal_ip_address", "qfpay_payment_type"]
        return params

    @api.constrains("use_payment_terminal")
    def _check_qfpay_terminal(self):
        if any(
            record.use_payment_terminal == "qfpay"
            and record.company_id.currency_id.name != "HKD"
            for record in self
        ):
            raise UserError(_("QFPay is only valid for HKD Currency"))

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {"qfpay_latest_response"})

    def qfpay_sign_request(self, payload):
        self.check_singleton()
        if not self.env.su and not self.env.user.has_group(
            "point_of_sale.group_pos_user"
        ):
            raise AccessDenied

        if self.use_payment_terminal != "qfpay":
            raise UserError(
                _("This method can only be used with QFPay payment terminal.")
            )

        key = self.sudo().qfpay_pos_key
        # AES IV is a constant as stated in the documentation
        aes_iv = "qfpay202306_hjsh"

        # Sort the payload items and format
        payload_items = sorted((k, "" if v is None else v) for k, v in payload.items())
        formated_payload = ",".join(
            f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}" for k, v in payload_items
        )
        formated_payload = "{" + formated_payload + "}"

        # Generate Digest
        md5 = hashlib.md5()
        md5.update((formated_payload + key).encode("utf-8"))
        digest = md5.hexdigest().upper()

        # Prepare the payload to encrypt
        payload_to_encrypt = (
            "{content:" + formated_payload + ", digest:'" + digest + "'}"
        )

        # Encrypt the payload
        cipher = Cipher(
            algorithms.AES(key.encode("utf-8")), modes.CBC(aes_iv.encode("utf-8"))
        )
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = (
            padder.update(payload_to_encrypt.encode("utf-8")) + padder.finalize()
        )
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode("utf-8")

    @api.model
    def _qfpay_handle_webhook(self, config, data, uuid):
        config._notify(
            "QFPAY_LATEST_RESPONSE",
            {
                "response": data,
                "line_uuid": uuid,
            },
        )
