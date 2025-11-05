import hashlib
import hmac
import json

from odoo.tests.common import HttpCase


class SnailmailWebhookCase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'street': 'Test Street 1',
            'zip': '1234',
            'city': 'Test City',
            'country_id': cls.env.ref('base.ch').id,
        })

        iap_service = cls.env.ref('snailmail.iap_service_snailmail')
        cls.iap_account = cls.env['iap.account'].create({
            'name': 'snailmail',
            'account_token': 'test_iap_account_token_1234',
            'service_id': iap_service.id,
        })
        cls.hashed_token = hashlib.sha1(
            cls.iap_account.account_token.encode('utf-8')
        ).hexdigest()
        cls.pingen_letter_id = 'test-pingen-letter-uuid-1234'

    def setUp(self):
        super().setUp()
        self.letter = self.env['snailmail.letter'].create({
            'partner_id': self.partner.id,
            'model': 'res.partner',
            'res_id': self.partner.id,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'document_id': self.pingen_letter_id,
            'state': 'pending',
        })

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _make_payload(self, letter_id=None, status=None, reason=None):
        """Build the event payload IAP sends to community."""
        payload = {
            'letter_id': letter_id or self.pingen_letter_id,
            'status': status or 'delivered',
        }
        if reason:
            payload['reason'] = reason
        return payload

    def _make_signature(self, payload, token=None):
        """Generate HMAC signature the way IAP does."""
        sign_token = token or self.hashed_token
        return hmac.new(
            key=sign_token.encode(),
            msg=json.dumps(payload, sort_keys=True).encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def _post_webhook(self, event_type, payload, signature=None):
        """Send a POST request to the snailmail webhook endpoint."""
        body = json.dumps(payload, sort_keys=True).encode()
        sig = signature or self._make_signature(payload)
        return self.url_open(
            f'/webhook/snailmail/1/{event_type}',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'odoo-iap-signature': sig,
            },
        )
