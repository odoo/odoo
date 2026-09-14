from odoo import Command
from odoo.exceptions import AccessError, LockError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


class TestORM(TransactionCase):
    @mute_logger("odoo.models")
    def test_access_deleted_records(self):
        c1 = self.env["res.partner.tag"].create({"name": "W"})
        c2 = self.env["res.partner.tag"].create({"name": "Y"})
        c1.unlink()

        user = self.env["res.users"].create(
            {
                "name": "test user",
                "login": "test2",
                "group_ids": [Command.set([self.ref("base.group_user")])],
            }
        )
        cs = (c1 + c2).with_user(user)
        self.assertEqual(
            [{"id": c2.id, "name": "Y"}],
            cs.read(["name"]),
            "read() should skip deleted records",
        )
        self.assertEqual([], cs[0].read(["name"]), "read() should skip deleted records")

        self.assertTrue(c1.unlink(), "Re-deleting should be a no-op")

    @mute_logger("odoo.models")
    def test_access_partial_deletion(self):
        Model = self.env["res.country"]
        display_name_field = Model._fields["display_name"]
        self.assertTrue(
            display_name_field.compute and not display_name_field.store,
            "test assumption not satisfied",
        )

        records = Model.create(
            [
                {"name": name[0], "code": name[1]}
                for name in (["Foo", "ZV"], ["Bar", "ZX"], ["Baz", "ZY"])
            ]
        )
        for record in records:
            _ = record.name
            record.unlink()

        records = Model.create(
            [
                {"name": name[0], "code": name[1]}
                for name in (["Foo", "ZV"], ["Bar", "ZX"], ["Baz", "ZY"])
            ]
        )
        for record in records:
            _ = record.display_name
            record.unlink()

    @mute_logger("odoo.models", "odoo.addons.base.models.ir_rule")
    def test_access_filtered_records(self):
        p1 = self.env["res.partner"].create({"name": "W"})
        p2 = self.env["res.partner"].create({"name": "Y"})
        user = self.env["res.users"].create(
            {
                "name": "test user",
                "login": "test2",
                "group_ids": [Command.set([self.ref("base.group_user")])],
            }
        )

        partner_model = self.env["ir.model"].search([("model", "=", "res.partner")])
        self.env["ir.rule"].create(
            {
                "name": "Y is invisible",
                "domain_force": [("id", "!=", p1.id)],
                "model_id": partner_model.id,
            }
        )

        partners = self.env["res.partner"].with_user(user).search([])
        self.assertNotIn(p1, partners, "W should not be visible...")
        self.assertIn(p2, partners, "... but Y should be visible")

        with self.assertRaises(AccessError):
            p1.with_user(user).read(["name"])
        with self.assertRaises(AccessError):
            p1.with_user(user).write({"name": "foo"})
        with self.assertRaises(AccessError):
            p1.with_user(user).unlink()

        p2.unlink()
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).read(["name"])
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).unlink()

    def test_read(self):
        partner = self.env["res.partner"].create({"name": "MyPartner1"})
        result = partner.read()
        self.assertIsInstance(result, list)

    @mute_logger("odoo.models")
    def test_search_read(self):
        partner = self.env["res.partner"]

        partner.create({"name": "MyPartner1"})
        found = partner.search_read([("name", "=", "MyPartner1")], ["name"])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["name"], "MyPartner1")
        self.assertIn("id", found[0])

        partner.create({"name": "MyPartner2"})
        found = partner.search_read(
            [("name", "like", "MyPartner")], ["name"], order="name"
        )
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["name"], "MyPartner1")
        self.assertEqual(found[1]["name"], "MyPartner2")
        found = partner.search_read(
            [("name", "like", "MyPartner")], ["name"], order="name desc"
        )
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["name"], "MyPartner2")
        self.assertEqual(found[1]["name"], "MyPartner1")

        found = partner.search_read([("name", "=", "Does not exists")], ["name"])
        self.assertEqual(len(found), 0)

        found = partner.search_read([], [], limit=1)
        self.assertEqual(len(found), 1)
        for field in ("id", "name", "display_name", "email"):
            self.assertIn(field, found[0])

        found = partner.search_read([], False, limit=1)
        self.assertEqual(len(found), 1)
        for field in ("id", "name", "display_name", "email"):
            self.assertIn(field, found[0])

    @mute_logger("odoo.db")
    def test_exists(self):
        partner = self.env["res.partner"]

        recs = partner.search([])
        self.assertTrue(recs)
        self.assertEqual(recs.exists(), recs)

        recs = partner.new({})
        self.assertTrue(recs.exists())

        recs = partner.browse([0])
        self.assertFalse(recs.exists())

    def test_lock_for_update(self):
        partner = self.env["res.partner"]
        p1, p2 = partner.search([("name", "!=", False)], limit=2)

        p1.lock_for_update(allow_referencing=True)
        p1.lock_for_update(allow_referencing=False)

        with self.env.registry.cursor() as cr:
            recs = (p1 + p2).with_env(partner.env(cr=cr))
            with self.assertRaises(LockError):
                recs.lock_for_update()
            sub_p2 = recs[1]
            sub_p2.lock_for_update()

            p2.invalidate_model()
            self.assertTrue(p2.name)
            with self.assertRaises(LockError):
                p2.lock_for_update()

            p1.invalidate_model()
            self.assertTrue(p1.name)

        p2.lock_for_update()

        inexisting = partner.create({"name": "inexisting"})
        inexisting.unlink()
        self.assertFalse(inexisting.exists())
        with self.assertRaises(LockError):
            inexisting.lock_for_update()

    def test_try_lock_for_update(self):
        partner = self.env["res.partner"]
        p1, p2, *_other = recs = partner.search([], limit=4)

        self.assertEqual(p1.try_lock_for_update(allow_referencing=True), p1)
        self.assertEqual(p1.try_lock_for_update(allow_referencing=False), p1)

        with self.env.registry.cursor() as cr:
            sub_recs = (p1 + p2).with_env(partner.env(cr=cr))
            self.assertEqual(sub_recs.try_lock_for_update(), sub_recs[1])

        self.assertEqual(recs.try_lock_for_update(limit=1), p1)
        self.assertEqual(recs.try_lock_for_update(), recs)

        self.assertEqual(recs[::-1].try_lock_for_update(limit=1), recs[-1])

    def test_write_duplicate(self):
        p1 = self.env["res.partner"].create({"name": "W"})
        (p1 + p1).write({"name": "X"})

    def test_m2m_store_trigger(self):
        group_user = self.env.ref("base.group_user")

        user = self.env["res.users"].create(
            {
                "name": "test",
                "login": "test_m2m_store_trigger",
                "group_ids": [Command.set([])],
            }
        )
        self.assertTrue(user.share)

        group_user.write({"user_ids": [Command.link(user.id)]})
        self.assertFalse(user.share)

        group_user.write({"user_ids": [Command.unlink(user.id)]})
        self.assertTrue(user.share)

    def test_create_multi(self):
        vals_list = [{"name": name} for name in ("Foo", "Bar", "Baz")]
        vals_list[0]["email"] = "foo@example.com"
        for vals in vals_list:
            record = self.env["res.bank"].create(vals)
            self.assertEqual(len(record), 1)
            self.assertEqual(record.name, vals["name"])
            self.assertEqual(record.email, vals.get("email", False))

        records = self.env["res.bank"].create([])
        self.assertFalse(records)

        records = self.env["res.bank"].create(vals_list)
        self.assertEqual(len(records), len(vals_list))
        for record, vals in zip(records, vals_list, strict=False):
            self.assertEqual(record.name, vals["name"])
            self.assertEqual(record.email, vals.get("email", False))

        vals_list = [
            {
                "name": "Foo",
                "state_ids": [
                    Command.create({"name": "North Foo", "code": "NF"}),
                    Command.create({"name": "South Foo", "code": "SF"}),
                    Command.create({"name": "West Foo", "code": "WF"}),
                    Command.create({"name": "East Foo", "code": "EF"}),
                ],
                "code": "ZV",
            },
            {
                "name": "Bar",
                "state_ids": [
                    Command.create({"name": "North Bar", "code": "NB"}),
                    Command.create({"name": "South Bar", "code": "SB"}),
                ],
                "code": "ZX",
            },
        ]
        foo, bar = self.env["res.country"].create(vals_list)
        self.assertEqual(foo.name, "Foo")
        self.assertCountEqual(foo.mapped("state_ids.code"), ["NF", "SF", "WF", "EF"])
        self.assertEqual(bar.name, "Bar")
        self.assertCountEqual(bar.mapped("state_ids.code"), ["NB", "SB"])


