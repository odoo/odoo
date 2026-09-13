import base64

from odoo import Command
from odoo.tests import tagged

from .common import REDIRECT_URI, OauthServerCommon


@tagged('post_install', '-at_install')
class TestAccessTokenGeneration(OauthServerCommon):

    def test_full_authorization_code_exchange_mints_apikey(self):
        registration = self._register_client()
        client_id, client_secret = registration['client_id'], registration['client_secret']
        self.authenticate('internal_user', 'internal_user')

        code = self._generate_auth_code(client_id=client_id)
        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 200, response.text)
        response_json = response.json()
        self.assertEqual(response_json['scope'], 'testrs')
        self.assertEqual(response_json['token_type'], 'Bearer')

        uid = self.env['res.users.apikeys']._check_credentials(scope='testrs', key=response_json['access_token'])
        self.assertEqual(uid, self.internal_user.id)

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

    def test_refresh_token_rotation_generates_new_apikey_and_revokes_old(self):
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

        old_uid = self.env['res.users.apikeys']._check_credentials(scope='testrs', key=access_token_generation_response_json['access_token'])
        self.assertIsNone(old_uid)
        new_uid = self.env['res.users.apikeys']._check_credentials(scope='testrs', key=access_token_rotation_response_json['access_token'])
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

        uid = self.env['res.users.apikeys']._check_credentials(scope='testrs', key=refresh_token_first_redemption_response_json['access_token'])
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
        # the code was issued: the code must not be redeemable for an apikey anymore.
        self.resource.allowed_group_ids = self.env.ref('base.group_system')

        response = self._generate_access_token(code, client_id=client_id, client_secret=client_secret)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')
        self.assertFalse(self.env['res.users.apikeys'].search([
            ('user_id', '=', self.internal_user.id), ('scope', '=', self.resource.access_token_scope),
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
        self.assertIsNone(self.env['res.users.apikeys']._check_credentials(scope='testrs', key=tokens['access_token']))
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

    def test_autovacuumed_apikey_keeps_the_refresh_token(self):
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
            "UPDATE res_users_apikeys SET expiration_date = now() - interval '1 day' WHERE id = %s",
            [access_token.id],
        )
        self.env['res.users.apikeys']._gc_user_apikeys()
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

        uid = self.env['res.users.apikeys']._check_credentials(scope='testrs', key=tokens['access_token'])
        self.assertEqual(uid, self.internal_user.id)
