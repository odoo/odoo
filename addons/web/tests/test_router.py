from odoo.tests.common import TransactionCase
from odoo.addons.web.controllers.utils import get_action_triples, get_action


class TestWebRouter(TransactionCase):
    def test_router_get_action_exist(self):
        ir_cron_act = self.env.ref('base.ir_cron_act')
        valid_actions = [
            f'action-{ir_cron_act.id}',  # record id
            'action-base.ir_cron_act',   # xml id
            'm-ir.cron',                 # m- model name (for website)
            'ir.cron',                   # dotted model name
            'crons',                     # action path
        ]
        for action in valid_actions:
            with self.subTest(action=action):
                self.assertEqual(get_action(self.env, action), ir_cron_act)

    def test_router_get_action_missing(self):
        Actions = self.env['ir.actions.actions']
        missing_actions = [
            'action-999999999',
            'action-base.idontexist',
            'm-base',  # abstract model
            'm-idontexist',
            'base.idontexist',
            'idontexist',
        ]
        for action in missing_actions:
            with self.subTest(action=action):
                self.assertEqual(get_action(self.env, action), Actions)

    def test_router_get_action_triples_exist(self):
        base = self.env['ir.module.module'].search([('name', '=', 'base')])
        user = self.env.user
        ir_cron_act = self.env.ref('base.ir_cron_act')

        matrix = {
            # single action
            f'action-{ir_cron_act.id}': [(None, ir_cron_act, None)],
            'action-base.ir_cron_act': [(None, ir_cron_act, None)],
            'm-ir.cron': [(None, ir_cron_act, None)],
            'ir.cron': [(None, ir_cron_act, None)],
            'crons': [(None, ir_cron_act, None)],

            # multiple actions, all are accessible by clicking in the web client

            # Apps > Base > Module info
            f'apps/{base.id}/ir.module.module/{base.id}': [
                (None, self.env.ref('base.open_module_tree'), base.id),
                (base.id, self.env.ref('base.open_module_tree'), base.id)],

            # Settings > Users & Companies > Users > Marc Demo > Related Partner
            f'users/{user.id}/res.partner/{user.partner_id.id}': [
                (None, self.env.ref('base.action_res_users'), user.id),
                (user.id, self.env.ref('base.action_partner_form'), user.partner_id.id)],

            # Settings > Users & Companies > Users > Marc Demo > Access Right > TOTP
            f'users/{user.id}/ir.model.access/ir.model.access/146': [
                (None, self.env.ref('base.action_res_users'), user.id),
                (user.id, self.env.ref('base.ir_access_act'), None),
                (user.id, self.env.ref('base.ir_access_act'), 146),
            ]
        }
        for path, triples in matrix.items():
            with self.subTest(path=path):
                self.assertEqual(list(get_action_triples(self.env, path)), triples)

    def test_router_get_action_triples_missing(self):
        # single unknown action
        missing_actions = [
            'action-999999999',
            'action-base.idontexist',
            'm-base',
            'm-idontexist',
            'base.idontexist',
            'idontexist',
        ]
        for action in missing_actions:
            with self.subTest(path=action):
                with self.assertRaises(ValueError) as capture:
                    all(get_action_triples(self.env, action))
                self.assertEqual(capture.exception.args[0],
                    f"expected action at word 0 but found “{action}”")
