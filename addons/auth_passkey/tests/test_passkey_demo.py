import time

from odoo.http import _request_stack
from odoo.tools import DotDict

from odoo.tests.common import TransactionCase
from odoo.addons.website.tools import MockRequest


class PasskeyTest(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # needs a fake request in order to call methods protected with check_identity
        fake_req = DotDict({
            'session': {'identity-check-last': time.time()},
        })
        _request_stack.push(fake_req)

        self.admin_user = self.env.ref('base.user_admin')
        self.demo_user = self.env.ref('base.user_demo')

        admin_key = self.env['auth.passkey.key.name'].with_user(self.admin_user).sudo().create({'name': 'test_passkey_1'})
        admin_key.make_key(
            credential_identifier='wtw0u7D8rp7nq7WBWFCt_FRhEHpU6EHvEgTn3BBid5N-UE5a9XCzS8NaVuh7ydFz',
            public_key='pQECAyYgASFYIMLcNLuw_K6e56u1gVioLcAJF8v8eUw7kfqTOqDdl7nFIlggFSs_nZWewd_JqzeWzXmJ6Wmn_nKuo82rCdoOZ-oewOU='
        )

        demo_key = self.env['auth.passkey.key.name'].with_user(self.demo_user).sudo().create({'name': 'test_passkey_2'})
        demo_key.make_key(
            credential_identifier='y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0',
            public_key='pQECAyYgASFYICjw-NoCHMkYYbRo8Q4SgJ4tZc8BSEmuEI0XmA6hUqR_IlggjtuBgyhwnr7PqABF2o8vCniMVa7_mTG6_l9Pc4eI4mo=',
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(_request_stack.pop)

    def test_authentication(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://localhost:8069')
        # Yubikey Nano
        auth = {
            "id": "wtw0u7D8rp7nq7WBWFCt_FRhEHpU6EHvEgTn3BBid5N-UE5a9XCzS8NaVuh7ydFz",
            "rawId": "wtw0u7D8rp7nq7WBWFCt_FRhEHpU6EHvEgTn3BBid5N-UE5a9XCzS8NaVuh7ydFz",
            "response": {
                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAABg",
                "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoib2owOXpydVV5cVVNSUZPMG9sNVVsdFVkOTU1UXF3OWljaGU1d19nOWs2akJ5UjY5aW9XdG5DLVJXTFJpZV84c3FIT19UMmJJQ0pwbGFRTlBSeGZwZUEiLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
                "signature": "MEUCIDj-tI1yRGqnqd6uZeuInPaGY0yNYwC-5W4d024zwUs0AiEApJAst0t7G40ZRp1_TIKbftD-p9BkmafTPZBBe4Ps0P0",
                "userHandle": "Mg"
            },
            "type": "public-key",
            "clientExtensionResults": {},
            "authenticatorAttachment": "cross-platform"
        }
        webauthn_challenge = b'\xa2==\xce\xbb\x94\xca\xa5\x0c S\xb4\xa2^T\x96\xd5\x1d\xf7\x9eP\xab\x0fbr\x17\xb9\xc3\xf8=\x93\xa8\xc1\xc9\x1e\xbd\x8a\x85\xad\x9c/\x91X\xb4b{\xff,\xa8s\xbfOf\xc8\x08\x9aei\x03OG\x17\xe9x'
        self.env['auth.passkey.key']._verify_auth(auth, webauthn_challenge)
        # Replay attacks will raise an error
        with self.assertRaises(Exception):
            self.env['auth.passkey.key']._verify_auth(auth, webauthn_challenge)

    def test_verification(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'https://localhost:8888')
        # This is an emulated key by KeePassXC that does not support sign_count
        auth = {
            "id": "y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0",
            "rawId": "y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0",
            "response": {
                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAA",
                "clientDataJSON": "eyJjaGFsbGVuZ2UiOiJMTnBWMGRQSU10bXBTd0dlbklIX2gxVnljUXVBZ0ZnUVJKOVRQS0JvTmF5U2NOQUVyUy1yc25hVTE5bjdfQWFYemVpWVJnM25HSTN5dUgwYWk2VVBYQSIsImNyb3NzT3JpZ2luIjpmYWxzZSwib3JpZ2luIjoiaHR0cHM6Ly9sb2NhbGhvc3Q6ODg4OCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ",
                "signature": "MEYCIQCqkh2NBQQao5uDTaBKyNhiEpnk4jgbH-PjdLAul9-d0gIhAMObtNTbaEMUILdNgCT01BKNN4NHRzkzsGaDN2Ozu0WX",
                "userHandle": "Ng"
            },
            "type": "public-key",
            "clientExtensionResults": {},
            "authenticatorAttachment": "platform"
        }
        webauthn_challenge = b',\xdaU\xd1\xd3\xc82\xd9\xa9K\x01\x9e\x9c\x81\xff\x87Urq\x0b\x80\x80X\x10D\x9fS<\xa0h5\xac\x92p\xd0\x04\xad/\xab\xb2v\x94\xd7\xd9\xfb\xfc\x06\x97\xcd\xe8\x98F\r\xe7\x18\x8d\xf2\xb8}\x1a\x8b\xa5\x0f\\'
        with MockRequest(self.env) as request:
            request.session['webauthn_challenge'] = webauthn_challenge
            idcheck = self.env['res.users.identitycheck'].with_user(self.demo_user).create({'auth_method': 'passkey'})
            idcheck._check_identity(auth)
            # Due to lack of support of sign_count, replay attacks are possible
            # This is an accepted risk in order to increase compatbility with passkey implementations
            request.session['webauthn_challenge'] = webauthn_challenge
            idcheck = self.env['res.users.identitycheck'].with_user(self.demo_user).create({'auth_method': 'passkey'})
            idcheck._check_identity(auth)

    def test_verification_only_self(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'https://localhost:8888')
        auth = {
            "id": "y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0",
            "rawId": "y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0",
            "response": {
                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAA",
                "clientDataJSON": "eyJjaGFsbGVuZ2UiOiJMTnBWMGRQSU10bXBTd0dlbklIX2gxVnljUXVBZ0ZnUVJKOVRQS0JvTmF5U2NOQUVyUy1yc25hVTE5bjdfQWFYemVpWVJnM25HSTN5dUgwYWk2VVBYQSIsImNyb3NzT3JpZ2luIjpmYWxzZSwib3JpZ2luIjoiaHR0cHM6Ly9sb2NhbGhvc3Q6ODg4OCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ",
                "signature": "MEYCIQCqkh2NBQQao5uDTaBKyNhiEpnk4jgbH-PjdLAul9-d0gIhAMObtNTbaEMUILdNgCT01BKNN4NHRzkzsGaDN2Ozu0WX",
                "userHandle": "Ng"
            },
            "type": "public-key",
            "clientExtensionResults": {},
            "authenticatorAttachment": "platform"
        }
        webauthn_challenge = b',\xdaU\xd1\xd3\xc82\xd9\xa9K\x01\x9e\x9c\x81\xff\x87Urq\x0b\x80\x80X\x10D\x9fS<\xa0h5\xac\x92p\xd0\x04\xad/\xab\xb2v\x94\xd7\xd9\xfb\xfc\x06\x97\xcd\xe8\x98F\r\xe7\x18\x8d\xf2\xb8}\x1a\x8b\xa5\x0f\\'
        with self.assertRaises(AssertionError):
            with MockRequest(self.env) as request:
                request.session['webauthn_challenge'] = webauthn_challenge
                idcheck = self.env['res.users.identitycheck'].with_user(self.admin_user).create({'auth_method': 'passkey'})
                idcheck._check_identity(auth)
