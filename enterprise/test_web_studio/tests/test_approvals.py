from odoo import Command
from odoo.exceptions import UserError

from odoo.tests.common import TransactionCase, HttpCase, tagged
from odoo.addons.web_studio.tests.test_ui import setup_view_editor_data

@tagged("-at_install", "post_install")
class TestStudioApprovals(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = cls.env.ref("base.user_admin")
        cls.demo_user = cls.env["res.users"].search([("login", "=", "demo")], limit=1)
        if not cls.demo_user:
            cls.demo_user = cls.env["res.users"].create({
                "login": "demo",
                "name": "demo",
                "email": "demo@demo",
                "groups_id": [Command.link(cls.env.ref("base.group_user").id)]
            })

        cls.other_user = cls.env["res.users"].create({
            "name": "test",
            "login": "test",
            "email": "test@test.test",
            "groups_id": [Command.link(cls.env.ref("base.group_user").id)]
        })

        cls.test_user_2 = cls.env["res.users"].create({
            "name": "test_2",
            "login": "test_2",
            "email": "test_2@test_2.test_2",
            "groups_id": [Command.link(cls.env.ref("base.group_user").id)]
        })
        cls.attrs_before['test.studio.model_action'].update((
            'action_confirm',
            'action_step',
        ))
        cls.attrs_before['test.studio.model_action2'].update((
            'action_confirm',
            'action_step',
        ))

    def test_approval_method_two_models(self):
        IrModel = self.env["ir.model"]

        self.env["studio.approval.rule"].create([
            {
                "name": "Rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "name": "Rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "name": "Rule 3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            },
            {
                "name": "Rule 4",
                "model_id": IrModel._get("test.studio.model_action2").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            }
        ])

        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })

        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name}, Approved")
        self.assertTrue('title="Rule 1"' in model_action.message_ids[0].body)
        self.assertEqual(model_action.message_ids[0].author_id, self.demo_user.partner_id)
        self.assertEqual(len(model_action.activity_ids), 1)

        with self.with_user("admin"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name}, Approved")
        self.assertTrue('title="Rule 2"' in model_action.message_ids[0].body)
        self.assertEqual(len(model_action.activity_ids), 1)

        with self.with_user("test"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertTrue(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.other_user.name}, Approved")
        self.assertTrue('title="Rule 3"' in model_action.message_ids[0].body)
        self.assertEqual(len(model_action.activity_ids), 0)

    def test_notify_higher_notification_order(self):
        IrModel = self.env["ir.model"]

        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "domain": "[('step', '<', 1)]",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            },
            {
                "name": "rule 2 - bis",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "domain": "[('step', '>=', 1)]",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(self.other_user.id)],
            },
            {
                "name": "rule 3",
                "model_id": IrModel._get("test.studio.model_action2").id,
                "method": "action_step",
                "notification_order": "1",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
        ])

        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        # Rule 3 is not found: it applies on another model
        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name}, Approved")
        self.assertTrue('title="rule 1"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 1)

        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[(model_action.id, "action_step", False)]
        self.assertEqual(len(spec["entries"]), 1)
        self.assertEqual(spec["entries"][0]["rule_id"][0], rules[0].id)

        with self.with_user("admin"):
            self.env["studio.approval.rule"].browse(rules[1].id).set_approval(model_action.id, True)

        # rule 2 is validated, rule 2 - bis doesn't apply, but is at the same level as rule 2 anyway, so it would not notify.
        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.other_user.name}, Approved")
        self.assertTrue('title="rule 2"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 0)

        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[(model_action.id, "action_step", False)]

        self.assertEqual(len(spec["entries"]), 2)
        self.assertEqual(spec["entries"][1]["rule_id"][0], rules[1].id)

    def test_entries_approved_by_other_read_by_regular_user(self):
        IrModel = self.env["ir.model"]
        self.env["studio.approval.rule"].create([
            {   # rule 0
                "name": "R0",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "1",
                "exclusive_user": True,
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
            },
            {
                "name": "R1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "exclusive_user": True,
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
            },
            {
                "name": "R2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "exclusive_user": True,
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
            },
            {
                "name": "R3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "3",
                "exclusive_user": True,
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.test_user_2.id)],
            },
        ])
        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        with self.with_user("admin"):
            # validates rule 0
            # this will create an entry belonging to admin
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Approved")
        self.assertTrue('title="R0"' in model_action.message_ids[0].body)
        self.assertEqual(len(model_action.activity_ids), 2)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.admin_user.ids)

        with self.with_user("test"):
            # validates rule 1
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Approved")
        self.assertEqual(model_action.message_ids[0].author_id, self.other_user.partner_id)
        self.assertTrue('title="R1"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.admin_user.ids)

        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Approved")
        self.assertTrue('title="R2"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.test_user_2.ids)

        with self.with_user("test_2"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 1)
        self.assertEqual(model_action.message_ids[0].preview, "Approved")
        self.assertTrue('title="R3"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 0)

    def test_no_responsible(self):
        IrModel = self.env["ir.model"]
        self.env["studio.approval.rule"].create([
            {
                "name": "R0",
                "model_id": IrModel._get("test.studio.model_action").id,
                "approval_group_id": self.env.ref("base.group_system").id,
                "method": "action_step",
                "notification_order": "1",
                "users_to_notify": [Command.link(self.demo_user.id), Command.link(self.other_user.id)]
            }
        ])
        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        with self.with_user("test_2"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()
        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Test Model Studio created")
        self.assertEqual(len(model_action.activity_ids), 0)

    def test_rule_notify_domain(self):
        IrModel = self.env["ir.model"]

        model_action = self.env["test.studio.model_action"].create({
            "name": "test 2"
        })
        rules = self.env["studio.approval.rule"].create([
            {
                "name": "ruledomain",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "domain": "[('name', '=', 'test')]",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "name": "rule3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            }
        ])
        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()
        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name}, Approved")
        self.assertTrue('title="rule 2"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 1)

        spec = self.env["studio.approval.rule"].get_approval_spec([
            dict(model="test.studio.model_action", method="action_confirm", action_id=False, res_id=model_action.id)
        ])
        spec = dict(spec["test.studio.model_action"])[(model_action.id, "action_confirm", False)]
        self.assertEqual(len(spec["entries"]), 1)
        self.assertEqual(spec["entries"][0]["rule_id"][0], rules[1].id)

    def test_rule_notify_higher_order_domain(self):
        IrModel = self.env["ir.model"]

        model_action = self.env["test.studio.model_action"].create({
            "name": "test 2"
        })
        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 1 - bis",
                "domain": "[('name', '=', 'test')]",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "domain": "[('name', '=', 'test')]",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.other_user.id)],
                "users_to_notify": [Command.link(self.other_user.id)],
            }
        ])
        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[0].id).set_approval(model_action.id, True)
        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name}, Approved")
        self.assertTrue('title="rule 1"' in model_action.message_ids[0].body)

        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.user_id.id, self.other_user.id)

        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_confirm", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[(model_action.id, "action_confirm", False)]

        self.assertEqual(len(spec["entries"]), 1)
        self.assertEqual(spec["entries"][0]["rule_id"][0], rules[0].id)

    def test_notify_higher_1(self):
        IrModel = self.env["ir.model"]

        model_action = self.env["test.studio.model_action"].create({
            "name": "test 2"
        })
        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 1 - bis",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
        ])
        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[0].id).set_approval(model_action.id, True)
        self.assertEqual(len(model_action.activity_ids), 0)

        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[1].id).set_approval(model_action.id, True)

        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(self.env["studio.approval.request"].search([("rule_id", "=", rules[2].id)]).mail_activity_id, model_action.activity_ids)

    def test_notify_higher_2(self):
        IrModel = self.env["ir.model"]

        model_action = self.env["test.studio.model_action"].create({
            "name": "test 2"
        })
        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 1 - bis",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
        ])
        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[0].id).set_approval(model_action.id, False)
        self.assertEqual(len(model_action.activity_ids), 0)

        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[1].id).set_approval(model_action.id, True)

        self.assertEqual(len(model_action.activity_ids), 0)
        self.assertEqual(self.env["studio.approval.request"].search([("rule_id", "=", rules[2].id)]).mail_activity_id, model_action.activity_ids)

    def test_notify_higher_3(self):
        IrModel = self.env["ir.model"]

        model_action = self.env["test.studio.model_action"].create({
            "name": "test 2"
        })
        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 1 - bis",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "approval_group_id": self.env.ref("base.group_user").id,
                "approver_ids": [Command.link(self.admin_user.id)],
                "users_to_notify": [Command.link(2)],
            },
        ])
        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[0].id).set_approval(model_action.id, True)
        self.assertEqual(len(model_action.activity_ids), 0)

        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[1].id).set_approval(model_action.id, False)

        self.assertEqual(len(model_action.activity_ids), 0)
        self.assertEqual(self.env["studio.approval.request"].search([("rule_id", "=", rules[2].id)]).mail_activity_id, model_action.activity_ids)

    def test_can_revoke_approval_with_inferior_order(self):
        IrModel = self.env["ir.model"]

        rules = self.env["studio.approval.rule"].create([
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "approver_ids": [Command.link(self.other_user.id)],
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "approver_ids": [Command.link(self.demo_user.id)],
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "approver_ids": [Command.link(self.test_user_2.id)],
            },
        ])

        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        rules[0].with_user(self.other_user).set_approval(model_action.id, True)
        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[model_action.id, "action_step", False]
        self.assertEqual(len(spec["entries"]), 1)
        with self.assertRaises(UserError):
            rules[0].with_user(self.demo_user).delete_approval(model_action.id)

        rules[0].with_user(self.test_user_2).delete_approval(model_action.id)
        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[model_action.id, "action_step", False]
        self.assertEqual(len(spec["entries"]), 0)

    def test_create_base_automation(self):
        self.addCleanup(self.env['base.automation']._unregister_hook)
        IrModel = self.env["ir.model"]

        def _mocked__base_automation_data_for_model(self, model_id):
            if model_id.model == "test.studio.model_action":
                confirmed_field = self.env["ir.model.fields"]._get("test.studio.model_action", "confirmed")
                return {
                    'trigger': 'on_create_or_write',
                    'trigger_field_ids': [Command.link(confirmed_field.id)],
                    'filter_pre_domain': "[('confirmed', '=', True)]",
                    'filter_domain': "[('confirmed', '=', False)]",
                }

        self.patch(self.env.registry.get("studio.approval.rule"), "_base_automation_data_for_model", _mocked__base_automation_data_for_model)

        model_action = self.env["test.studio.model_action"].create({
            "name": "test 2"
        })
        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "approver_ids": [Command.link(self.admin_user.id)],
            },
            {
                "name": "rule 1 - bis",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "approver_ids": [Command.link(self.admin_user.id)],
            }
        ])
        self.assertTrue(self.env.ref("web_studio.remove_approval_entries__test_studio_model_action__automation").exists())
        self.assertTrue(self.env.ref("web_studio.remove_approval_entries__test_studio_model_action__action_server").exists())
        # recreate a rule to make sure we don't re-create those two objects
        self.env["studio.approval.rule"].create({
            "name": "rule recreate",
            "model_id": IrModel._get("test.studio.model_action").id,
            "method": "action_step",
            "approver_ids": [Command.link(self.admin_user.id)],
        })

        rules[0].with_user(self.admin_user).set_approval(model_action.id, True)
        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[model_action.id, "action_step", False]
        self.assertEqual(len(spec["entries"]), 1)

        model_action.action_confirm()
        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[model_action.id, "action_step", False]
        self.assertEqual(len(spec["entries"]), 1)

        model_action.confirmed = False
        spec = self.env["studio.approval.rule"].get_approval_spec([dict(model="test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)])
        spec = dict(spec["test.studio.model_action"])[model_action.id, "action_step", False]
        self.assertEqual(len(spec["entries"]), 0)

@tagged("-at_install", "post_install")
class TestStudioApprovalsUIUnit(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        setup_view_editor_data(cls)
        cls.testAction.res_model = "test.studio.model_action"
        cls.testView.model = "test.studio.model_action"
        cls.testView.arch = """
            <form>
                <button name="action_confirm" type="object" class="mybutton"/>
            </form>
        """
        cls.admin_user = cls.env.ref("base.user_admin")

    def test_disable_approvals(self):
        rule = self.env["studio.approval.rule"].create({
            "model_id": self.env["ir.model"]._get("test.studio.model_action").id,
            "method": "action_confirm",
            "approval_group_id": self.env.ref("base.group_user").id,
            "approver_ids": [Command.link(self.admin_user.id)],
            "users_to_notify": [Command.link(self.admin_user.id)],
        })

        url = f"/odoo/action-studio?mode=editor&_action={self.testAction.id}&_view_type=form&_tab=views&menu_id={self.testMenu.id}"
        self.start_tour(url, "test_web_studio.test_disable_approvals", login="admin")
        self.assertEqual(rule.active, False)

    def test_disable_approvals_via_kanban(self):
        rule = self.env["studio.approval.rule"].create({
            "model_id": self.env["ir.model"]._get("test.studio.model_action").id,
            "method": "action_confirm",
            "approval_group_id": self.env.ref("base.group_user").id,
            "approver_ids": [Command.link(self.admin_user.id)],
            "users_to_notify": [Command.link(self.admin_user.id)],
        })

        url = f"/odoo/action-studio?mode=editor&_action={self.testAction.id}&_view_type=form&_tab=views&menu_id={self.testMenu.id}"
        self.start_tour(url, "test_web_studio.test_disable_approvals_via_kanban", login="admin")
        self.assertEqual(rule.active, False)