class TestInherits(TransactionCase):
    def test_default(self):
        defaults = self.env["res.users"].default_get(["partner_id"])
        if "partner_id" in defaults:
            self.assertIsInstance(defaults["partner_id"], (bool, int))

    def test_create(self):
        partners_before = self.env["res.partner"].search([])
        user_foo = self.env["res.users"].create({"name": "Foo", "login": "foo"})

        self.assertNotIn(user_foo.partner_id, partners_before)

    def test_create_with_ancestor(self):
        partner_foo = self.env["res.partner"].create({"name": "Foo"})
        partners_before = self.env["res.partner"].search([])
        user_foo = self.env["res.users"].create(
            {"partner_id": partner_foo.id, "login": "foo"}
        )
        partners_after = self.env["res.partner"].search([])

        self.assertEqual(partners_before, partners_after)
        self.assertEqual(user_foo.name, "Foo")
        self.assertEqual(user_foo.partner_id, partner_foo)

    @mute_logger("odoo.models")
    def test_read(self):
        user_foo = self.env["res.users"].create({"name": "Foo", "login": "foo"})
        (user_values,) = user_foo.read()
        (partner_values,) = user_foo.partner_id.read()

        self.assertEqual(user_values["name"], partner_values["name"])
        self.assertEqual(user_foo.name, user_foo.partner_id.name)

    @mute_logger("odoo.models")
    def test_copy(self):
        user_foo = self.env["res.users"].create(
            {
                "name": "Foo",
                "login": "foo",
                "is_company": True,
            }
        )
        (foo_before,) = user_foo.read()
        del foo_before["create_date"]
        del foo_before["write_date"]
        user_bar = user_foo.copy({"login": "bar"})
        (foo_after,) = user_foo.read()
        del foo_after["create_date"]
        del foo_after["write_date"]
        self.assertEqual(foo_before, foo_after)

        self.assertEqual(user_bar.name, "Foo (copy)")
        self.assertEqual(user_bar.login, "bar")
        self.assertEqual(user_foo.is_company, user_bar.is_company)
        self.assertNotEqual(user_foo.id, user_bar.id)
        self.assertNotEqual(user_foo.partner_id.id, user_bar.partner_id.id)

    @mute_logger("odoo.models")
    def test_copy_with_ancestor(self):
        user_foo = self.env["res.users"].create(
            {"login": "foo", "name": "Foo", "signature": "Foo"}
        )
        partner_bar = self.env["res.partner"].create({"name": "Bar"})

        (foo_before,) = user_foo.read()
        del foo_before["create_date"]
        del foo_before["write_date"]
        del foo_before["login_date"]
        partners_before = self.env["res.partner"].search([])
        user_bar = user_foo.copy({"partner_id": partner_bar.id, "login": "bar"})
        (foo_after,) = user_foo.read()
        del foo_after["create_date"]
        del foo_after["write_date"]
        del foo_after["login_date"]
        partners_after = self.env["res.partner"].search([])

        self.assertEqual(foo_before, foo_after)
        self.assertEqual(partners_before, partners_after)

        self.assertNotEqual(user_foo.id, user_bar.id)
        self.assertEqual(user_bar.partner_id.id, partner_bar.id)
        self.assertEqual(user_bar.login, "bar", "login is given from copy parameters")
        self.assertFalse(
            user_bar.password,
            "password should not be copied from original record",
        )
        self.assertEqual(user_bar.name, "Bar", "name is given from specific partner")
        self.assertEqual(
            user_bar.signature, user_foo.signature, "signature should be copied"
        )

    @mute_logger("odoo.models")
    def test_write_date(self):
        user = self.env.user
        write_date_before = user.write_date

        user.write(
            {
                "image_1920": "R0lGODlhAQABAIAAAP///////yH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
            }
        )
        write_date_after = user.write_date
        self.assertNotEqual(write_date_before, write_date_after)


