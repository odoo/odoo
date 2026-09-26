# Part of Odoo. See LICENSE file for full copyright and licensing details.
import secrets
import string
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import hmac, consteq

# Google wallet

CODE_LENGTH = 6
VALIDITY = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5

import base64
import json
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class ResPartner(models.Model):
    _inherit = 'res.partner'

    self_otp_code_hash = fields.Char(string="Hashed One Time Code", copy=False, groups=fields.NO_ACCESS)
    self_otp_sent_at = fields.Datetime(string="One Time Code Sent Datetime", copy=False, groups=fields.NO_ACCESS)
    self_otp_expires_at = fields.Datetime(string="One Time Code Expiration Datetime", copy=False, groups=fields.NO_ACCESS)
    self_otp_attempts = fields.Integer(default=0, copy=False, groups=fields.NO_ACCESS)

    def _generate_otp(self):
        self.ensure_one()
        partner = self.sudo()
        now = fields.Datetime.now()
        if partner.self_otp_sent_at and partner.self_otp_sent_at > now - RESEND_COOLDOWN:
            return None
        code = ''.join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))
        partner.self_otp_code_hash = hmac(self.env(su=True), 'self-loyalty-auth', (self.id, code))
        partner.self_otp_attempts = 0
        now = fields.Datetime.now()
        partner.self_otp_sent_at = now
        partner.self_otp_expires_at = now + VALIDITY
        return code

    def _verify_otp(self, code):
        self.ensure_one()
        partner = self.sudo()

        if not isinstance(code, str) or len(code) != CODE_LENGTH or not code.isdigit():
            return False

        self.env.flush_all()
        self.env.cr.execute("SELECT id FROM res_partner WHERE id = %s FOR UPDATE", (self.id,))
        partner.invalidate_recordset(['self_otp_code_hash', 'self_otp_expires_at', 'self_otp_attempts'])

        if not partner.self_otp_code_hash:
            return False
        if partner.self_otp_attempts >= MAX_ATTEMPTS:
            partner._otp_clear()
            return False
        if not partner.self_otp_expires_at or partner.self_otp_expires_at < fields.Datetime.now():
            partner._otp_clear()
            return False

        partner.self_otp_attempts += 1
        expected = hmac(self.env(su=True), 'self-loyalty-auth', (self.id, code))
        return consteq(partner.self_otp_code_hash, expected)

    def _otp_clear(self):
        self.sudo().write({
            "self_otp_code_hash": False,
            "self_otp_sent_at": False,
            "self_otp_expires_at": False,
            "self_otp_attempts": 0,
        })

    def _send_code_to_client(self):
        code = self._generate_otp()
        if code:
            template = self.env.ref('pos_self_order_loyalty.mail_template_self_otp').sudo()
            email_values = {
                'email_to': self.email,
                'email_cc': False,
                'auto_delete': True,
                'recipient_ids': [],
                'partner_ids': [],
                'scheduled_date': False,
            }
            template.with_context(
                otp_code=code,
                validity_minutes=int(VALIDITY.total_seconds() // 60),
            ).send_mail(
                self.id, force_send=True,
                email_values=email_values,
                email_layout_xmlid='mail.mail_notification_light',
            )
        return True

    def _validate_code(self, code):
        if not self._verify_otp(code):
            return False
        self._otp_clear()
        return True

    @api.autovacuum
    def _gc_partner_otp(self):
        """Expired codes are already refused; this just stops stale hashes
        from sitting in every backup and staging clone indefinitely."""
        stale = self.sudo().search([
            ("self_otp_code_hash", "!=", False),
            ("self_otp_expires_at", "<", fields.Datetime.now()),
        ])
        stale._otp_clear()

    # ------------------------------------------------------------------
    # Google Wallet
    # ------------------------------------------------------------------

    def _google_wallet_url(self):
        """Return an 'Add to Google Wallet' link, or False if unconfigured.

        The pass object is embedded in the JWT rather than pre-created via
        the REST API, so nothing exists on Google's side until the customer
        actually taps the link. Keep the whole URL under ~1800 characters:
        past that, browsers truncate it and the save silently fails.
        """

        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        params = self.env['ir.config_parameter'].sudo()
        issuer_id = params.get_param('self_wallet.google_issuer_id')
        sa_path = params.get_param('self_wallet.google_sa_path')
        class_id = params.get_param('self_wallet.google_class_suffix')
        if not issuer_id or not sa_path:
            return False

        with open(sa_path, 'rb') as fh:
            service_account = json.load(fh)

        base_url = params.get_str('web.base.url')
        claims = {
            'iss': service_account['client_email'],
            'aud': 'google',
            'typ': 'savetowallet',
            'iat': int(time.time()),
            # Required. The button will not render without it.
            'origins': [base_url],
            'payload': {'loyaltyObjects': [{
                'id': '%s.%s' % (issuer_id, self.barcode),
                'classId': '%s.%s' % (issuer_id, class_id),
                'state': 'ACTIVE',
                'accountId': self.barcode,
                'accountName': self.name,
                'barcode': {'type': 'CODE_128', 'value': self.barcode},
            }]},
        }

        def b64(raw):
            return base64.urlsafe_b64encode(raw).rstrip(b'=')

        segments = [
            b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}, separators=(',', ':')).encode()),
            b64(json.dumps(claims, separators=(',', ':')).encode()),
        ]
        signing_input = b'.'.join(segments)
        key = serialization.load_pem_private_key(
            service_account['private_key'].encode(), password=None
        )
        signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        token = b'.'.join([signing_input, b64(signature)]).decode()
        return 'https://pay.google.com/gp/v/save/%s' % token
