import base64
from unittest.mock import patch

from odoo import Command
from odoo.tests import new_test_user, tagged

from odoo.addons.auth_oauth_server.controllers.oauth_server_controller import OauthServerController

from .common import REDIRECT_URI, OauthServerCommon


@tagged('post_install', '-at_install')
class TestAccessTokenGeneration(OauthServerCommon):

    def test_full_authorization_code_exchange_generates_access_token(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')

        code = self._generate_auth_code(client_id=client_id)
        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 200, response.text)
        response_json = response.json()
        self.assertEqual(response_json['scope'], 'testrs')
        self.assertEqual(response_json['token_type'], 'Bearer')

        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=response_json['access_token'])
        self.assertEqual(uid, self.internal_user.id)

    def test_oauth_token_is_named_correctly(self):
        # Without passing client_name, the token will be named using the name of the registered client.
        registration = self._register_client()
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=registration['client_id'])
        self._generate_access_token(code, client_id=registration['client_id'], client_secret=registration['client_secret'])

        oauth_token = self.env['oauth.token'].search([('user_id', '=', self.internal_user.id)])
        self.assertEqual(oauth_token.name, 'Test Client')

        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        # Passing client_name overrides the name of the registered client for the token.
        token_generation_response = self._generate_access_token(
            code, client_id=client_id, client_secret=client_secret, client_name='ChatGPT',
        ).json()

        access_token = self.env['oauth.access.token']._retrieve_record(access_token=token_generation_response['access_token'])
        oauth_token = access_token.oauth_token_id
        self.assertEqual(oauth_token.name, 'ChatGPT')

        # Rotating the refresh token keeps the name of the application.
        token_rotation_response = self._redeem_refresh_token(
            refresh_token=token_generation_response['refresh_token'], client_id=client_id, client_secret=client_secret,
        ).json()
        rotated_access_token = self.env['oauth.access.token']._retrieve_record(access_token=token_rotation_response['access_token'])
        rotated_token = rotated_access_token.oauth_token_id
        self.assertEqual(rotated_token.name, 'ChatGPT')

    def test_access_token_is_not_valid_for_another_scope(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        access_token = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()['access_token']

        uid = self.env['oauth.access.token']._check_credentials(scope='other_scope', access_token=access_token)
        self.assertIsNone(uid)

    def test_client_secret_basic_authenticates_via_authorization_header(self):
        # client_secret_basic sends client_id/client_secret in the HTTP Basic Authorization header.
        registration = self._register_client(auth_method='client_secret_basic')
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')

        base_auth_header = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
        code = self._generate_auth_code(client_id=client_id)
        response = self._generate_access_token(code, headers={'Authorization': f'Basic {base_auth_header}'})
        self.assertEqual(response.status_code, 200, response.text)
        response_json = response.json()
        self.assertEqual(response_json['scope'], 'testrs')
        self.assertEqual(response_json['token_type'], 'Bearer')
        self.assertIn('access_token', response_json)
        self.assertIn('refresh_token', response_json)

    def test_missing_client_id_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        response = self._generate_access_token(code, client_secret=client_secret)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'invalid_client')

    def test_wrong_client_secret_is_rejected(self):
        client_id = self._register_client()['client_id']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        response = self._generate_access_token(code, client_id=client_id, client_secret='wrong-secret')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'invalid_client')

    def test_token_endpoint_validates_client_credentials(self):
        client = self._register_client()
        token_result = {
            'access_token': 'access_token', 'refresh_token': 'refresh_token',
            'token_type': 'Bearer', 'expires_in': 600, 'scope': 'testrs',
        }
        with patch.object(
            OauthServerController, '_redeem_authorization_code', return_value=token_result,
        ) as redeem_authorization_code_mock:
            response = self._generate_access_token(
                'authorization_code', client_id=client['client_id'], client_secret='wrong-secret',
            )
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()['error'], 'invalid_client')
            self.assertEqual(response.json()['error_description'], "Invalid client credentials")
            redeem_authorization_code_mock.assert_not_called()

            response = self._generate_access_token(
                'authorization_code', client_id=client['client_id'], client_secret=client['client_secret'],
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), token_result)
            redeem_authorization_code_mock.assert_called_once()

    def test_wrong_code_verifier_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        response = self._generate_access_token(
            code, client_id=client_id, client_secret=client_secret, code_verifier='wrong-verifier',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')

    def test_code_cannot_be_redeemed_twice(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)

        first_redeem_response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(first_redeem_response.status_code, 200)
        self.assertIn('access_token', first_redeem_response.json())
        second_redeem_response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(second_redeem_response.status_code, 400)
        self.assertEqual(second_redeem_response.json()['error'], 'invalid_grant')

    def test_redirect_uri_mismatch_at_token_is_rejected(self):
        registration = self._register_client(redirect_uris=[REDIRECT_URI, 'https://other.example.com/cb'])
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id, redirect_uri=REDIRECT_URI)
        response = self._generate_access_token(
            code, client_id=client_id, client_secret=client_secret,
            redirect_uri='https://other.example.com/cb',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')

    def test_loopback_redirect_uri_port_must_match_exactly_at_token(self):
        registration = self._register_client(redirect_uris=['http://127.0.0.1:8080/cb'])
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')

        code = self._generate_auth_code(client_id=client_id, redirect_uri='http://127.0.0.1:54321/cb')
        response = self._generate_access_token(
            code, client_id=client_id, client_secret=client_secret,
            redirect_uri='http://127.0.0.1:9999/cb',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')

        response = self._generate_access_token(
            code, client_id=client_id, client_secret=client_secret,
            redirect_uri='http://127.0.0.1:54321/cb',
        )
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response_json)
        self.assertIn('refresh_token', response_json)

    def test_refresh_token_rotation_generates_new_access_token_and_revokes_old(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        access_token_generation_response_json = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        access_token_rotation_response = self._redeem_refresh_token(
            refresh_token=access_token_generation_response_json['refresh_token'],
            client_id=client_id,
            client_secret=client_secret,
        )
        self.assertEqual(access_token_rotation_response.status_code, 200, access_token_rotation_response.text)
        access_token_rotation_response_json = access_token_rotation_response.json()
        self.assertNotEqual(access_token_rotation_response_json['access_token'], access_token_generation_response_json['access_token'])
        self.assertNotEqual(access_token_rotation_response_json['refresh_token'], access_token_generation_response_json['refresh_token'])

        old_uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=access_token_generation_response_json['access_token'])
        self.assertIsNone(old_uid)
        new_uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=access_token_rotation_response_json['access_token'])
        self.assertEqual(new_uid, self.internal_user.id)

    def test_replayed_refresh_token_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        access_token_generation_response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()
        refresh_token_first_redemption_response_json = self._redeem_refresh_token(
            refresh_token=access_token_generation_response['refresh_token'],
            client_id=client_id,
            client_secret=client_secret,
        ).json()

        refresh_token_second_redemption_response = self._redeem_refresh_token(
            refresh_token=access_token_generation_response['refresh_token'],
            client_id=client_id,
            client_secret=client_secret,
        )
        refresh_token_second_redemption_response_json = refresh_token_second_redemption_response.json()
        self.assertEqual(refresh_token_second_redemption_response.status_code, 400)
        self.assertEqual(refresh_token_second_redemption_response_json['error'], 'invalid_grant')

        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=refresh_token_first_redemption_response_json['access_token'])
        self.assertEqual(uid, self.internal_user.id)

    def test_access_denied_at_redemption_if_user_lost_resource_access(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        self.internal_user.write({'group_ids': [Command.unlink(self.env.ref('base.group_user').id)]})

        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'invalid_grant')

    def test_access_denied_at_redemption_if_resource_groups_changed(self):
        client_data = self._register_client()
        client_id, client_secret = client_data['client_id'], client_data['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)

        # Same user, but the resource itself is restricted to a group they aren't in after
        # the code was issued: the code must not be redeemable for an access token anymore.
        self.resource.allowed_group_ids = self.env.ref('base.group_system')

        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')
        self.assertFalse(self.env['oauth.access.token'].search([
            ('oauth_token_id.user_id', '=', self.internal_user.id),
            ('oauth_token_id.scope', '=', self.resource.access_token_scope),
        ]))

    def test_revoke_disables_the_refresh_token(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        revoke_response = self._revoke(
            client_id=client_id,
            client_secret=client_secret,
            token=tokens['refresh_token'],
        )
        self.assertEqual(revoke_response.status_code, 200)
        # Assert access token has been revoked.
        self.assertIsNone(self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token']))
        # Assert refresh token has been revoked.
        refresh_token_redemption_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'],
            client_id=client_id,
            client_secret=client_secret,
        )
        self.assertEqual(refresh_token_redemption_response.status_code, 400)
        self.assertEqual(refresh_token_redemption_response.json()['error'], 'invalid_grant')

    def test_removing_the_oauth_token_removes_the_access_token(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()
        oauth_token = self.env['oauth.token'].search([('user_id', '=', self.internal_user.id)])
        self.assertTrue(oauth_token)
        access_token = oauth_token.access_token_ids
        refresh_token = oauth_token.refresh_token_ids

        oauth_token.unlink()
        self.assertFalse(oauth_token.exists())
        self.assertFalse(access_token.exists())
        self.assertFalse(refresh_token.exists())

        refresh_token_redemption_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'],
            client_id=client_id,
            client_secret=client_secret,
        )
        self.assertEqual(refresh_token_redemption_response.status_code, 400)
        self.assertEqual(refresh_token_redemption_response.json()['error'], 'invalid_grant')

    def test_removing_the_access_token_removes_the_oauth_token(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()
        oauth_token = self.env['oauth.token'].search([('user_id', '=', self.internal_user.id)])
        access_token = oauth_token.access_token_ids
        refresh_token = oauth_token.refresh_token_ids

        access_token._remove()
        self.assertFalse(access_token.exists())
        self.assertFalse(oauth_token.exists())
        self.assertFalse(refresh_token.exists())

        refresh_token_redemption_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'],
            client_id=client_id,
            client_secret=client_secret,
        )
        self.assertEqual(refresh_token_redemption_response.status_code, 400)

    def test_autovacuumed_access_token_keeps_the_refresh_token(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()
        oauth_token = self.env['oauth.token'].search([('user_id', '=', self.internal_user.id)])
        access_token = oauth_token.access_token_ids
        refresh_token = oauth_token.refresh_token_ids
        # The access token expires days before its refresh token, so the vacuum reaches it first.
        self.env.cr.execute(
            "UPDATE oauth_access_token SET expiration_date = now() - interval '1 day' WHERE id = %s",
            [access_token.id],
        )
        self.env['oauth.access.token']._gc_expired_access_tokens()
        oauth_token.invalidate_recordset()

        self.assertFalse(access_token.exists())
        self.assertTrue(oauth_token.exists())
        self.assertTrue(refresh_token.exists())

    def test_revoke_of_access_token_requires_matching_client(self):
        # A client presenting a token it doesn't own must still see 200 -
        # the caller can't be allowed to distinguish "not yours" from "revoked".
        owner_registration = self._register_client()
        owner_client_id, owner_client_secret = owner_registration['client_id'], owner_registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=owner_client_id)
        tokens = self._generate_access_token(code, client_id=owner_client_id, client_secret=owner_client_secret).json()

        other_registration = self._register_client()
        other_client_id, other_client_secret = other_registration['client_id'], other_registration['client_secret']
        revoke_response = self.url_open('/oauth/revoke', data={
            'client_id': other_client_id, 'client_secret': other_client_secret, 'token': tokens['access_token'],
        })
        self.assertEqual(revoke_response.status_code, 200)

        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token'])
        self.assertEqual(uid, self.internal_user.id)

    def test_revoke_validates_client_credentials(self):
        public_client = self._register_client(auth_method='none')
        confidential_client = self._register_client()

        with patch.object(OauthServerController, '_handle_revoke_request') as handle_revoke_mock:
            response = self._revoke('some-token', client_id='unknown_client_id', client_secret=None)
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()['error'], 'invalid_client')
            self.assertEqual(response.json()['error_description'], "Invalid client credentials")
            handle_revoke_mock.assert_not_called()

            response = self._revoke('some-token', client_id=public_client['client_id'], client_secret=None)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), {})
            handle_revoke_mock.assert_called_once()
            handle_revoke_mock.reset_mock()

            response = self._revoke(
                'some-token', client_id=confidential_client['client_id'], client_secret='wrong-secret',
            )
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()['error'], 'invalid_client')
            self.assertEqual(response.json()['error_description'], "Invalid client credentials")
            handle_revoke_mock.assert_not_called()

            response = self._revoke(
                'some-token',
                client_id=confidential_client['client_id'],
                client_secret=confidential_client['client_secret'],
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), {})
            handle_revoke_mock.assert_called_once()

    def test_single_client_can_generate_multiple_tokens_for_the_same_user(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')

        first_code = self._generate_auth_code(client_id=client_id)
        first_tokens = self._generate_access_token(first_code, client_id=client_id, client_secret=client_secret).json()
        second_code = self._generate_auth_code(client_id=client_id)
        second_tokens = self._generate_access_token(second_code, client_id=client_id, client_secret=client_secret).json()

        self.assertNotEqual(first_tokens['access_token'], second_tokens['access_token'])
        self.assertNotEqual(first_tokens['refresh_token'], second_tokens['refresh_token'])
        oauth_tokens = self.env['oauth.token'].search([('user_id', '=', self.internal_user.id)])
        self.assertEqual(len(oauth_tokens), 2)
        for tokens in (first_tokens, second_tokens):
            uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token'])
            self.assertEqual(uid, self.internal_user.id)

    def test_single_client_can_generate_tokens_for_several_users(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        other_user = new_test_user(self.env, login='other_internal_user', groups='base.group_user')

        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        first_user_tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        self.authenticate('other_internal_user', 'other_internal_user')
        code = self._generate_auth_code(client_id=client_id)
        other_user_tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        first_user_uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=first_user_tokens['access_token'])
        self.assertEqual(first_user_uid, self.internal_user.id)
        other_user_uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=other_user_tokens['access_token'])
        self.assertEqual(other_user_uid, other_user.id)

    def test_authorization_code_of_inactive_user_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)

        self.internal_user.active = False
        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()['error'], 'invalid_grant')
        self.assertFalse(self.env['oauth.token'].search([('user_id', '=', self.internal_user.id)]))

        self.internal_user.active = True
        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 200, response.text)
        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=response.json()['access_token'])
        self.assertEqual(uid, self.internal_user.id)

    def test_refresh_token_rotation_of_inactive_user_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        self.internal_user.active = False
        rotation_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'], client_id=client_id, client_secret=client_secret,
        )
        self.assertEqual(rotation_response.status_code, 400, rotation_response.text)
        self.assertEqual(rotation_response.json()['error'], 'invalid_grant')
        self.assertIsNone(self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token']))

    def test_archiving_one_user_keeps_the_tokens_of_the_others(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        other_user = new_test_user(self.env, login='other_internal_user', groups='base.group_user')

        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        inactive_user_tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        self.authenticate('other_internal_user', 'other_internal_user')
        code = self._generate_auth_code(client_id=client_id)
        other_user_tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        self.internal_user.active = False
        self.assertIsNone(self.env['oauth.access.token']._check_credentials(
            scope='testrs', access_token=inactive_user_tokens['access_token'])
        )

        rotation_response = self._redeem_refresh_token(
            refresh_token=other_user_tokens['refresh_token'], client_id=client_id, client_secret=client_secret,
        )
        self.assertEqual(rotation_response.status_code, 200, rotation_response.text)
        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=rotation_response.json()['access_token'])
        self.assertEqual(uid, other_user.id)

    def test_access_token_of_inactive_client_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()
        client = self.env['oauth.client'].search([('client_id', '=', client_id)])

        client.action_archive()
        self.assertIsNone(self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token']))

        client.action_unarchive()
        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token'])
        self.assertEqual(uid, self.internal_user.id)

    def test_authorization_code_of_inactive_client_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        client = self.env['oauth.client'].search([('client_id', '=', client_id)])

        client.action_archive()
        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json()['error'], 'invalid_client')
        self.assertFalse(self.env['oauth.token'].search([('client_id', '=', client.id)]))

        client.action_unarchive()
        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 200, response.text)
        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=response.json()['access_token'])
        self.assertEqual(uid, self.internal_user.id)

    def test_refresh_token_rotation_of_inactive_client_is_rejected(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()
        client = self.env['oauth.client'].search([('client_id', '=', client_id)])

        client.action_archive()
        rotation_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'], client_id=client_id, client_secret=client_secret,
        )
        self.assertEqual(rotation_response.status_code, 401, rotation_response.text)
        self.assertEqual(rotation_response.json()['error'], 'invalid_client')

        client.action_unarchive()
        rotation_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'], client_id=client_id, client_secret=client_secret,
        )
        self.assertEqual(rotation_response.status_code, 200, rotation_response.text)

    def test_archiving_one_client_keeps_the_tokens_of_the_others(self):
        inactive_client_data = self._register_client()
        active_client_data = self._register_client()
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=inactive_client_data['client_id'])
        inactive_client_tokens = self._generate_access_token(
            code, client_id=inactive_client_data['client_id'], client_secret=inactive_client_data['client_secret'],
        ).json()
        code = self._generate_auth_code(client_id=active_client_data['client_id'])
        active_client_tokens = self._generate_access_token(
            code, client_id=active_client_data['client_id'], client_secret=active_client_data['client_secret'],
        ).json()

        self.env['oauth.client'].search([('client_id', '=', inactive_client_data['client_id'])]).action_archive()
        self.assertIsNone(self.env['oauth.access.token']._check_credentials(
            scope='testrs', access_token=inactive_client_tokens['access_token'])
        )

        uid = self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=active_client_tokens['access_token'])
        self.assertEqual(uid, self.internal_user.id)
        rotation_response = self._redeem_refresh_token(
            refresh_token=active_client_tokens['refresh_token'],
            client_id=active_client_data['client_id'],
            client_secret=active_client_data['client_secret'],
        )
        self.assertEqual(rotation_response.status_code, 200, rotation_response.text)

    def test_archiving_the_resource_rejects_the_access_tokens_of_its_clients(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')
        code = self._generate_auth_code(client_id=client_id)
        tokens = self._generate_access_token(code, client_id=client_id, client_secret=client_secret).json()

        # Archiving a resource archives its clients.
        self.resource.action_archive()
        self.assertIsNone(self.env['oauth.access.token']._check_credentials(scope='testrs', access_token=tokens['access_token']))
        rotation_response = self._redeem_refresh_token(
            refresh_token=tokens['refresh_token'], client_id=client_id, client_secret=client_secret,
        )
        self.assertEqual(rotation_response.status_code, 401, rotation_response.text)
        self.assertEqual(rotation_response.json()['error'], 'invalid_client')