@tagged("post_install", "-at_install")
class TestCompanyDependent(TransactionCase):
    def test_flush_stale_flat_cache_entry_not_nulled(self):
        partner = self.env["res.partner"].create({"name": "Flat", "barcode": "BC-1"})
        field = partner._fields["barcode"]
        self.assertTrue(field.company_dependent, "barcode must be company_dependent")
        core = self.env.core

        core.get_field_data(field).clear()
        core.set_value(field, partner.id, "BC-1")

        col_val = field.get_column_update(partner)
        self.assertIsNotNone(
            col_val,
            "company-dependent field whose value lives only in a stale flat "
            "cache entry was flushed as SQL NULL",
        )
        self.assertIn("BC-1", col_val.obj.values())

    def test_orm_ondelete_restrict(self):
        for model in self.env.registry.values():
            for field in model._fields.values():
                if (
                    field.company_dependent
                    and field.type == "many2one"
                    and field.ondelete.lower() == "restrict"
                ):
                    for comodel_field in self.env[field.comodel_name]._fields.values():
                        self.assertFalse(
                            comodel_field.type == "many2one"
                            and comodel_field.ondelete == "cascade",
                            (
                                f"when a row for {comodel_field.comodel_name} is deleted, a row for {comodel_field.model_name} "
                                f"may also be deleted for sake of on delete cascade field {comodel_field}, which will "
                                f'bypass the ORM ondelete="restrict" check for a company dependent many2one field {field}. '
                                f"Please override the unlink method of {comodel_field.comodel_name} and do the ORM on "
                                f'delete cascade logic and remove/override the ondelete="cascade" of {comodel_field}'
                            ),
                        )


