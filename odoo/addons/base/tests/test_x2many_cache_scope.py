from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestX2manyCacheScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="scope_x2many",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.parent = cls.env["res.partner"].create({"name": "scope parent"})
        cls.visible, cls.hidden = cls.env["res.partner"].create(
            [
                {"name": "scope visible", "parent_id": cls.parent.id},
                {"name": "scope hidden", "parent_id": cls.parent.id},
            ]
        )
        cls.env["ir.rule"].create(
            {
                "name": "scope: no hidden partners",
                "model_id": cls.env["ir.model"]._get_id("res.partner"),
                "domain_force": "[('name', 'not like', 'scope hidden')]",
                "groups": [Command.link(cls.env.ref("base.group_user").id)],
            }
        )
        cls.env.invalidate_all()

    def _as_user(self):
        return self.parent.with_user(self.user)

    def test_a_sudo_read_does_not_hand_the_user_the_hidden_child(self):
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        self.assertEqual(self._as_user().child_ids, self.visible)

    def test_a_user_read_does_not_starve_the_superuser(self):
        self.assertEqual(self._as_user().child_ids, self.visible)
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)

    def test_a_write_in_one_scope_is_seen_by_the_other(self):
        self.assertEqual(self._as_user().child_ids, self.visible)
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        added = self.env["res.partner"].create({"name": "scope added"})
        self.parent.sudo().write({"child_ids": [Command.link(added.id)]})
        self.assertEqual(
            self.parent.sudo().child_ids, self.visible | self.hidden | added
        )
        self.assertEqual(self._as_user().child_ids, self.visible | added)
        self._as_user().write({"child_ids": [Command.unlink(added.id)]})
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        self.assertEqual(self._as_user().child_ids, self.visible)

    def test_an_inverse_write_under_sudo_reaches_a_user_slot_filled_before(self):
        self.assertEqual(self._as_user().child_ids, self.visible)
        added = (
            self.env["res.partner"]
            .sudo()
            .create({"name": "scope added by parent_id", "parent_id": self.parent.id})
        )
        self.assertEqual(self._as_user().child_ids, self.visible | added)
        added.sudo().write({"parent_id": False})
        self.assertEqual(self._as_user().child_ids, self.visible)

    def test_a_user_write_serves_the_superuser_when_no_rule_filters_the_comodel(self):
        tag = self.env["res.partner.tag"].create({"name": "scope tag"})
        self.visible.with_user(self.user).write({"tag_ids": [Command.set(tag.ids)]})
        with self.assertQueryCount(0):
            self.assertEqual(self.visible.sudo().tag_ids, tag)

    def test_a_user_write_leaves_the_superuser_to_fetch_when_a_rule_filters(self):
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        self._as_user().write({"child_ids": [Command.unlink(self.visible.id)]})
        self.assertEqual(self._as_user().child_ids, self.env["res.partner"])
        self.assertEqual(self.parent.sudo().child_ids, self.hidden)

    def test_a_user_read_serves_the_superuser_when_no_rule_filters_the_comodel(self):
        tag = self.env["res.partner.tag"].create({"name": "scope read tag"})
        self.visible.write({"tag_ids": [Command.set(tag.ids)]})
        self.env.invalidate_all()
        self.assertEqual(self.visible.with_user(self.user).tag_ids, tag)
        with self.assertQueryCount(0):
            self.assertEqual(self.visible.sudo().tag_ids, tag)

    def test_a_record_created_by_a_user_serves_the_superuser_its_empty_x2many(self):
        created = (
            self.env["res.partner"]
            .with_user(self.user)
            .create({"name": "scope created"})
        )
        with self.assertQueryCount(0):
            self.assertFalse(created.sudo().child_ids)
