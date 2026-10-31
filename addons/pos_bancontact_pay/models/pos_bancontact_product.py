import base64
import json
import uuid
from datetime import UTC, datetime

import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.pos_bancontact_pay import const


class PosBancontactProduct(models.Model):
    _name = "pos.bancontact.product"
    _description = "Bancontact Pay Product"

    name = fields.Char(required=True)
    ppid = fields.Char("Product ID", required=True, copy=False, help="Bancontact Pro Portal > Admin Centre > Shops and products > Select a shop > Read the product ID from the card")
    api_key = fields.Char("API Key", required=True, copy=False, groups="point_of_sale.group_pos_manager", help="Bancontact Pro Portal > Admin Centre > Shops and products > Select a product > Manage API keys > View API key")
    preprod = fields.Boolean("Preprod", help="Run transactions in Bancontact's preprod environment.")
    usage = fields.Selection(
        selection=[
            ("display", "Display"),
            ("sticker", "Static QR"),
        ],
        string="QR Usage",
        default="display",
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    refund_enabled = fields.Boolean("Refunds")
    can_enable_refund = fields.Boolean(compute="_compute_can_enable_refund")
    payment_method_ids = fields.One2many("pos.payment.method", "bancontact_product_id", string="Payment Methods", context={"active_test": False})
    sticker_ids = fields.One2many("pos.bancontact.sticker", "product_id", string="Stickers")

    @api.depends("company_id.bancontact_merchant_id", "company_id.bancontact_signing_kid")
    def _compute_can_enable_refund(self):
        for product in self:
            product.can_enable_refund = product.company_id._bancontact_can_sign()

    @api.constrains("refund_enabled", "company_id")
    def _check_refund_enabled(self):
        for product in self:
            if product.refund_enabled and not product.company_id._bancontact_can_sign():
                raise ValidationError(_("Set the Bancontact Merchant ID of %(company)s in the Point of Sale settings before enabling refunds.", company=product.company_id.name))

    def _get_bancontact_api_url(self, target):
        """Return the Bancontact endpoint URL for the product's environment."""
        environment = "preprod" if self.preprod else "production"
        return const.API_URLS[environment][target]

    def _sign_bancontact_request(self, path, body):
        """Return the detached JWS (ES256) of a request sent to Bancontact, for its Signature header.

        :param str path: path of the request, e.g. ``/v3/payments/{payment-id}/refunds``.
        :param bytes body: body of the request.
        :return: the JWS, in the form ``protected..signature`` (the payload is detached).
        """
        self.ensure_one()
        company = self.company_id
        if not company._bancontact_can_sign():
            raise UserError(_("Set the Bancontact Merchant ID of %(company)s in the Point of Sale settings.", company=company.name))

        protected = {
            "typ": "jose+json",
            "alg": "ES256",
            "kid": company.bancontact_signing_kid,
            "crit": [const.ISS_KEY, const.IAT_KEY, const.JTI_KEY, const.PATH_KEY, const.SUB_KEY],
            const.ISS_KEY: company.bancontact_merchant_id,
            const.IAT_KEY: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            const.JTI_KEY: uuid.uuid4().hex,
            const.PATH_KEY: path,
            const.SUB_KEY: self.ppid,
        }

        def b64url(data):
            return base64.urlsafe_b64encode(data).decode().rstrip("=")

        protected_b64 = b64url(json.dumps(protected, separators=(",", ":")).encode())
        signing_input = f"{protected_b64}.{b64url(body)}".encode()
        r, s = decode_dss_signature(company._bancontact_get_signing_key().sign(signing_input, ec.ECDSA(SHA256())))
        return f"{protected_b64}..{b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"

    def _send_bancontact_signed_request(self, method, path, payload=None, idempotency_key=None):
        """Send a request signed with the company's key to the Bancontact merchant API.

        :param str method: HTTP method.
        :param str path: path of the request, e.g. ``/v3/payments/{payment-id}/refunds``.
        :param dict payload: JSON body of the request, if any.
        :param str idempotency_key: value of the Idempotency-Key header, if any.
        :return: the response.
        :rtype: requests.Response
        """
        self.ensure_one()
        body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else b""
        headers = {"Signature": self._sign_bancontact_request(path, body)}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return requests.request(method, f"{self._get_bancontact_api_url('merchant')}{path}", data=body or None, headers=headers, timeout=5)

    def write(self, vals):
        used_products = self.filtered("payment_method_ids")
        if "usage" in vals and any(product.usage != vals["usage"] for product in used_products):
            raise UserError(_("The QR usage of a Bancontact product can't be changed while it is used by a payment method."))
        return super().write(vals)
