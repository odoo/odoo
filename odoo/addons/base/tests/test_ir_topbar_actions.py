
from odoo.tests import tagged
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo

@tagged('nice')
class TestTopBarActionsBase(TransactionCaseWithUserDemo):
    def setUp(self):
        super(TestTopBarActionsBase, self).setUp()

        # Data on which we will run the server action
        self.test_partner = self.env['res.partner'].create({
            'city': 'OrigCity',
            'email': 'test.partner@test.example.com',
            'name': 'TestingPartner',
            'employee': True,
        })
        self.context = {
            'active_model': 'res.partner',
            'active_id': self.test_partner.id,
        }

        # create parent action
        self.parent_action = self.env['ir.actions.act_window'].create({
            'name': 'ParentAction',
            'res_model': 'res.partner',
        })

        # create actions
        self.action_1 = self.env['ir.actions.act_window'].create({
            'name': 'Action1',
            'res_model': 'res.partner',
        })
        # create actions
        self.action_2 = self.env['ir.actions.act_window'].create({
            'name': 'Action2',
            'res_model': 'res.partner',
        })

        # create topbar actions
        self.topbar_action_1 = self.env['ir.actions.topbar'].create({
            'name': 'TopBarAction1',
            'res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_1.id,
        })

        # create topbar actions
        self.topbar_action_2 = self.env['ir.actions.topbar'].create({
            'name': 'TopBarAction1',
            'res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_2.id,
        })

    def get_children_ids(self, parent_action):
        return [el.get('id') for el in parent_action.with_context(self.context).read()[0]['children_ids']]

    def test_parent_has_topbar_actions(self):
        res = self.get_children_ids(self.parent_action)
        self.assertEqual(len(res), 2, "There should be 2 topbar records linked to the parent action")
        self.assertTrue(self.topbar_action_1.id in res and self.topbar_action_2.id in res, "The correct topbar actions\
                        should be in children_ids")

    def test_cannot_delete_default_topbar_action(self):
        print()

    def test_can_delete_custom_topbar_action(self):
        print()

    def test_domain_on_topbar_action(self):
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
        topbar_action_custo = self.env['ir.actions.topbar'].create({
            'name': 'TopBarActionCusto',
            'res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_2.id,
            'domain': [('employee', '=', True)]
        })
        res = self.get_children_ids(self.parent_action)
        self.assertTrue(topbar_action_custo.id not in res, "The topbar action not respecting the domain should\
                         not be returned in the read method")

    def test_groups_on_topbar_action(self):
        print()

    def test_create_topbar_python_action(self):
        print()
