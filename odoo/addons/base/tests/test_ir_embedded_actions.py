# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


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
        arbitrary_group = self.env['res.groups'].create({
            'name': 'arbitrary_group',
            'implied_ids': [(6, 0, [self.ref('base.group_user')])],
        })
        embedded_action_custo = self.env['ir.embedded.actions'].create({
            'name': 'EmbeddedActionCusto',
            'parent_res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_2.id,
            'groups_ids': [(6, 0, [arbitrary_group.id])]
        })
        res = self.get_embedded_actions_ids(self.parent_action)
        self.assertEqual(len(res), 2, "There should be 2 embedded records linked to the parent action")
        self.assertTrue(self.embedded_action_1.id in res and self.embedded_action_2.id in res, "The correct embedded actions\
                        should be in embedded_actions")
        self.env.user.write({'groups_id': [(4, arbitrary_group.id)]})
        res = self.get_embedded_actions_ids(self.parent_action)
        self.assertEqual(len(res), 3, "There should be 3 embedded records linked to the parent action")
        self.assertTrue(self.embedded_action_1.id in res and self.embedded_action_2.id in res and embedded_action_custo.id in res, "The correct embedded actions\
                        should be in embedded_actions")

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
