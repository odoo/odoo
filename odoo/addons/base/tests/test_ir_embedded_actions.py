# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestEmbeddedActionsBase(TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_partner = cls.env['res.partner'].create({
            'city': 'OrigCity',
            'email': 'test.partner@test.example.com',
            'name': 'TestingPartner',
            'employee': True,
        })
        cls.context = {
            'active_model': 'res.partner',
            'active_id': cls.test_partner.id,
        }

        # create parent action
        cls.parent_action = cls.env['ir.actions.act_window'].create({
            'name': 'ParentAction',
            'res_model': 'res.partner',
        })

        # create actions
        cls.action_1 = cls.env['ir.actions.act_window'].create({
            'name': 'Action1',
            'res_model': 'res.partner',
        })
        # create actions
        cls.action_2 = cls.env['ir.actions.act_window'].create({
            'name': 'Action2',
            'res_model': 'res.partner',
        })

        # create embedded actions
        cls.embedded_action_1 = cls.env['ir.embedded.actions'].create({
            'name': 'EmbeddedAction1',
            'parent_res_model': 'res.partner',
            'parent_action_id': cls.parent_action.id,
            'action_id': cls.action_1.id,
        })

        # create embedded actions
        cls.embedded_action_2 = cls.env['ir.embedded.actions'].create({
            'name': 'EmbeddedAction1',
            'parent_res_model': 'res.partner',
            'parent_action_id': cls.parent_action.id,
            'action_id': cls.action_2.id,
        })

    def get_embedded_actions_ids(self, parent_action):
        return parent_action.with_context(self.context).read()[0]['embedded_action_ids']

    def test_parent_has_embedded_actions(self):
        res = self.get_embedded_actions_ids(self.parent_action)
        self.assertEqual(len(res), 2, "There should be 2 embedded records linked to the parent action")
        self.assertTrue(self.embedded_action_1.id in res and self.embedded_action_2.id in res, "The correct embedded actions\
                        should be in embedded_actions")

    def test_cannot_delete_default_embedded_action(self):
        return

    def test_can_delete_custom_embedded_action(self):
        embedded_action_custo = self.env['ir.embedded.actions'].create({
            'name': 'EmbeddedActionCusto',
            'parent_res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_2.id,
            'is_deletable': True,
        })
        try:
            embedded_action_custo.unlink()
        except UserError:
            self.assertTrue(False)

    def test_domain_on_embedded_action(self):
        test_partner_custo = self.env['res.partner'].create({
            'city': 'CustoCity',
            'email': 'test.partner@test.example.com',
            'name': 'CustomPartner',
            'employee': False,
        })
        self.context = {
            'active_model': 'res.partner',
            'active_id': test_partner_custo.id,
        }
        embedded_action_custo = self.env['ir.embedded.actions'].create({
            'name': 'EmbeddedActionCusto',
            'parent_res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_2.id,
            'domain': [('employee', '=', True)]
        })
        res = self.get_embedded_actions_ids(self.parent_action)
        self.assertTrue(embedded_action_custo.id not in res, "The embedded action not respecting the domain should\
                         not be returned in the read method")

    def test_groups_on_embedded_action(self):
        # Create user groups with implied permissions
        nested_arbitrary_group = self.env['res.groups'].create({
            'name': 'arbitrary_group',
            'implied_ids': [(6, 0, [self.ref('base.group_user')])],
        })
        arbitrary_group = self.env['res.groups'].create({
            'name': 'arbitrary_group',
            'implied_ids': [(6, 0, [nested_arbitrary_group.id])],
        })
        embedded_action1, embedded_action2 = self.env['ir.embedded.actions'].create([
            {
                'name': 'EmbeddedActionCusto',
                'parent_res_model': 'res.partner',
                'parent_action_id': self.parent_action.id,
                'action_id': self.action_2.id,
                'groups_ids': [(6, 0, [nested_arbitrary_group.id])],
            },
            {
                'name': 'EmbeddedActionCusto2',
                'parent_res_model': 'res.partner',
                'parent_action_id': self.parent_action.id,
                'action_id': self.action_2.id,
                'groups_ids': [(6, 0, [arbitrary_group.id])],
            }
        ])
        res = self.get_embedded_actions_ids(self.parent_action)
        self.assertEqual(len(res), 2, "There should be 2 embedded records linked to the parent action")
        self.assertTrue(self.embedded_action_1.id in res and self.embedded_action_2.id in res, "The correct embedded actions\
                        should be in embedded_actions")
        self.env.user.write({'group_ids': [(4, arbitrary_group.id)]})
        res = self.get_embedded_actions_ids(self.parent_action)
        self.assertEqual(len(res), 4, "There should be 4 embedded records linked to the parent action")
        self.assertTrue(
            self.embedded_action_1.id in res and self.embedded_action_2.id in res and embedded_action1.id in res and embedded_action2.id in res,
            "The correct embedded actions should be in embedded_actions",
        )

    def test_create_embedded_action_with_action_and_python_method(self):
        embedded_action1, embedded_action2 = self.env['ir.embedded.actions'].create([
            {
                'name': 'EmbeddedActionCustom',
                'action_id': self.action_2.id,
                'parent_action_id': self.parent_action.id,
                'parent_res_model': 'res.partner',
                'python_method': "action_python_method",
            },
            {
                'name': 'EmbeddedActionCustom2',
                'action_id': self.action_2.id,
                'python_method': "",
                'parent_action_id': self.parent_action.id,
                'parent_res_model': 'res.partner',
            }
        ])
        self.assertEqual(embedded_action1.python_method, "action_python_method")
        self.assertFalse(embedded_action1.action_id)
        self.assertEqual(embedded_action2.action_id, self.env['ir.actions.actions'].browse(self.action_2.id))
        self.assertFalse(embedded_action2.python_method)

    def test_embedded_action_display_name_delegates_to_linked_action(self):
        """Embedded action display_name must delegate to linked action display_name."""
        server_action = self.env['ir.actions.server'].create({
            'name': 'Create Activity',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'code': 'result = {}',
            'state': 'code',
        })
        embedded_action = self.env['ir.embedded.actions'].create({
            'name': 'Stored Embedded Name',
            'parent_res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': server_action.id,
        })
        linked_action = embedded_action.action_id

        # display_name delegates to the linked action, ignoring the stored name
        self.assertEqual(embedded_action.name, 'Stored Embedded Name')
        self.assertEqual(embedded_action.display_name, linked_action.display_name)

        # display_name stays in sync when the linked action is renamed
        linked_action.name = 'Updated Action Name'
        self.assertEqual(embedded_action.display_name, linked_action.display_name)

        # display_name uses the linked action's translation in any active language
        self.env['res.lang']._activate_lang('fr_FR')
        linked_action.with_context(lang='fr_FR').name = 'Créer une activité'
        self.assertEqual(
            embedded_action.with_context(lang='fr_FR').display_name,
            linked_action.with_context(lang='fr_FR').display_name,
        )
