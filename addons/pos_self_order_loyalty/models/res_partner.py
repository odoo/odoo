# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

# Google wallet
# import base64
# import json
# import time
# from cryptography.hazmat.primitives import hashes, serialization
# from cryptography.hazmat.primitives.asymmetric import padding


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
