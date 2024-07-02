import json

from contextlib import contextmanager
from lxml import etree
from unittest.mock import patch

from odoo.http import request
from odoo.tools import SQL, mute_logger

from odoo.tests.common import HttpCase


class PasskeyTest(HttpCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.admin_user = self.env.ref('base.user_admin')
        self.demo_user = self.env.ref('base.user_demo')

        # Hard-coded webauthn keys, challenges and responses, used in the below unit tests.
        self.passkeys = {
            'test-yubikey': {
                'user': self.admin_user,
                'credential_identifier': 'L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB',
                'public_key': 'pQECAyYgASFYIC9qeo73FrgjE0ZpGRwxLIG50L4kNlhj2DIyqSc_YiRSIlgg2q6bL2-IoJ6j_GkVTdfPKyx8RF5e8wzX9-Zk37AykM8=',
                'host': 'http://localhost:8069',
                'registration': {
                    'challenge': 'Uoa6M5jEP7I3ToyK9QA0vf8IcsezfeJk0rgs1pLUWrMgF9vd0-7Dv5iV3xW7r70-YqkweRXhACmDPmhHKtAIeQ',
                    'response': {
                        "id": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                        "rawId": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                        "response": {
                            "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjCSZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2PFAAAAAgAAAAAAAAAAAAAAAAAAAAAAMC9qeo73FrgjE0ZpGRyqqr0G89A4ZNyWyTsdRfHIvfZ0jY5X8d2e55IoDHVAAi4IAaUBAgMmIAEhWCAvanqO9xa4IxNGaRkcMSyBudC-JDZYY9gyMqknP2IkUiJYINqumy9viKCeo_xpFU3XzyssfEReXvMM1_fmZN-wMpDPoWtjcmVkUHJvdGVjdAI",
                            "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiVW9hNk01akVQN0kzVG95SzlRQTB2ZjhJY3NlemZlSmswcmdzMXBMVVdyTWdGOXZkMC03RHY1aVYzeFc3cjcwLVlxa3dlUlhoQUNtRFBtaEhLdEFJZVEiLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
                            "transports": [
                                "nfc",
                                "usb",
                            ],
                            "publicKeyAlgorithm": -7,
                            "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEL2p6jvcWuCMTRmkZHDEsgbnQviQ2WGPYMjKpJz9iJFLarpsvb4ignqP8aRVN188rLHxEXl7zDNf35mTfsDKQzw",
                            "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2PFAAAAAgAAAAAAAAAAAAAAAAAAAAAAMC9qeo73FrgjE0ZpGRyqqr0G89A4ZNyWyTsdRfHIvfZ0jY5X8d2e55IoDHVAAi4IAaUBAgMmIAEhWCAvanqO9xa4IxNGaRkcMSyBudC-JDZYY9gyMqknP2IkUiJYINqumy9viKCeo_xpFU3XzyssfEReXvMM1_fmZN-wMpDPoWtjcmVkUHJvdGVjdAI"
                        },
                        "type": "public-key",
                        "clientExtensionResults": {},
                        "authenticatorAttachment": "cross-platform"
                    }
                },
                'auth': {
                    'challenge': 'DKrw5IeFiL0w_y5oB0RATPrqG1eFOC2P7yEiXCstBRuZYbSBBkAWfhAIInkMqWjYIN8vbKn7J3PMX_ThznHpqg',
                    'response': {
                        "id": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                        "rawId": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                        "response": {
                            "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAw",
                            "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiREtydzVJZUZpTDB3X3k1b0IwUkFUUHJxRzFlRk9DMlA3eUVpWENzdEJSdVpZYlNCQmtBV2ZoQUlJbmtNcVdqWUlOOHZiS243SjNQTVhfVGh6bkhwcWciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
                            "signature": "MEUCIQD5iaPp48QMS3amx4PS89kv_EBAo3bBkaWnLzWlSgFSXgIgLWKEv9xR_ZwVXZbw2zx459RKbrQuAcd-UqD4gJw1lWY",
                            "userHandle": "Mg"
                        },
                        "type": "public-key",
                        "clientExtensionResults": {},
                        "authenticatorAttachment": "cross-platform",
                    },
                },
            },
            'test-yubikey-nano': {
                'user': self.admin_user,
                'credential_identifier': 'wtw0u7D8rp7nq7WBWFCt_FRhEHpU6EHvEgTn3BBid5N-UE5a9XCzS8NaVuh7ydFz',
                'public_key': 'pQECAyYgASFYIMLcNLuw_K6e56u1gVioLcAJF8v8eUw7kfqTOqDdl7nFIlggFSs_nZWewd_JqzeWzXmJ6Wmn_nKuo82rCdoOZ-oewOU=',
                'host': 'http://localhost:8069',
                'auth': {
                    'challenge': 'oj09zruUyqUMIFO0ol5UltUd955Qqw9iche5w_g9k6jByR69ioWtnC-RWLRie_8sqHO_T2bICJplaQNPRxfpeA',
                    'response': {
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
                        "authenticatorAttachment": "cross-platform",
                    }
                },
            },
            'test-keepassxc': {
                'user': self.demo_user,
                'credential_identifier': 'y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0',
                'public_key': 'pQECAyYgASFYICjw-NoCHMkYYbRo8Q4SgJ4tZc8BSEmuEI0XmA6hUqR_IlggjtuBgyhwnr7PqABF2o8vCniMVa7_mTG6_l9Pc4eI4mo=',
                'host': 'https://localhost:8888',
                'supports_sign_count': False,  # keepassxc doesn't support sign_count
                'auth': {
                    'challenge': 'LNpV0dPIMtmpSwGenIH_h1VycQuAgFgQRJ9TPKBoNayScNAErS-rsnaU19n7_AaXzeiYRg3nGI3yuH0ai6UPXA',
                    'response': {
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
                        "authenticatorAttachment": "platform",
                    }
                },
            }
        }

        for key, values in self.passkeys.items():
            self.cr.execute(SQL(
                """
                INSERT INTO auth_passkey_key (name, credential_identifier, public_key, create_uid, write_date, create_date)
                VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
                RETURNING id
                """, key, values['credential_identifier'], values['public_key'], values['user'].id,
            ))
            passkey_id = self.cr.fetchone()
            values['passkey'] = self.env['auth.passkey.key'].browse(passkey_id)

    def rpc(self, model, method, *args, **kwargs):
        return self.url_open('/web/dataset/call_kw', headers={"Content-Type": "application/json"}, data=json.dumps({
                "params": {
                    'model': model,
                    'method': method,
                    'args': args,
                    'kwargs': kwargs,
                },
            })).json()

    @contextmanager
    def patch_start_auth(self, challenge):
        """Force the webauthn challenge for unit tests testing the authentication"""
        origin_start_auth = self.env.registry['auth.passkey.key']._start_auth

        def _start_auth(self):
            res = origin_start_auth(self)
            res['challenge'] = request.session['webauthn_challenge'] = challenge
            return res

        with patch.object(self.env.registry['auth.passkey.key'], '_start_auth', _start_auth):
            yield

    @contextmanager
    def patch_start_registration(self, challenge):
        """Force the webauthn challenge for unit tests testing the registration"""
        origin_start_registration = self.env.registry['auth.passkey.key']._start_registration

        def _start_registration(self):
            res = origin_start_registration(self)
            res['challenge'] = request.session['webauthn_challenge'] = challenge
            return res

        with patch.object(self.env.registry['auth.passkey.key'], '_start_registration', _start_registration):
            yield

    def test_registration(self):
        passkey = self.passkeys['test-yubikey']
        registration = passkey['registration']
        webauthn_challenge, webauthn_response = registration['challenge'], registration['response']
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', passkey['host'])
        with self.patch_start_registration(webauthn_challenge):
            # Remove existing user passkeys so the check identity ask for a password authentication by default.
            # To mimic the behavior when a user has no passkeys set yet.
            self.admin_user.auth_passkey_key_ids.unlink()

            # Authenticate the user, as the goal here is to create a new passkey for an already authenticated user.
            self.authenticate(self.admin_user.login, self.admin_user.login)

            # Click the "Add Passkey" button.
            wizard_id = self.rpc('res.users', 'action_create_passkey', self.admin_user.id)['result']['res_id']

            # Adding a passkey triggers an identity check. Confirm using the password and run the check.
            self.rpc('res.users.identitycheck', 'write', wizard_id, {'password': self.admin_user.login})
            action = self.rpc('res.users.identitycheck', 'run_check', wizard_id)['result']

            # Create the passkey creation wizard and set a name for the key
            wizard_id = self.rpc(action['res_model'], 'create', {'name': 'test-yubikey'})['result']

            # Make the key with the webauthn response
            response = self.rpc(action['res_model'], 'make_key', wizard_id, webauthn_response)

            # Assert the passkey registration is successful
            self.assertTrue(response.get('result'))
            self.assertFalse(response.get('error'))
            self.assertEqual(len(self.admin_user.auth_passkey_key_ids), 1)
            self.assertEqual(self.admin_user.auth_passkey_key_ids.name, 'test-yubikey')
            self.assertEqual(self.admin_user.auth_passkey_key_ids.sign_count, 0)

    def test_authentication(self):
        for passkey in self.passkeys.values():
            auth = passkey['auth']
            webauthn_challenge, webauthn_response = auth['challenge'], auth['response']
            self.env['ir.config_parameter'].sudo().set_param('web.base.url', passkey['host'])
            sign_count = passkey['passkey'].sign_count

            with self.patch_start_auth(webauthn_challenge):
                # Mimic a user login process

                # 1. Open the /web/login page, and get the csrf token which is use to protect the POST request
                csrf_token = etree.fromstring(
                    self.url_open('/web/login').content
                ).xpath('//input[@name="csrf_token"]')[0].get('value')

                # 2. Call the below route to start the webauthn authentication process
                # which is done in the web interface when clicking on "Login with a passkey"
                # It sets the webauthn challenge in the session
                self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})

                # 3. POST the login using the webauthn response
                response = self.url_open('/web/login', data={
                    'type': 'webauthn',
                    'webauthn_response': json.dumps(webauthn_response),
                    'csrf_token': csrf_token,
                    'password': '',  # Currently mandatory because of `if request.params['password'] != 'admin':`
                })

                # Assert the login is successful
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.headers.get('Set-Cookie'))
                if passkey.get('supports_sign_count', True):
                    # If the passkey supports sign counts, the sign count increases
                    self.assertGreater(passkey['passkey'].sign_count, sign_count)
                else:
                    # Otherwise it doesn't
                    self.assertEqual(passkey['passkey'].sign_count, sign_count)

                # Replay attacks raises an error
                csrf_token = etree.fromstring(
                    self.url_open('/web/login').content
                ).xpath('//input[@name="csrf_token"]')[0].get('value')
                response = self.url_open('/web/login', data={
                    'type': 'webauthn',
                    'webauthn_response': json.dumps(webauthn_response),
                    'csrf_token': csrf_token,
                })
                self.assertEqual(response.status_code, 200)
                error = etree.fromstring(response.content).xpath('//p[@class="alert alert-danger"]')[0].text.strip()
                self.assertEqual(error, 'Cannot find a challenge for this session')

    def test_check_identity(self):
        for passkey in self.passkeys.values():
            user, auth = passkey['user'], passkey['auth']
            webauthn_challenge, webauthn_response = auth['challenge'], auth['response']
            self.env['ir.config_parameter'].sudo().set_param('web.base.url', passkey['host'])
            sign_count = passkey['passkey'].sign_count

            with self.patch_start_auth(webauthn_challenge):
                # Authenticate the user, as the goal here is to assert the `check_identity`
                self.authenticate(user.login, user.login)

                # Call a method which triggers an identity check
                wizard_id = self.rpc('res.users', 'preference_change_password', user.id)['result']['res_id']

                # Mimic what the Javascript code is doing when clicking on the button "Use a passkey"

                # 1. Call the below route to start the webauthn authentication process
                # It sets the webauthn challenge in the session
                self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})

                # 2. Set the webauthn response in the password field
                self.rpc('res.users.identitycheck', 'write', wizard_id, {'password': json.dumps(webauthn_response)})

                # 3. Call the check method, which if successful returns the action to run following the identity check
                response = self.rpc('res.users.identitycheck', 'run_check', wizard_id)

                # Assert the identity check is successful
                self.assertTrue(response.get('result'))
                self.assertFalse(response.get('error'))
                if passkey.get('supports_sign_count', True):
                    self.assertGreater(passkey['passkey'].sign_count, sign_count)
                    sign_count = passkey['passkey'].sign_count
                else:
                    self.assertEqual(passkey['passkey'].sign_count, sign_count)

                # 4. Attempt a replay attack, without reseting the challenge
                self.rpc('res.users.identitycheck', 'write', wizard_id, {'password': json.dumps(webauthn_response)})
                with mute_logger('odoo.http'):
                    response = self.rpc('res.users.identitycheck', 'run_check', wizard_id)

                # Assert the authentication failed
                self.assertFalse(response.get('result'))
                self.assertTrue(response.get('error'))
                self.assertEqual(response['error']['data']['name'], 'odoo.exceptions.UserError')
                self.assertEqual(
                    response['error']['data']['message'],
                    'Incorrect Passkey. Please provide a valid passkey or use a different authentication method.'
                )
                # The authentication fail, hence the sign count doesn't increase
                self.assertEqual(passkey['passkey'].sign_count, sign_count)

                # 5. Do a second authentication with the same challenge and same response

                # Reset the challenge, which is forced to the same challenge with a mock patch above
                self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})

                # Write the same webauthn response
                self.rpc('res.users.identitycheck', 'write', wizard_id, {'password': json.dumps(webauthn_response)})
                with mute_logger('odoo.http'):
                    response = self.rpc('res.users.identitycheck', 'run_check', wizard_id)

                if passkey.get('supports_sign_count', True):
                    # If the passkey supports sign_count, a replay attack with the same challenge must fail
                    self.assertFalse(response.get('result'))
                    self.assertTrue(response.get('error'))
                else:
                    # If the passkey doesn't support sign_count, such as keepassxc, then it should success
                    self.assertTrue(response.get('result'))
                    self.assertFalse(response.get('error'))

                self.assertEqual(passkey['passkey'].sign_count, sign_count)

            # 6. Do a third authentication, with another challenge but the same reponse
            # This block is outside the block `with self.patch_start_auth(webauthn_challenge):`
            # hence it will generate a random challenge.
            self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})
            self.rpc('res.users.identitycheck', 'write', wizard_id, {'password': json.dumps(webauthn_response)})
            with mute_logger('odoo.http'):
                response = self.rpc('res.users.identitycheck', 'run_check', wizard_id)
            self.assertFalse(response.get('result'))
            self.assertTrue(response.get('error'))
            self.assertEqual(passkey['passkey'].sign_count, sign_count)
