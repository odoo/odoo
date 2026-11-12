from odoo.fields import Command
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

        cls.env['ir.hub'].search([('res_model', '=', 'res.partner')]).unlink()
        cls.hub = cls.env['ir.hub'].create({
            'name': 'Partner hub',
            'res_model': 'res.partner',
            'item_ids': [
                Command.create({'name': 'Visible method', 'python_method': 'action_visible', 'res_model': 'res.partner'}),
                Command.create({'name': 'Visible action', 'action_id': window_action('res.partner').id}),
                # the user can't read ir.config_parameter
                Command.create({'name': 'Unreadable method', 'python_method': 'action_unreadable', 'res_model': 'ir.config_parameter'}),
                Command.create({'name': 'Unreadable action', 'action_id': window_action('ir.config_parameter').id}),
                # the user is not an administrator
                Command.create({'name': 'Item group', 'python_method': 'action_item_group', 'res_model': 'res.partner', 'group_ids': [Command.link(group_system.id)]}),
                Command.create({'name': 'Action group', 'action_id': window_action('res.partner', group_system.ids).id}),
            ],
        })

    def _hub_item_names(self, method):
        action = {}
        add_hub_info(action, self.env(user=self.user), self.partner.id, model='res.partner', method=method)
        return [item['display_name'] for item in action['hub']['item_ids']] if 'hub' in action else None

    def test_unreadable_model(self):
        hubs = self.env['ir.hub'].with_user(self.user)._get_session_hubs()
        self.assertEqual(
            [item['display_name'] for item in hubs['res.partner']['item_ids']],
            ['Visible method', 'Visible action'],
        )
        self.assertEqual(self._hub_item_names('action_visible'), ['Visible method', 'Visible action'])
        self.assertIsNone(self._hub_item_names('action_unreadable'), "a hidden item doesn't open its hub")

    def test_groups(self):
        self.assertIsNone(self._hub_item_names('action_item_group'), "a hidden item doesn't open its hub")
        admin_hubs = self.env['ir.hub']._get_session_hubs()
        self.assertEqual(len(admin_hubs['res.partner']['item_ids']), 6)
