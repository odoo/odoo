from odoo.tests.common import TransactionCase, tagged

from odoo.addons.web.controllers.utils import get_action, get_action_triples


@tagged("web_unit", "web_router")
class TestWebRouter(TransactionCase):
    def test_router_get_action_exist(self):
        ir_cron_act = self.env.ref("base.ir_cron_act")
        valid_actions = [
            f"action-{ir_cron_act.id}",
            "action-base.ir_cron_act",
            "m-ir.cron",
            "ir.cron",
            "crons",
        ]
        for action in valid_actions:
            with self.subTest(action=action):
                self.assertEqual(get_action(self.env, action), ir_cron_act)

    def test_router_get_action_missing(self):
        Actions = self.env["ir.actions.actions"]
        missing_actions = [
            "action-999999999",
            "action-base.idontexist",
            "m-base",
            "m-idontexist",
            "base.idontexist",
            "idontexist",
        ]
        for action in missing_actions:
            with self.subTest(action=action):
                self.assertEqual(get_action(self.env, action), Actions)

    def test_router_get_action_triples_exist(self):
        base = self.env["ir.module.module"].search([("name", "=", "base")])
        user = self.env.user
        ir_cron_act = self.env.ref("base.ir_cron_act")

        matrix = {
            f"action-{ir_cron_act.id}": [(None, ir_cron_act, None)],
            "action-base.ir_cron_act": [(None, ir_cron_act, None)],
            "m-ir.cron": [(None, ir_cron_act, None)],
            "ir.cron": [(None, ir_cron_act, None)],
            "crons": [(None, ir_cron_act, None)],
            f"apps/{base.id}/ir.module.module/{base.id}": [
                (None, self.env.ref("base.open_module_tree"), base.id),
                (base.id, self.env.ref("base.open_module_tree"), base.id),
            ],
            f"users/{user.id}/res.partner/{user.partner_id.id}": [
                (None, self.env.ref("base.action_res_users"), user.id),
                (user.id, get_action(self.env, "res.partner"), user.partner_id.id),
            ],
            f"users/{user.id}/ir.access/ir.access/146": [
                (None, self.env.ref("base.action_res_users"), user.id),
                (user.id, self.env.ref("base.action_ir_access"), None),
                (user.id, self.env.ref("base.action_ir_access"), 146),
            ],
        }
        for path, triples in matrix.items():
            with self.subTest(path=path):
                self.assertEqual(list(get_action_triples(self.env, path)), triples)

    def test_router_get_action_triples_missing(self):
        missing_actions = [
            "action-999999999",
            "action-base.idontexist",
            "m-base",
            "m-idontexist",
            "base.idontexist",
            "idontexist",
        ]
        for action in missing_actions:
            with self.subTest(path=action):
                with self.assertRaises(ValueError) as capture:
                    all(get_action_triples(self.env, action))
                self.assertEqual(
                    capture.exception.args[0],
                    f"expected action at word 0 but found “{action}”",
                )
