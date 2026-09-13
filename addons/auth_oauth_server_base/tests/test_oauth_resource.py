from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOauthResource(TransactionCase):

    def _register_client(self, resource):
        credentials = self.env['oauth.client']._register_client(
            resource,
            'Test Client',
            ['https://client.example.com/callback'],
            'public'
        )
        return self.env['oauth.client'].search([('client_id', '=', credentials['client_id'])], limit=1)

    def test_archiving_resource_archives_its_clients(self):
        resource = self.env['oauth.resource'].create({
            'name': 'testrs', 'label': 'Test Resource', 'access_token_scope': 'testrs',
        })
        other_resource = self.env['oauth.resource'].create({
            'name': 'otherrs', 'label': 'Other Resource', 'access_token_scope': 'otherrs',
        })
        resource_client = self._register_client(resource)
        other_resource_client = self._register_client(other_resource)
        resource.action_archive()
        self.assertFalse(resource_client.active)
        self.assertTrue(other_resource_client.active)

    def test_unarchiving_resource_keeps_related_clients_archived(self):
        resource = self.env['oauth.resource'].create({
            'name': 'testrs', 'label': 'Test Resource', 'access_token_scope': 'testrs',
        })
        client = self._register_client(resource)
        resource.action_archive()
        self.assertFalse(client.active)
        resource.action_unarchive()
        self.assertFalse(client.active)
