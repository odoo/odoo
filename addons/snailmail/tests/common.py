import hashlib
import hmac
import json

from odoo.tests.common import HttpCase


class SnailmailWebhookCase(HttpCase):
    webhook_signing_key = 'test_webhook_signing_key'

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
        cls.env['ir.config_parameter'].sudo().set_str('snailmail.webhook_signing_key', cls.webhook_signing_key)
        cls.pingen_letter_id = 'test-pingen-letter-uuid-1234'

    def setUp(self):
        super().setUp()
        self.test_letter = self.env['snailmail.letter'].create({
            'partner_id': self.partner.id,
            'model': 'res.partner',
            'res_id': self.partner.id,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'letter_uid': self.pingen_letter_id,
            'state': 'pending',
        })

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _make_signature(self, body, token=None):
        """Generate HMAC signature the way IAP does."""
        sign_token = token or self.webhook_signing_key
        return hmac.new(
            key=sign_token.encode(),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()

    def _post_webhook(self, event_type, status=None, letter_id=None, reason=None, signature=None, payload=None):
        """Send a POST request to the snailmail webhook endpoint.
        event_type is either 'delivered' or 'undeliverable'."""
        if payload is None:
            payload = {
                'letter_id': letter_id or self.pingen_letter_id,
                'status': status or event_type,
            }
            if reason:
                payload['reason'] = reason

        body = json.dumps(payload).encode()
        sig = signature or self._make_signature(body)
        return self.url_open(
            f'/webhook/snailmail/1/{event_type}',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'odoo-iap-signature': sig,
            },
        )