class TestReadFormatPrefetch(TransactionCase):
    SCALARS = {"name", "active", "create_date"}

    def _cold(self, records):
        records.env.flush_all()
        records.env.invalidate_all()
        return records.browse(records.ids)

    def test_read_format_does_not_scale_with_record_count(self):
        few = self.env["res.partner"].create([{"name": f"few {i}"} for i in range(2)])
        many = self.env["res.partner"].create(
            [{"name": f"many {i}"} for i in range(20)]
        )

        with self.assertQueryCount(__system__=1):
            self._cold(few)._read_format(self.SCALARS)

        with self.assertQueryCount(__system__=1):
            self._cold(many)._read_format(self.SCALARS)

    def test_read_format_matches_read(self):
        partners = self.env["res.partner"].create(
            [{"name": f"cmp {i}"} for i in range(5)]
        )
        fnames = sorted(self.SCALARS)
        from_read_format = self._cold(partners)._read_format(set(fnames))
        from_read = self._cold(partners).read(fnames)
        self.assertEqual(from_read_format, from_read)

    def test_read_format_missing_record_still_dropped(self):
        partners = self.env["res.partner"].create(
            [{"name": f"gone {i}"} for i in range(3)]
        )
        victim = partners[1]
        victim.unlink()
        result = self._cold(partners)._read_format(self.SCALARS)
        self.assertEqual([vals["id"] for vals in result], (partners - victim).ids)

    def test_read_format_on_new_records(self):
        Partner = self.env["res.partner"]
        new_records = Partner.new({"name": "new a"}) | Partner.new({"name": "new b"})
        result = new_records._read_format({"name"})
        self.assertEqual([vals["name"] for vals in result], ["new a", "new b"])


class TestReadFormatMany2oneBatch(TransactionCase):
    def _cold(self, records):
        records.env.flush_all()
        records.env.invalidate_all()
        return records.browse(records.ids)

    def test_batched_conversion_matches_the_per_value_one(self):
        parent = self.env["res.partner"].create({"name": "batch parent"})
        children = self.env["res.partner"].create(
            [{"name": f"batch child {i}", "parent_id": parent.id} for i in range(4)]
        )
        children |= self.env["res.partner"].create({"name": "batch orphan"})

        field = self.env["res.partner"]._fields["parent_id"]
        expected = [field.convert_to_read(child.parent_id, child) for child in children]
        self.assertEqual(
            field.convert_to_read_multi(
                [child.parent_id for child in children], children
            ),
            expected,
        )

    def test_batched_conversion_without_display_name(self):
        parent = self.env["res.partner"].create({"name": "bare parent"})
        children = self.env["res.partner"].create(
            [{"name": f"bare child {i}", "parent_id": parent.id} for i in range(3)]
        )
        rows = self._cold(children).read(["parent_id"], load=None)
        self.assertEqual([row["parent_id"] for row in rows], [parent.id] * 3)

    def test_unreadable_target_is_still_hidden(self):
        secret = self.env["res.partner"].create({"name": "SECRET BATCH PARENT"})
        visible = self.env["res.partner"].create({"name": "VISIBLE BATCH PARENT"})
        children = self.env["res.partner"].create(
            [
                {"name": "batch hidden child", "parent_id": secret.id},
                {"name": "batch visible child", "parent_id": visible.id},
            ]
        )
        self.env["ir.rule"].create(
            {
                "name": "hide the secret batch parent",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": [("id", "!=", secret.id)],
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "Batch reader",
                "login": "batch_reader",
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        rows = self._cold(children).with_user(user).read(["parent_id"])
        by_name = {row["id"]: row["parent_id"] for row in rows}
        self.assertFalse(
            by_name[children[0].id],
            "an unreadable parent must not be named, batched or not",
        )
        self.assertEqual(by_name[children[1].id][0], visible.id)

    def test_missing_target_degrades_instead_of_raising(self):
        Partner = self.env["res.partner"]
        holder = Partner.create({"name": "holder"})
        ghost = Partner.browse(
            max(Partner.search([], order="id desc", limit=1).id, 0) + 10**6
        )
        field = Partner._fields["parent_id"]
        self.assertEqual(
            field.convert_to_read_multi([ghost, Partner.browse()], holder),
            [False, False],
        )
        self.assertEqual(field.convert_to_read(ghost, holder), False)


class TestOrdinaryTableMemo(TransactionCase):
    def test_a_table_absent_from_the_memo_is_requeried(self):
        registry = self.env.registry
        saved = registry._ordinary_tables
        try:
            registry._ordinary_tables = {"res_partner": True}
            self.assertTrue(
                self.env["res.users"]._is_an_ordinary_table(),
                "a table the memo never queried must be looked up, not denied",
            )
            self.assertIs(registry._ordinary_tables.get("res_users"), True)
        finally:
            registry._ordinary_tables = saved

    def test_a_model_without_a_table_stays_negative(self):
        self.assertFalse(self.env["ir.fields.converter"]._is_an_ordinary_table())
