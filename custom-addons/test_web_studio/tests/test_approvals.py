from odoo import Command

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

    def test_approval_method_two_models(self):
        IrModel = self.env["ir.model"]

        self.env["studio.approval.rule"].create([
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            },
            {
                "model_id": IrModel._get("test.studio.model_action2").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
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
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name} An approval for 'False' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)

        with self.with_user("admin"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, "@test An approval for 'False' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)

        with self.with_user("test"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertTrue(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 0)

    def test_notify_higher_notification_order(self):
        IrModel = self.env["ir.model"]

        rules = self.env["studio.approval.rule"].create([
            {
                "name": "rule 1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "domain": "[('step', '<', 1)]",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            },
            {
                "name": "rule 2 - bis",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "domain": "[('step', '>=', 1)]",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
            },
            {
                "name": "rule 3",
                "model_id": IrModel._get("test.studio.model_action2").id,
                "method": "action_step",
                "notification_order": "1",
                "responsible_id": self.admin_user.id,
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
        self.assertEqual(model_action.message_ids[0].preview, "@test An approval for 'rule 2' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)

        spec = self.env["studio.approval.rule"].get_approval_spec("test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)
        self.assertEqual(len(spec["entries"]), 1)
        self.assertEqual(spec["entries"][0]["rule_id"][0], rules[0].id)

        with self.with_user("admin"):
            self.env["studio.approval.rule"].browse(rules[1].id).set_approval(model_action.id, True)

        # rule 2 is validated, rule 2 - bis doesn't apply, but is at the same level as rule 2 anyway, so it would not notify.
        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 0)

        spec = self.env["studio.approval.rule"].get_approval_spec("test.studio.model_action", method="action_step", action_id=False, res_id=model_action.id)
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
                "responsible_id": self.admin_user.id,
            },
            {
                "name": "R1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "exclusive_user": True,
                "responsible_id": self.admin_user.id,
            },
            {
                "name": "R2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "exclusive_user": True,
                "responsible_id": self.admin_user.id,
            },
            {
                "name": "R3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "3",
                "exclusive_user": True,
                "responsible_id": self.test_user_2.id,
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
        self.assertEqual(model_action.message_ids[:2].mapped("preview"), ["An approval for 'R2' has been requested on test", "An approval for 'R1' has been requested on test"])
        self.assertEqual(len(model_action.activity_ids), 2)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.admin_user.ids)

        with self.with_user("test"):
            # validates rule 1
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.admin_user.ids)

        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "An approval for 'R3' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.test_user_2.ids)

        with self.with_user("test_2"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 1)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 0)

    def test_no_responsible_but_user_notified(self):
        IrModel = self.env["ir.model"]
        self.env["studio.approval.rule"].create([
            {
                "name": "R0",
                "model_id": IrModel._get("test.studio.model_action").id,
                "group_id": self.env.ref("base.group_system").id,
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
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.demo_user.name} @test An approval for 'R0' has been requested on test")
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
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "name": "rule3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            }
        ])
        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()
        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.other_user.name} An approval for 'rule3' has been requested on test 2")
        self.assertEqual(len(model_action.activity_ids), 1)

        spec = self.env["studio.approval.rule"].get_approval_spec("test.studio.model_action", method="action_confirm", action_id=False, res_id=model_action.id)
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
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 1 - bis",
                "domain": "[('name', '=', 'test')]",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule 2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "domain": "[('name', '=', 'test')]",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
            },
            {
                "name": "rule3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "responsible_id": self.other_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
            }
        ])
        with self.with_user("demo"):
            self.env["studio.approval.rule"].browse(rules[0].id).set_approval(model_action.id, True)
        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.other_user.name} An approval for 'rule3' has been requested on test 2")
        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.user_id.id, self.other_user.id)

        spec = self.env["studio.approval.rule"].get_approval_spec("test.studio.model_action", method="action_confirm", action_id=False, res_id=model_action.id)
        self.assertEqual(len(spec["entries"]), 1)
        self.assertEqual(spec["entries"][0]["rule_id"][0], rules[0].id)


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
                <button name="action_confirm" type="object" studio_approval="True" class="mybutton"/>
            </form>
        """
        cls.admin_user = cls.env.ref("base.user_admin")

    def test_disable_approvals(self):
        rule = self.env["studio.approval.rule"].create({
            "model_id": self.env["ir.model"]._get("test.studio.model_action").id,
            "method": "action_confirm",
            "responsible_id": self.admin_user.id,
            "users_to_notify": [Command.link(self.admin_user.id)],
        })

        url = f"/web#action=studio&mode=editor&_action={self.testAction.id}&_view_type=form&_tab=views&menu_id={self.testMenu.id}"
        self.start_tour(url, "test_web_studio.test_disable_approvals", login="admin")
        self.assertEqual(rule.active, False)
