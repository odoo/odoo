# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import json
import logging
import re
import requests

from functools import lru_cache
from werkzeug import urls
from werkzeug.exceptions import NotFound

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
except ImportError:
    serialization = hashes = ec = default_backend = InvalidSignature = None

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)
TIMEOUT = 60


class EbayController(Controller):
    _endpoint = '/ebay/account/delete'

    @route(_endpoint, type='http', auth='none', methods=['GET',])
    def ebay_account_deletion_check_endpoint(self, challenge_code):
        """ Query to validate the legitimacy of the endpoint URL

        See https://developer.ebay.com/marketplace-account-deletion

        :param str challenge_code: random string sent by eBay
        :return: The computed hexadecimal string response
        :rtype: json
        """
        IrConfigParam = request.env['ir.config_parameter'].sudo()
        verification_token = IrConfigParam.get_param("sale_ebay.acc_deletion_token", "")
        endpoint_url = urls.url_join(
            IrConfigParam.get_param('web.base.url'),
            self._endpoint,
        )

        response_code = hashlib.sha256(
            (challenge_code + verification_token + endpoint_url).encode()
        ).hexdigest()

        _logger.info(
            'Notification from eBay with the challenge_code %s. Returned response code: %s',
            challenge_code,
            response_code,
        )
        return json.dumps({'challengeResponse': response_code})

    @route(_endpoint, type='json', auth='none', methods=['POST',], csrf=False)
    def ebay_account_deletion_webhook(self):
        """ Query to inform the db about an eBay Marketplace Account Deletion/Closure

        See https://developer.ebay.com/marketplace-account-deletion

        :return: "OK" (HTTP 200)
        """
        if not self._verify_signature():
            # Verification details already logged in _verify_signature
            raise NotFound()

        request_content = json.loads(request.httprequest.data)
        notification_topic = request_content['metadata']['topic']
        if notification_topic != 'MARKETPLACE_ACCOUNT_DELETION':
            _logger.error(
                "Received notification with topic %s on marketplace account deletion route",
                notification_topic)
            raise NotFound()

        _logger.info(
            'Account Deletion/Closure notification from eBay: %s',
            request_content,
        )

        # NOTE: what we effectively store as ebayID seems to be the username
        # and not the userID.  The code is confusing, but it was verified
        # on effective instances.
        ebayID = request_content['notification']['data']['username']
        partners = request.env['res.partner'].sudo().search([
            ('ebay_id', '=', ebayID),
        ])
        if partners:
            partners._handle_ebay_account_deletion_notification()
        return

    def _verify_signature(self):
        """Verify signature of current eBay request

        :returns: True if signature is valid, False otherwise
        :rtype: bool
        """
        if not serialization:
            _logger.error("Couldn't load cryptography lib, all ebay notifications will be discarded")
            return False

        # https://developer.ebay.com/api-docs/commerce/notification/overview.html
        # payload = bytes encoded json data
        payload = request.httprequest.data

        # Decode x-ebay-signature header
        # -> {'alg': 'ecdsa', 'kid': '...', 'signature': '...', 'digest': 'SHA1'}
        signature_header = request.httprequest.headers.get('x-ebay-signature')
        signature_details = json.loads(base64.b64decode(signature_header))

        if not (signature_details['alg'] == "ecdsa" and signature_details['digest'] == "SHA1"):
            _logger.error(
                "Ebay: unsupported algorithm for notification signatures (algo: %s, digest:%s)",
                signature_details['alg'], signature_details['digest'])
            return False

        # Fetch public key (for given key id) from ebay
        pem_public_key = self._fetch_public_key(signature_details['kid'])
        if not pem_public_key:
            # Any error happened while fetching public key
            return False

        raw_signature = signature_details['signature']
        decoded_signature = base64.b64decode(raw_signature.encode())

        try:
            public_key = serialization.load_pem_public_key(
                pem_public_key.encode(), backend=default_backend())
        except ValueError as e:
            _logger.error(
                "Ebay: Public key (PEM) data’s structure could not be decoded successfully %s", e)
            return False

        try:
            public_key.verify(
                decoded_signature,
                payload,
                ec.ECDSA(hashes.SHA1())
            )
            return True
        except InvalidSignature:
            _logger.error(
                "Ebay: Received notification with invalid signature (payload %s, signature %s)",
                payload, raw_signature)
            return False

    def _fetch_ebay_oauth_token(self):
        """Fetch temporary OAuth token from eBay

        :returns: token to use in Authorization header for request to eBay Notification API
        :rtype: str
        """
        # https://developer.ebay.com/api-docs/static/oauth-client-credentials-grant.html
        IrConfigParam = request.env['ir.config_parameter'].sudo()
        client_id = IrConfigParam.get_param('ebay_prod_app_id') # App ID
        client_secret = IrConfigParam.get_param('ebay_prod_cert_id') # CERT ID
        if not client_id or not client_secret:
            _logger.error("Ebay: cannot fetch OAuth token without credentials.")
            return None

        authorization_prefix = (client_id + ':' + client_secret).encode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            # https://developer.ebay.com/api-docs/static/oauth-base64-credentials.html
            "Authorization": f"Basic {str(base64.b64encode(authorization_prefix), 'utf-8')}",
        }
        try:
            response = requests.post(
                # Note: never sandbox for marketplace account deletion
                url="https://api.ebay.com/identity/v1/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
                headers=headers,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
        except Exception as e:
            _logger.error("Couldn't fetch OAuth token from Ebay:\n%s", e)
            return None

        data = response.json()
        return data['access_token']

    @lru_cache(maxsize=256)
    def _fetch_public_key(self, key_id):
        """Fetch public key details, according to key id

        Covered by a LRU cache as requested by ebay
        "Make a cache-enabled call to the Notification API to retrieve the public key"

        :param str key_id: Id of the key to fetch from eBay
        :returns: public key (in wrong PEM format)
        :rtype: str
        """
        try:
            # Request authorization token (for ebay credentials)
            token = self._fetch_ebay_oauth_token()
            if not token:
                return None
            response = requests.get(
                url=f"https://api.ebay.com/commerce/notification/v1/public_key/{key_id}",
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': 'bearer ' + token,
                },
                timeout=TIMEOUT,
            )
            response.raise_for_status()
        except Exception as e:
            _logger.error("Couldn't fetch public key from ebay (key id: %s):\n%s", key_id, e)
            return None

        # Extract public key from response
        # -> {'key': '----BEGIN PUBLIC KEY----...', 'algorithm': 'ECDSA', 'digest': 'SHA1'}
        pk_details = response.json()
        if not (pk_details['algorithm'] == "ECDSA" and pk_details['digest'] == "SHA1"):
            _logger.error(
                "Ebay: unsupported algorithm for notification signatures (algo: %s, digest:%s)",
                pk_details['algorithm'], pk_details['digest'])
            return None

        # Format public key to correct PEM format for cryptography verification
        return self._format_public_key(pk_details['key'])

    def _format_public_key(self, key):
        """Format public key to valid PEM format

        :param str key: key in wrong PEM format (missing \n)
        :returns: valid PEM format key (header, footer, lines of 64chars)
        :rtype: str
        """
        key = re.findall(
            '-----BEGIN PUBLIC KEY-----(.+)-----END PUBLIC KEY-----',
            key
        )[0]
        pk_split = ["-----BEGIN PUBLIC KEY-----"]
        # index = 0
        for index in range(0, len(key), 64):
            pk_split.append(key[index:index+64])
        pk_split.append("-----END PUBLIC KEY-----")
        return "\n".join(pk_split)
