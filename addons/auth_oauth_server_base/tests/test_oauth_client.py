from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestOauthClient(TransactionCase):

    def test_immutable_client_fields(self):
        resource = self.env['oauth.resource'].create({
            'name': 'testrs', 'label': 'Test Resource', 'access_token_scope': 'testrs',
        })
        client_id = self.env['oauth.client']._register_client(
            resource=resource,
            client_name='Test Client',
            redirect_uris=["https://client.example.com/callback"],
            client_type='confidential',
        )['client_id']

        client = self.env['oauth.client'].search([('client_id', '=', client_id)], limit=1)

        with self.assertRaises(UserError):
            client.client_id = 'new client id'

        with self.assertRaises(UserError):
            client.client_type = 'public'

        with self.assertRaises(UserError):
            client.resource_id = resource
