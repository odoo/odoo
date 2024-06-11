import json
import random
import time

from odoo.exceptions import UserError
from odoo.http import _request_stack
from odoo.tools import DotDict, SQL

from odoo.tests.common import TransactionCase, get_db_name
from odoo.addons.website.tools import MockRequest


class PasskeyTest(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.admin_user = self.env.ref('base.user_admin')
        self.demo_user = self.env.ref('base.user_demo')

        query = '''
        INSERT INTO auth_passkey_key (name, credential_identifier, public_key, create_uid, write_date, create_date)
        VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
        '''

        self.cr.execute(SQL(
            query,
            'test-yubikey-nano',
            'c2dc34bbb0fcae9ee7abb5815850adfc5461107a54e841ef1204e7dc106277937e504e5af570b34bc35a56e87bc9d173',
            'pQECAyYgASFYIMLcNLuw_K6e56u1gVioLcAJF8v8eUw7kfqTOqDdl7nFIlggFSs_nZWewd_JqzeWzXmJ6Wmn_nKuo82rCdoOZ-oewOU=',
            self.admin_user.id,
        ))

        self.cr.execute(SQL(
            query,
            'test-keepassxc',
            'cba689549b2fbd24a46f04de199d456d03ff8c20e1a3b1013f066afb79408d0d',
            'pQECAyYgASFYICjw-NoCHMkYYbRo8Q4SgJ4tZc8BSEmuEI0XmA6hUqR_IlggjtuBgyhwnr7PqABF2o8vCniMVa7_mTG6_l9Pc4eI4mo=',
            self.demo_user.id,
        ))

        with MockRequest(self.env) as request:
            request.session['identity-check-last'] = time.time()
            request.session['webauthn_challenge'] = b'R\x86\xba3\x98\xc4?\xb27N\x8c\x8a\xf5\x004\xbd\xff\x08r\xc7\xb3}\xe2d\xd2\xb8,\xd6\x92\xd4Z\xb3 \x17\xdb\xdd\xd3\xee\xc3\xbf\x98\x95\xdf\x15\xbb\xaf\xbd>b\xa90y\x15\xe1\x00)\x83>hG*\xd0\x08y'
            yubikey = self.env['auth.passkey.key.name'].with_user(self.admin_user).create({'name': 'test-yubikey'})
            yubikey.make_key({
                "id": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                "rawId": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                "response": {
                    "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjCSZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2PFAAAAAgAAAAAAAAAAAAAAAAAAAAAAMC9qeo73FrgjE0ZpGRyqqr0G89A4ZNyWyTsdRfHIvfZ0jY5X8d2e55IoDHVAAi4IAaUBAgMmIAEhWCAvanqO9xa4IxNGaRkcMSyBudC-JDZYY9gyMqknP2IkUiJYINqumy9viKCeo_xpFU3XzyssfEReXvMM1_fmZN-wMpDPoWtjcmVkUHJvdGVjdAI",
                    "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiVW9hNk01akVQN0kzVG95SzlRQTB2ZjhJY3NlemZlSmswcmdzMXBMVVdyTWdGOXZkMC03RHY1aVYzeFc3cjcwLVlxa3dlUlhoQUNtRFBtaEhLdEFJZVEiLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
                    "transports": [
                    "nfc",
                    "usb"
                    ],
                    "publicKeyAlgorithm": -7,
                    "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEL2p6jvcWuCMTRmkZHDEsgbnQviQ2WGPYMjKpJz9iJFLarpsvb4ignqP8aRVN188rLHxEXl7zDNf35mTfsDKQzw",
                    "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2PFAAAAAgAAAAAAAAAAAAAAAAAAAAAAMC9qeo73FrgjE0ZpGRyqqr0G89A4ZNyWyTsdRfHIvfZ0jY5X8d2e55IoDHVAAi4IAaUBAgMmIAEhWCAvanqO9xa4IxNGaRkcMSyBudC-JDZYY9gyMqknP2IkUiJYINqumy9viKCeo_xpFU3XzyssfEReXvMM1_fmZN-wMpDPoWtjcmVkUHJvdGVjdAI"
                },
                "type": "public-key",
                "clientExtensionResults": {},
                "authenticatorAttachment": "cross-platform"
            })

    def setUp(self):
        super().setUp()
        # _login uses with registry(db).cursor() as cr
        self.env.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)

    def test_authentication(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://localhost:8069')
        # test-yubikey-nano
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
        with MockRequest(self.env) as request:
            request.session['webauthn_challenge'] = b'\xa2==\xce\xbb\x94\xca\xa5\x0c S\xb4\xa2^T\x96\xd5\x1d\xf7\x9eP\xab\x0fbr\x17\xb9\xc3\xf8=\x93\xa8\xc1\xc9\x1e\xbd\x8a\x85\xad\x9c/\x91X\xb4b{\xff,\xa8s\xbfOf\xc8\x08\x9aei\x03OG\x17\xe9x'
            credential = {'webauthn_response': json.dumps(auth), 'type': 'webauthn'}
            self.env['res.users']._login(get_db_name(), credential, None)
            # Replay attacks will raise an error
            with self.assertRaises(Exception):
                self.env['res.users']._login(get_db_name(), credential, None)

    def test_check_identity_admin(self):
        # test-yubikey
        auth = {
            "id": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
            "rawId": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
            "response": {
                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAw",
                "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiREtydzVJZUZpTDB3X3k1b0IwUkFUUHJxRzFlRk9DMlA3eUVpWENzdEJSdVpZYlNCQmtBV2ZoQUlJbmtNcVdqWUlOOHZiS243SjNQTVhfVGh6bkhwcWciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9","signature":"MEUCIQD5iaPp48QMS3amx4PS89kv_EBAo3bBkaWnLzWlSgFSXgIgLWKEv9xR_ZwVXZbw2zx459RKbrQuAcd-UqD4gJw1lWY",
                "userHandle": "Mg"
            },
            "type": "public-key",
            "clientExtensionResults": {},
            "authenticatorAttachment": "cross-platform"
        }
        webauthn_challenge = b'\x0c\xaa\xf0\xe4\x87\x85\x88\xbd0\xff.h\x07D@L\xfa\xea\x1bW\x858-\x8f\xef!"\\+-\x05\x1b\x99a\xb4\x81\x06@\x16~\x10\x08"y\x0c\xa9h\xd8 \xdf/l\xa9\xfb\'s\xcc_\xf4\xe1\xceq\xe9\xaa'
        with MockRequest(self.env) as request:
            request.session['webauthn_challenge'] = webauthn_challenge
            idcheck = self.env['res.users.identitycheck'].with_user(self.admin_user).create({'auth_method': 'webauthn'})
            idcheck.password = json.dumps(auth)
            idcheck._check_identity()

    def test_check_identity_demo(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'https://localhost:8888')
        # This is an emulated key by KeePassXC that does not support sign_count
        # test-keepassxc
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
            idcheck = self.env['res.users.identitycheck'].with_user(self.demo_user).create({'auth_method': 'webauthn'})
            idcheck.password = json.dumps(auth)
            idcheck._check_identity()
            # Due to lack of support of sign_count, we can replay the same request if we set the webauthn_challenge.
            # This increases compatibility with more authenticators and due to the random challenge, replay attacks are not possible.
            request.session['webauthn_challenge'] = webauthn_challenge
            idcheck = self.env['res.users.identitycheck'].with_user(self.demo_user).create({'auth_method': 'webauthn'})
            idcheck.password = json.dumps(auth)
            idcheck._check_identity()
        with self.assertRaises(KeyError):
            with MockRequest(self.env) as request:
                idcheck = self.env['res.users.identitycheck'].with_user(self.demo_user).create({'auth_method': 'webauthn'})
                idcheck.password = json.dumps(auth)
                idcheck._check_identity()
        with self.assertRaises(UserError):
            with MockRequest(self.env) as request:
                request.session['webauthn_challenge'] = random.randbytes(64)
                idcheck = self.env['res.users.identitycheck'].with_user(self.demo_user).create({'auth_method': 'webauthn'})
                idcheck.password = json.dumps(auth)
                idcheck._check_identity()

    def test_verification_only_self(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'https://localhost:8888')
        # test-keepassxc (belongs to demo_user)
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
        with self.assertRaises(UserError):
            with MockRequest(self.env) as request:
                request.session['webauthn_challenge'] = webauthn_challenge
                idcheck = self.env['res.users.identitycheck'].with_user(self.admin_user).create({'auth_method': 'webauthn'})
                idcheck.password = json.dumps(auth)
                idcheck._check_identity()
