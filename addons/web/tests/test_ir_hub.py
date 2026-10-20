from odoo.fields import Command
from odoo.models import get_public_method
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.web.controllers.utils import add_hub_info


@tagged('post_install', '-at_install')
class TestIrHub(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'hub_user', groups='base.group_user')
        cls.partner = cls.env['res.partner'].create({'name': 'Hub partner'})
        group_system = cls.env.ref('base.group_system')

        def window_action(res_model, groups=()):
            return cls.env['ir.actions.act_window'].create({
                'name': res_model, 'res_model': res_model, 'group_ids': [Command.set(groups)],
            })

        cls.visible_action = window_action('res.partner')
        cls.env['ir.hub'].search([('res_model', '=', 'res.partner')]).unlink()
        cls.hub = cls.env['ir.hub'].create({
            'name': 'Partner hub',
            'res_model': 'res.partner',
            'item_ids': [
                Command.create({'name': 'Visible method', 'python_method': 'action_visible', 'res_model': 'res.partner'}),
                Command.create({'name': 'Visible action', 'action_id': cls.visible_action.id}),
                # the user can't read ir.config_parameter
                Command.create({'name': 'Unreadable method', 'python_method': 'action_unreadable', 'res_model': 'ir.config_parameter'}),
                Command.create({'name': 'Unreadable action', 'action_id': window_action('ir.config_parameter').id}),
                # the user is not an administrator
                Command.create({'name': 'Item group', 'python_method': 'action_item_group', 'res_model': 'res.partner', 'group_ids': [Command.link(group_system.id)]}),
                Command.create({'name': 'Action group', 'action_id': window_action('res.partner', group_system.ids).id}),
            ],
        })

    def _opened_item_name(self, method=None, action_id=None):
        action = {}
        add_hub_info(action, self.env(user=self.user), self.partner.id, action_id=action_id, model='res.partner', method=method)
        return self.env['ir.hub.item'].browse(action['hub']['active_item_id']).name if 'hub' in action else None

    # items on a model the user can't read are hidden and don't open their hub
    def test_unreadable_model(self):
        self.env.invalidate_all()
        hubs = self.env['ir.hub'].with_user(self.user)._get_session_hubs()
        self.assertEqual(
            [item['display_name'] for item in hubs['res.partner']['item_ids']],
            ['Visible method', 'Visible action'],
        )
        self.assertEqual(self._opened_item_name('action_visible'), 'Visible method')
        self.assertIsNone(self._opened_item_name('action_unreadable'), "a hidden item doesn't open its hub")

    # items restricted to groups the user isn't in are hidden
    def test_groups(self):
        self.assertIsNone(self._opened_item_name('action_item_group'), "a hidden item doesn't open its hub")
        admin_hubs = self.env['ir.hub']._get_session_hubs()
        self.assertEqual(len(admin_hubs['res.partner']['item_ids']), 6)

    # the invisible expression of an item is evaluated on the hub's record
    def test_invisible(self):
        item = self.env['ir.hub.item'].create({
            'hub_id': self.hub.id, 'name': 'Companies only', 'python_method': 'action_companies',
            'res_model': 'res.partner', 'invisible': 'not is_company',
        })
        hub = self.hub.with_user(self.user)
        self.env.invalidate_all()
        self.assertEqual(hub._get_invisible_item_ids(self.partner.id), item.ids)
        self.partner.is_company = True
        self.assertEqual(hub._get_invisible_item_ids(self.partner.id), [])

    # an action opened by its id opens the item of that action
    def test_open_action_item(self):
        self.assertEqual(self._opened_item_name(action_id=self.visible_action.id), 'Visible action')

    # the item of the called method wins over the item of the returned action
    def test_python_method_over_action(self):
        self.assertEqual(
            self._opened_item_name(method='action_visible', action_id=self.visible_action.id),
            'Visible method',
        )

    # the user's setting of a record is created, updated, and formatted
    def test_set_hub_setting(self):
        settings = self.env['res.users.settings']._find_or_create_for_user(self.user).with_user(self.user)
        settings.set_hub_setting(self.hub.id, self.partner.id, {'pinned_item_ids': [1, 2], 'unknown': True})
        settings.set_hub_setting(self.hub.id, self.partner.id, {'show_tabs': True})
        self.assertEqual(len(settings.hub_config_ids), 1, "the setting of the record is updated")
        self.assertEqual(
            settings._res_users_settings_format(['hub_config_ids'])['hub_config_ids'],
            {f'{self.hub.id},{self.partner.id}': {'pinned_item_ids': [1, 2], 'show_tabs': True}},
        )

    # the hub is added to the action, with the correct display_name
    def test_hub_info(self):
        action = {}
        add_hub_info(action, self.env(user=self.user), self.partner.id, model='res.partner', method='action_visible')
        item = self.hub.item_ids.filtered(lambda item: item.name == 'Visible method')
        self.assertEqual(action['hub'], {
            'id': self.hub.id,
            'res_model': 'res.partner',
            'res_id': self.partner.id,
            'active_item_id': item.id,
            'invisible_item_ids': [],
        })
        self.assertEqual(action['display_name'], 'Hub partner - Visible method')

    # no hub without a record, without a matching item, or for a portal user
    def test_no_hub(self):
        portal_user = new_test_user(self.env, 'hub_portal_user', groups='base.group_portal')
        for env, res_id, method in [
            (self.env(user=self.user), False, 'action_visible'),
            (self.env(user=self.user), self.partner.id, 'action_unknown'),
            (self.env(user=portal_user), self.partner.id, 'action_visible'),
        ]:
            with self.subTest(user=env.user.login, res_id=res_id, method=method):
                action = {}
                add_hub_info(action, env, res_id, model='res.partner', method=method)
                self.assertNotIn('hub', action)

    # the method of an item only matches when called on the hub's model
    def test_model_restricts_items(self):
        action = {}
        add_hub_info(action, self.env(user=self.user), self.partner.id, model='res.users', method='action_visible')
        self.assertNotIn('hub', action, "the item of a hub on another model doesn't match the method")


@tagged('post_install', '-at_install')
class TestIrHubData(TransactionCase):

    # the items of the hubs of the installed modules reference existing actions/methods
    def test_hub_items(self):
        for item in self.env['ir.hub.item'].search([]):
            hub_model = item.hub_id.res_model
            with self.subTest(item=item.display_name, hub=hub_model):
                self.assertIn(hub_model, self.env)
                if item.python_method:
                    # raises if the method doesn't exist or can't be called by the web client
                    get_public_method(self.env[hub_model], item.python_method)
                    self.assertIn(item.res_model, self.env)
                else:
                    action = self.env[item.action_id.type].browse(item.action_id.id)
                    if action._fields.get('res_model') and action.res_model:
                        self.assertIn(action.res_model, self.env)
