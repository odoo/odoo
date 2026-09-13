from datetime import timedelta

from odoo.fields import Command, Date
from odoo.tests.common import TransactionCase, new_test_user


class TestOne2manyClearArchived(TransactionCase):
    def _make_family(self):
        Category = self.env["res.partner.tag"]
        parent = Category.create({"name": "parent"})
        active = Category.create({"name": "active child", "parent_id": parent.id})
        archived = Category.create(
            {"name": "archived child", "parent_id": parent.id, "active": False}
        )
        self.env.flush_all()
        return parent, active, archived

    def test_clear_detaches_archived_lines(self):
        parent, active, archived = self._make_family()
        parent.write({"child_ids": [Command.clear()]})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(active.exists(), "active line is removed by CLEAR")
        remaining = archived.exists()
        if remaining:
            self.assertFalse(
                remaining.parent_id,
                "archived line must be detached by CLEAR like an active one",
            )

    def test_set_detaches_archived_lines(self):
        parent, _active, archived = self._make_family()
        keeper = self.env["res.partner.tag"].create(
            {"name": "keeper", "parent_id": parent.id}
        )
        parent.write({"child_ids": [Command.set(keeper.ids)]})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(keeper.parent_id, parent)
        remaining = archived.exists()
        if remaining:
            self.assertFalse(
                remaining.parent_id,
                "archived line must be detached by SET like an active one",
            )


class TestCompanyDependentInsertFallback(TransactionCase):
    def test_create_with_user_scoped_default_round_trips(self):
        user = new_test_user(self.env, "audit_cd_user", groups="base.group_system")
        IrDefault = self.env["ir.default"]
        IrDefault.set("test_orm.company", "foo", "GLOBAL")
        IrDefault.set("test_orm.company", "foo", "USERVAL", user_id=user.id)
        self.env.flush_all()
        self.env.registry.clear_cache()

        record = self.env["test_orm.company"].with_user(user).create({"foo": "USERVAL"})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            record.with_user(user).foo,
            "USERVAL",
            "the creating user must read back the value they wrote",
        )
        self.assertEqual(
            record.foo,
            "USERVAL",
            "other users must see the written value, not the global default",
        )
        self.env.cr.execute(
            "SELECT foo FROM test_orm_company WHERE id = %s", [record.id]
        )
        self.assertIsNotNone(self.env.cr.fetchone()[0])

    def test_create_matching_superuser_fallback_stores_null(self):
        IrDefault = self.env["ir.default"]
        IrDefault.set("test_orm.company", "foo", "GLOBAL")
        self.env.flush_all()
        self.env.registry.clear_cache()
        record = self.env["test_orm.company"].create({"foo": "GLOBAL"})
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT foo FROM test_orm_company WHERE id = %s", [record.id]
        )
        self.assertIsNone(self.env.cr.fetchone()[0])
        self.env.invalidate_all()
        self.assertEqual(record.foo, "GLOBAL")


class TestDatetimeEqualsDate(TransactionCase):
    def test_equals_date_matches_whole_day(self):
        record = self.env["test_orm.mixed"].create({})
        self.env.flush_all()
        Model = self.env["test_orm.mixed"]
        today = Date.context_today(record, record.create_date)
        whole_day = Model.search_count(
            [
                "&",
                ("create_date", ">=", today),
                ("create_date", "<", today + timedelta(days=1)),
                ("id", "=", record.id),
            ]
        )
        self.assertEqual(whole_day, 1)
        self.assertEqual(
            Model.search_count([("create_date", "=", today), ("id", "=", record.id)]),
            1,
            "'=' with a date must cover the whole day",
        )
        self.assertEqual(
            Model.search_count([("create_date", "=", "today"), ("id", "=", record.id)]),
            1,
            "'=' with 'today' must cover the whole day",
        )
        self.assertEqual(
            Model.search_count([("create_date", "!=", today), ("id", "=", record.id)]),
            0,
            "'!=' with a date is the complement of the whole day",
        )
