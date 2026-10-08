# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import timedelta

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import hmac, consteq

# Google wallet
# import base64
# import json
# import time
# from cryptography.hazmat.primitives import hashes, serialization
# from cryptography.hazmat.primitives.asymmetric import padding


SELF_ORDER_TOKEN_SCOPE = 'pos-self-order-partner'
SELF_ORDER_TOKEN_VALIDITY = {
    'mobile': timedelta(days=90),
    'kiosk': timedelta(minutes=30),
}


class SelfOrderIdentificationExpired(UserError):
    """The partner sent by a self-order client isn't backed by a valid identification token."""


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # Self-order identification token
    # ------------------------------------------------------------------

    def _get_self_order_token(self, pos_config):
        """Proof, for the self-order client of `pos_config`, that it identified as this partner."""
        self.ensure_one()
        # Anything but mobile is a shared device (kiosk): keep it short
        validity = SELF_ORDER_TOKEN_VALIDITY.get(pos_config.self_ordering_mode, SELF_ORDER_TOKEN_VALIDITY['kiosk'])
        expiration = int(time.time() + validity.total_seconds())
        signature = hmac(self.env(su=True), SELF_ORDER_TOKEN_SCOPE, (self.id, pos_config.id, expiration))
        return f"{expiration}.{signature}"

    @api.model
    def _get_partner_from_self_order_token(self, pos_config, partner_id, token):
        """:return: the partner `token` proves the client identified as, or an empty recordset."""
        if isinstance(partner_id, bool) or not isinstance(partner_id, int) or not isinstance(token, str):
            return self.browse()
        expiration, _sep, signature = token.partition('.')
        if not expiration.isdigit() or int(expiration) < time.time():
            return self.browse()
        expected = hmac(self.env(su=True), SELF_ORDER_TOKEN_SCOPE, (partner_id, pos_config.id, int(expiration)))
        if not consteq(signature, expected):
            return self.browse()
        return self.browse(partner_id).exists()

    @api.model
    def _load_pos_self_data_read_with_token(self, partners, pos_config):
        """Partner data for a client that just proved its identity, with a fresh token.

        The token is deliberately not added by _load_pos_self_data_read: it also serves
        responses where the client proved nothing.
        """
        records = self._load_pos_self_data_read(partners, pos_config)
        for record in records:
            record['_self_order_token'] = self.browse(record['id'])._get_self_order_token(pos_config)
        return records

    # ------------------------------------------------------------------
    # Google Wallet (POC)
    # ------------------------------------------------------------------

    # def _google_wallet_url(self):
    #     """Return an 'Add to Google Wallet' link, or False if unconfigured.

    #     The pass object is embedded in the JWT rather than pre-created via
    #     the REST API, so nothing exists on Google's side until the customer
    #     actually taps the link. Keep the whole URL under ~1800 characters:
    #     past that, browsers truncate it and the save silently fails.
    #     """

    #     self.ensure_one()
    #     params = self.env['ir.config_parameter'].sudo()
    #     params = self.env['ir.config_parameter'].sudo()
    #     issuer_id = params.get_param('self_wallet.google_issuer_id')
    #     sa_path = params.get_param('self_wallet.google_sa_path')
    #     class_id = params.get_param('self_wallet.google_class_suffix')
    #     if not issuer_id or not sa_path:
    #         return False

    #     with open(sa_path, 'rb') as fh:
    #         service_account = json.load(fh)

    #     base_url = params.get_str('web.base.url')
    #     claims = {
    #         'iss': service_account['client_email'],
    #         'aud': 'google',
    #         'typ': 'savetowallet',
    #         'iat': int(time.time()),
    #         # Required. The button will not render without it.
    #         'origins': [base_url],
    #         'payload': {'loyaltyObjects': [{
    #             'id': '%s.%s' % (issuer_id, self.barcode),
    #             'classId': '%s.%s' % (issuer_id, class_id),
    #             'state': 'ACTIVE',
    #             'accountId': self.barcode,
    #             'accountName': self.name,
    #             'barcode': {'type': 'CODE_128', 'value': self.barcode},
    #         }]},
    #     }

    #     def b64(raw):
    #         return base64.urlsafe_b64encode(raw).rstrip(b'=')

    #     segments = [
    #         b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}, separators=(',', ':')).encode()),
    #         b64(json.dumps(claims, separators=(',', ':')).encode()),
    #     ]
    #     signing_input = b'.'.join(segments)
    #     key = serialization.load_pem_private_key(
    #         service_account['private_key'].encode(), password=None
    #     )
    #     signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    #     token = b'.'.join([signing_input, b64(signature)]).decode()
    #     return 'https://pay.google.com/gp/v/save/%s' % token
