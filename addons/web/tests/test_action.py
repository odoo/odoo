import json
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLoadBreadcrumbs(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env['ir.model']._get_id('res.partner')

        # Create a user in order to have a fixed name in local and on the runbot
        cls.env = cls.env(user=cls.env.ref('base.user_admin'))
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

        cls.window_action = cls.env['ir.actions.act_window'].create({
            'name': 'Test Partners',
            'res_model': 'res.partner',
        })

        cls.server_action_without_path = cls.env['ir.actions.server'].create({
            'name': 'Test Server Action Without Path',
            'model_id': model_id,
            'state': 'code',
            'code': """action = {
                'type': 'ir.actions.act_window',
                'name': 'Window Action From Server',
                'res_model': 'res.partner',
            }""",

        })

        cls.server_action = cls.env['ir.actions.server'].create({
            'name': 'Breadcrumb Server Action',
            'model_id': model_id,
            'state': 'code',
            'path': 'test_path',
            'code': """action = {
                'type': 'ir.actions.act_window',
                'name': 'Window Action From Server',
                'res_model': 'res.partner',
                'views': [(False, 'list')],
            }""",
        })

        cls.client_action = cls.env['ir.actions.client'].create({
            'name': 'Breadcrumb Client Action',
            'res_model': 'res.partner',
            'tag': 'account_report',
        })

        cls.server_action_with_form_view = cls.env['ir.actions.server'].create({
            'name': 'Breadcrumb Server Action With Path',
            'model_id': model_id,
            'state': 'code',
            'path': 'test_path_form_view',
            'code': """action = {
                'type': 'ir.actions.act_window',
                'name': 'Window Action From Server',
                'res_model': 'res.partner',
                'views': [(False, 'form')],
            }""",
        })

    def test_breadcrumbs_empty_action(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [],
                },
            }),
        )
        self.assertEqual(resp.json()['result'], [])

    def test_breadcrumbs_window_action(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.window_action.id,
                            'resId': None,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['display_name'], 'Test Partners')

    def test_breadcrumbs_server_action_path(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.server_action_without_path.id,
                            'resId': None,
                        },
                        {
                            'action': self.server_action.id,
                            'resId': None,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['error'], 'A server action must have a path to be restored')
        self.assertEqual(resp.json()['result'][1]['display_name'], 'Window Action From Server')

    def test_breadcrumbs_client_action(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.client_action.id,
                            'resId': None,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['display_name'], 'Breadcrumb Client Action')

    def test_breadcrumbs_client_action_multirecord(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.client_action.id,
                            'resId': None,
                        },
                        {
                            'action': self.client_action.id,
                            'resId': 1,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['error'], 'Client actions don\'t have multi-record views')

    def test_breadcrumbs_action_with_res_model(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.client_action.id,
                            'resId': 'new',
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['display_name'], 'New')

        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.client_action.id,
                            'resId': self.partner.id,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['display_name'], 'Test Partner')

    def test_breadcrumbs_server_action_without_res_model(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'action': self.server_action.id,
                            'resId': None,
                        },
                        {
                            'action': self.server_action_with_form_view.id,
                            'resId': None,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['display_name'], 'Window Action From Server')
        self.assertEqual(resp.json()['result'][1]['display_name'], None)

    def test_breadcrumbs_get_model(self):
        self.authenticate("admin", "admin")

        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'resId': None,
                            'model': 'res.users',
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['error']['message'], 'Odoo Server Error')

        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'resId': self.partner.id,
                            'model': 'res.partner',
                        },
                        {
                            'resId': 'new',
                            'model': 'res.partner',
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['result'][0]['display_name'], self.partner.display_name)
        self.assertEqual(resp.json()['result'][1]['display_name'], 'New')

    def test_breadcrumbs_no_action_nor_model(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            '/web/action/load_breadcrumbs',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'params': {
                    'actions': [
                        {
                            'resId': None,
                        },
                    ],
                },
            }),
        )
        self.assertEqual(resp.json()['error']['message'], 'Odoo Server Error')


@tagged('post_install', '-at_install')
class TestActionHub(HttpCase):
    """ The routes opening actions add the hub of the opened item (see
    ``test_ir_hub`` for the content of the hub).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'hub_http_user', groups='base.group_user')
        cls.partners = cls.env['res.partner'].create([{'name': 'Hub partner 1'}, {'name': 'Hub partner 2'}])
        cls.window_action = cls.env['ir.actions.act_window'].create({'name': 'Partners', 'res_model': 'res.partner'})
        cls.env['ir.hub'].search([('res_model', '=', 'res.partner')]).unlink()
        cls.hub = cls.env['ir.hub'].create({
            'name': 'Partner hub',
            'res_model': 'res.partner',
            'item_ids': [
                Command.create({'name': 'Method', 'python_method': 'action_hub_test', 'res_model': 'res.partner'}),
                Command.create({'name': 'Action', 'action_id': cls.window_action.id}),
            ],
        })
        cls.method_item, cls.action_item = cls.hub.item_ids

        def action_hub_test(self):
            return {'type': 'ir.actions.act_window', 'res_model': 'res.partner', 'views': [[False, 'list']]}

        cls.startClassPatcher(patch.object(
            cls.registry['res.partner'], 'action_hub_test', action_hub_test, create=True,
        ))

    def setUp(self):
        super().setUp()
        self.authenticate('hub_http_user', 'hub_http_user')

    def _call_button(self, partners):
        return self.make_jsonrpc_request('/web/dataset/call_button', {
            'model': 'res.partner', 'method': 'action_hub_test', 'args': [partners.ids], 'kwargs': {},
        })

    # a button calling an item's method on one record opens that item's hub
    def test_call_button_hub(self):
        with self.assertNoLogs('odoo.addons.web.controllers.utils', 'WARNING'):
            action = self._call_button(self.partners[0])
        self.assertEqual(action['hub']['active_item_id'], self.method_item.id)

    # a button called on several records opens no hub
    def test_call_button_multi_ids(self):
        self.assertNotIn('hub', self._call_button(self.partners))

    # loading an item's action opens its hub only when given an active record
    # of the hub's model
    def test_action_load_hub(self):
        def load(context=None):
            return self.make_jsonrpc_request('/web/action/load', {
                'action_id': self.window_action.id, 'context': context or {},
            })

        partner_id = self.partners[0].id
        action = load({'active_id': partner_id, 'active_model': 'res.partner'})
        self.assertEqual(action['hub']['active_item_id'], self.action_item.id)
        # restored from the url, without active_model
        self.assertEqual(load({'active_id': partner_id})['hub']['active_item_id'], self.action_item.id)
        self.assertNotIn('hub', load())
        self.assertNotIn('hub', load({'active_id': partner_id, 'active_model': 'res.users'}))
        missing_id = self.env['res.partner'].search([], order='id desc', limit=1).id + 1
        self.assertNotIn('hub', load({'active_id': missing_id}))
