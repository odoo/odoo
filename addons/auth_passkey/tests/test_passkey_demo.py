import json

from contextlib import contextmanager
from lxml import etree
from unittest.mock import patch

from odoo.http import request
from odoo.tests import tagged
from odoo.tools import SQL, mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


class PasskeyTest(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.admin_user = self.env.ref('base.user_admin')

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
                'user': self.user_demo,
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
            },
            'test-user-verification': {
                'user': self.user_demo,
                'credential_identifier': '723TCjL_RdQHFk3Ysp-HUymcWoazFi3ZdfZ1bIn6MYC5bAXvI6B-j8G-UA1taMO0',
                'public_key': 'pQECAyYgASFYIO9t0woy_0XUBxZN2LKpzFmzmauPpdgt7B1EnoVXHL56IlggUJWIu-UCOAFOCAMUXDXb36pJ49aWNI9Z7njiLQt7amw=',
                'host': 'http://localhost:8069',
                'auth': {
                    'challenge': 'MTIzNDU',
                    'response': {
                        'id': '723TCjL_RdQHFk3Ysp-HUymcWoazFi3ZdfZ1bIn6MYC5bAXvI6B-j8G-UA1taMO0',
                        'rawId': '723TCjL_RdQHFk3Ysp-HUymcWoazFi3ZdfZ1bIn6MYC5bAXvI6B-j8G-UA1taMO0',
                        'response': {
                            'authenticatorData': 'SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAADg',
                            'clientDataJSON': 'eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiTVRJek5EVSIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6ODA2OSIsImNyb3NzT3JpZ2luIjpmYWxzZX0',
                            'signature': 'MEQCIFYAdM82D9otAfX2s6WY4CyH8i733Km-3TZSYcfwDmbqAiB6OXGuoaMgX13v6LWCIdkCRY9ZTYhNzhXFTs1Wp7-zkQ',
                            'userHandle': 'Mg'
                        },
                        'type': 'public-key',
                        'clientExtensionResults': {},
                        'authenticatorAttachment': 'cross-platform'
                    }
                },
            },
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
            action = self.rpc('res.users.identitycheck', 'run_check', wizard_id,
                context={'password': self.admin_user.login}
            )['result']

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
        for key in ['test-yubikey', 'test-yubikey-nano', 'test-keepassxc']:
            passkey = self.passkeys[key]
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
        for key in ['test-yubikey', 'test-yubikey-nano', 'test-keepassxc']:
            passkey = self.passkeys[key]
            user, auth = passkey['user'], passkey['auth']
            webauthn_challenge, webauthn_response = auth['challenge'], auth['response']
            self.env['ir.config_parameter'].sudo().set_param('web.base.url', passkey['host'])
            sign_count = passkey['passkey'].sign_count

            with self.patch_start_auth(webauthn_challenge):
                # Authenticate the user, as the goal here is to assert the `check_identity`
                self.authenticate(user.login, user.login)

                # Call a method which triggers an identity check
                wizard_id = self.rpc('res.users', 'api_key_wizard', user.id)['result']['res_id']

                # Mimic what the Javascript code is doing when clicking on the button "Use a passkey"

                # 1. Call the below route to start the webauthn authentication process
                # It sets the webauthn challenge in the session
                self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})

                # 2. Call the check method with the webauthn response in the password,
                # which if successful returns the action to run following the identity check
                response = self.rpc('res.users.identitycheck', 'run_check', wizard_id,
                    context={'password': json.dumps(webauthn_response)}
                )

                # Assert the identity check is successful
                self.assertTrue(response.get('result'))
                self.assertFalse(response.get('error'))
                if passkey.get('supports_sign_count', True):
                    self.assertGreater(passkey['passkey'].sign_count, sign_count)
                    sign_count = passkey['passkey'].sign_count
                else:
                    self.assertEqual(passkey['passkey'].sign_count, sign_count)

                # 3. Attempt a replay attack, without reseting the challenge
                with mute_logger('odoo.http'):
                    response = self.rpc('res.users.identitycheck', 'run_check', wizard_id,
                        context={'password': json.dumps(webauthn_response)}
                    )

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

                # 4. Do a second authentication with the same challenge and same response

                # Reset the challenge, which is forced to the same challenge with a mock patch above
                self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})

                # Write the same webauthn response
                with mute_logger('odoo.http'):
                    response = self.rpc('res.users.identitycheck', 'run_check', wizard_id,
                        context={'password': json.dumps(webauthn_response)}
                    )

                if passkey.get('supports_sign_count', True):
                    # If the passkey supports sign_count, a replay attack with the same challenge must fail
                    self.assertFalse(response.get('result'))
                    self.assertTrue(response.get('error'))
                else:
                    # If the passkey doesn't support sign_count, such as keepassxc, then it should success
                    self.assertTrue(response.get('result'))
                    self.assertFalse(response.get('error'))

                self.assertEqual(passkey['passkey'].sign_count, sign_count)

            # 5. Do a third authentication, with another challenge but the same reponse
            # This block is outside the block `with self.patch_start_auth(webauthn_challenge):`
            # hence it will generate a random challenge.
            self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})
            with mute_logger('odoo.http'):
                response = self.rpc('res.users.identitycheck', 'run_check', wizard_id,
                    context={'password': json.dumps(webauthn_response)}
                )
            self.assertFalse(response.get('result'))
            self.assertTrue(response.get('error'))
            self.assertEqual(passkey['passkey'].sign_count, sign_count)

    def test_check_user_verification(self):
        """Asserts authenticating without user verification (not entering the PIN code of the passkey) is prevented.

        In addition to ask the browser to require the user verification
        during the preparation of the webauthn authentication options,
        the fact the user verification actually happened must be verified, server-side.

        In the webauthn protocol, the fact the user verification happened
        is stored by the browser in the `authenticatorData`,
        in the 33rd byte "flags", in the 2nd bit "User Verified (UV)".
        https://www.w3.org/TR/webauthn-1/#sec-authenticator-data

        In the webauthn response provided in the setup class above, the `authenticatorData` provided
        does not have the user verification flag.
        This response should therefore not be allowed for authentication,
        as we want to require the user to enter his PIN code (User Verification, UV)
        in addition to touching the key (User Presence, UP) to act as a 2 factor authentication:
        Something you have + Something you know.

        Then, we replay the same authentication, with the same challenge,
        but this time with an authenticator data with the user verified,
        and an updated signature with this new authenticator data,
        and then the authentication can be allowed.
        """
        passkey = self.passkeys['test-user-verification']
        webauthn_challenge, webauthn_response = passkey['auth']['challenge'], passkey['auth']['response']
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', passkey['host'])

        with self.patch_start_auth(webauthn_challenge):
            csrf_token = etree.fromstring(
                self.url_open('/web/login').content
            ).xpath('//input[@name="csrf_token"]')[0].get('value')
            self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})
            response = self.url_open('/web/login', data={
                'type': 'webauthn',
                'webauthn_response': json.dumps(webauthn_response),
                'csrf_token': csrf_token,
                'password': '',
            })
            # Login unsuccessful, redirected back to /web/login
            self.assertTrue(response.url.endswith('/web/login'))
            # with the error message
            error = etree.fromstring(response.content).xpath('//p[@class="alert alert-danger"]')[0].text.strip()
            self.assertEqual(error, 'User verification is required but user was not verified during authentication')

            # New authenticator data with the user verification bit turned on (+ counter increased)
            # Previous authenticator data without user verified:    SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAADg
            # New authenticator data with user verified:            SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAFQ
            # Only the end changes, as:
            # - An Authenticator Data is 37 bytes long
            # - The user verified (UV) is on the 33rd byte
            # - The counter is from the 34th byte to the 37th byte
            # https://www.w3.org/TR/webauthn-1/#sec-authenticator-data
            # To see the 33rd byte "flags" change:
            # ```py
            # import base64
            # flags = base64.urlsafe_b64decode(authenticator_data + '==')[32:33]
            # print(f'{flags[0]:08b}')
            # ```
            # Without the User Verified authenticator data, the above code prints `00000001`
            # With the User Verified authenticator data, the above code prints `00000101`
            # bit 0 is the least significant bit:
            # - Bit 0: User Present (UP)
            # - Bit 2: User Verified (UV)
            # The counter is from byte 34 to 37. To get the counter:
            # `int.from_bytes(base64.urlsafe_b64decode(authenticator_data + '==')[33:37])`
            # In the case of the authenticator data without user verified, the counter is 14
            # In the case of the authenticator data with user verified, the counter is 21
            # The response with the invalid authenticator data, without the UV flag
            # must be played before the response with the valid authenticator data,
            # as its counter is lower. Otherwise you would have another error in addition to the missing UV flag:
            # `Response sign count of 14 was not greater than current count of 21`
            webauthn_response['response']['authenticatorData'] = 'SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAFQ'
            # Signature changes as the authenticator data changed.
            webauthn_response['response']['signature'] = 'MEQCIAdcWwNtQVrklYo70p5eHjVdSkA4Pgk6hbCCT6O8-V0BAiBBVKgroyNNOqN5xwO6Rr4yJV61J1TGWoOyUsoUftjypw'

            csrf_token = etree.fromstring(
                self.url_open('/web/login').content
            ).xpath('//input[@name="csrf_token"]')[0].get('value')
            self.url_open('/auth/passkey/start-auth', '{}', headers={"Content-Type": "application/json"})
            response = self.url_open('/web/login', data={
                'type': 'webauthn',
                'webauthn_response': json.dumps(webauthn_response),
                'csrf_token': csrf_token,
                'password': '',
            })

            # Login successful, redirected to /odoo
            self.assertTrue(response.url.endswith('/odoo'))


@tagged('post_install', '-at_install')
class PasskeyTestTours(PasskeyTest):
    def test_passkey_login(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', self.passkeys['test-keepassxc']['host'])
        with self.patch_start_auth(self.passkeys['test-keepassxc']['auth']['challenge']):
            self.start_tour("/web/login?debug=tests", 'passkeys_tour_login')

    def test_passkey_backend(self):
        # All these tests rely on each other but had to be split up to patch different methods.
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', self.passkeys['test-yubikey']['host'])
        self.admin_user.tz = 'UTC'  # workaround to fix timezone not being set so you are unable to click any buttons on the profile page
        self.admin_user.auth_passkey_key_ids.unlink()
        with self.patch_start_registration(self.passkeys['test-yubikey']['registration']['challenge']):
            self.start_tour("/odoo?debug=tests", 'passkeys_tour_registration', login="admin")
        with self.patch_start_auth(self.passkeys['test-yubikey']['auth']['challenge']):
            self.start_tour("/odoo?debug=tests", 'passkeys_tour_verify', login="admin")
        self.start_tour("/odoo?debug=tests", 'passkeys_tour_delete', login="admin")
