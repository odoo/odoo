from odoo.tests.common import TransactionCase, new_test_user


class TestX2manyScopeFollowsWhatTheRulesRead(TransactionCase):
    # a user's x2many slot holds what the user's search returned; a sudo
    # write that changes that search's answer must empty the slot, however
    # far from the comodel the value the search read is stored

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, "scope_reader", groups="base.group_user")
        cls.shown, cls.hidden = cls.env["test_orm.scope_tag"].create(
            [{"name": "shown", "visible": True}, {"name": "hidden", "visible": False}]
        )
        cls.box = cls.env["test_orm.scope_box"].create({"name": "box"})
        cls.item_shown, cls.item_hidden = cls.env["test_orm.scope_item"].create(
            [
                {"name": "i1", "box_id": cls.box.id, "tag_id": cls.shown.id},
                {"name": "i2", "box_id": cls.box.id, "tag_id": cls.hidden.id},
            ]
        )
        cls.gated_open, cls.gated_blocked = cls.env["test_orm.scope_gated"].create(
            [{"name": "g1", "box_id": cls.box.id}, {"name": "g2", "box_id": cls.box.id}]
        )
        cls.block = cls.env["test_orm.scope_block"].create(
            {"gated_id": cls.gated_blocked.id}
        )
        cls.narrow_open, cls.narrow_hidden = cls.env["test_orm.scope_narrow"].create(
            [
                {"name": "n1", "box_id": cls.box.id},
                {"name": "n2", "box_id": cls.box.id, "hidden": True},
            ]
        )

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.env.invalidate_all()
        self.user_box = self.box.with_user(self.user)

    def _user_search(self, model_name):
        return (
            self.env[model_name]
            .with_user(self.user)
            .search([("box_id", "=", self.box.id)])
        )

    def test_a_rule_on_a_related_path_follows_a_write_at_its_end(self):
        self.assertEqual(self.user_box.item_ids, self.item_shown)
        self.hidden.visible = True
        self.assertEqual(self.user_box.item_ids, self.item_shown | self.item_hidden)
        self.shown.visible = False
        self.assertEqual(self.user_box.item_ids, self.item_hidden)
        self.assertEqual(
            self.user_box.item_ids, self._user_search("test_orm.scope_item")
        )

    def test_a_search_override_reading_another_model_follows_that_model(self):
        self.assertEqual(self.user_box.gated_ids, self.gated_open)
        self.block.unlink()
        self.assertEqual(self.user_box.gated_ids, self.gated_open | self.gated_blocked)
        self.env["test_orm.scope_block"].create({"gated_id": self.gated_open.id})
        self.assertEqual(self.user_box.gated_ids, self.gated_blocked)
        self.assertEqual(
            self.user_box.gated_ids, self._user_search("test_orm.scope_gated")
        )

    def test_a_search_override_follows_the_fields_it_reads_not_what_it_declares(
        self,
    ):
        self.assertEqual(self.user_box.narrow_ids, self.narrow_open)
        self.narrow_hidden.hidden = False
        self.assertEqual(
            self.user_box.narrow_ids, self.narrow_open | self.narrow_hidden
        )
        self.narrow_open.hidden = True
        self.assertEqual(self.user_box.narrow_ids, self.narrow_hidden)

    def test_a_write_the_rules_do_not_read_keeps_the_slot(self):
        self.assertEqual(self.user_box.item_ids, self.item_shown)
        self.shown.name = "renamed"
        with self.assertQueryCount(0):
            self.assertEqual(self.user_box.item_ids, self.item_shown)

    def test_a_row_the_superuser_holds_empty_keeps_its_slot_through_a_rule_write(
        self,
    ):
        empty = self.env["test_orm.scope_box"].create({"name": "empty"})
        self.assertFalse(empty.item_ids)
        self.assertFalse(empty.with_user(self.user).item_ids)
        self.assertEqual(self.user_box.item_ids, self.item_shown)
        self.shown.visible = False
        with self.assertQueryCount(0):
            self.assertFalse(empty.with_user(self.user).item_ids)
        self.assertFalse(self.user_box.item_ids)

    def test_a_read_verdict_follows_a_write_at_the_end_of_the_rule_path(self):
        item = self.item_shown.with_user(self.user)
        self.assertTrue(item.has_access("read"))
        self.shown.visible = False
        self.assertFalse(item.has_access("read"))
        self.shown.visible = True
        self.assertTrue(item.has_access("read"))

    def test_a_read_verdict_follows_the_deletion_of_the_row_the_rule_reads(self):
        item = self.item_shown.with_user(self.user)
        self.assertTrue(item.has_access("read"))
        self.shown.unlink()
        self.assertFalse(item.has_access("read"))
