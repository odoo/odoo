from odoo.exceptions import AccessError
from odoo.tests import common, new_test_user


@common.tagged("post_install", "-at_install", "web_unit", "web_read")
class TestWebReadRelational(common.TransactionCase):
    def test_many2one_subfield_resolution(self):
        parent = self.env["res.partner"].create(
            {"name": "Parent Co", "is_company": True}
        )
        child = self.env["res.partner"].create(
            {"name": "Child", "parent_id": parent.id}
        )
        res = child.web_read(
            {"name": {}, "parent_id": {"fields": {"display_name": {}}}}
        )
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "Child")
        self.assertIsInstance(res[0]["parent_id"], dict)
        self.assertEqual(res[0]["parent_id"]["display_name"], "Parent Co")

    def test_many2one_to_deleted_target_is_false(self):
        parent = self.env["res.partner"].create(
            {"name": "ToDelete", "is_company": True}
        )
        child = self.env["res.partner"].create(
            {"name": "Orphan", "parent_id": parent.id}
        )
        self.env.flush_all()
        parent.unlink()
        child.invalidate_recordset()
        res = child.web_read(
            {"name": {}, "parent_id": {"fields": {"display_name": {}}}}
        )
        self.assertFalse(
            res[0]["parent_id"], "deleted m2o target must resolve to False"
        )

    def test_x2many_limit_resolves_fields_but_returns_all_ids(self):
        parent = self.env["res.partner"].create({"name": "P", "is_company": True})
        for i in range(5):
            self.env["res.partner"].create({"name": f"C{i}", "parent_id": parent.id})
        self.env.flush_all()
        res = parent.web_read(
            {
                "child_ids": {"fields": {"name": {}}, "limit": 2, "order": "name desc"},
            }
        )
        child_ids = res[0]["child_ids"]
        self.assertEqual(len(child_ids), 5, "all related ids must be returned")
        resolved = [c for c in child_ids if "name" in c]
        stubs = [c for c in child_ids if "name" not in c]
        self.assertEqual(
            len(resolved), 2, "only `limit` co-records get fields resolved"
        )
        self.assertEqual(len(stubs), 3, "the rest are {id} stubs")
        first_two = [c["name"] for c in child_ids[:2]]
        self.assertEqual(first_two, sorted(first_two, reverse=True), "order honored")

    def test_x2many_no_order_filters_inaccessible_corecords(self):
        Partner = self.env["res.partner"]
        ok1 = Partner.create({"name": "VisibleChild1"})
        secret = Partner.create({"name": "ZZSECRET child"})
        ok2 = Partner.create({"name": "VisibleChild2"})
        parent = Partner.create(
            {
                "name": "AccessParent",
                "child_ids": [(6, 0, (ok1 + secret + ok2).ids)],
            }
        )
        self.env.flush_all()

        self.env["ir.rule"].create(
            {
                "name": "test hide secret partners",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "domain_force": "[('name', 'not ilike', 'ZZSECRET')]",
                "groups": [],
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "x2m access tester",
                "login": "x2m_access_tester",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertNotIn(secret.id, Partner.with_user(user).search([]).ids)

        res = parent.with_user(user).web_read({"child_ids": {"fields": {"name": {}}}})

        returned_ids = [c["id"] for c in res[0]["child_ids"]]
        self.assertEqual(
            returned_ids,
            [ok1.id, ok2.id],
            "rule-hidden co-record must be filtered out, not raise AccessError",
        )
        self.assertNotIn(
            secret.id, returned_ids, "inaccessible co-record id must not leak"
        )

    def test_many2one_to_inaccessible_target_keeps_its_id_and_hides_its_label(self):
        Partner = self.env["res.partner"]
        secret = Partner.create({"name": "ZZSECRET parent", "is_company": True})
        child = Partner.create({"name": "Child", "parent_id": secret.id})
        self.env.flush_all()

        self.env["ir.rule"].create(
            {
                "name": "test hide secret parents",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "domain_force": "[('name', 'not ilike', 'ZZSECRET')]",
                "groups": [],
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "m2o access tester",
                "login": "m2o_access_tester",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertNotIn(secret.id, Partner.with_user(user).search([]).ids)

        [res] = child.with_user(user).web_read(
            {"parent_id": {"fields": {"display_name": {}, "email": {}}}}
        )
        self.assertEqual(
            res["parent_id"],
            {"id": secret.id},
            "a sub-field spec must not change whether the many2one reports the "
            "value the readable record holds, and a target a record rule hides "
            "keeps its label and sub-fields to itself",
        )

    def test_many2one_to_a_private_address_hides_its_label(self):
        Partner = self.env["res.partner"]
        subject = Partner.create({"name": "Subject"})
        home = Partner.create(
            {"name": "Subject Home", "type": "private", "parent_id": subject.id}
        )
        record = Partner.create({"name": "Points at home", "parent_id": home.id})
        user = new_test_user(self.env, "private_address_reader")
        self.env.flush_all()
        self.assertNotIn(home.id, Partner.with_user(user).search([]).ids)

        [res] = record.with_user(user).web_read(
            {"parent_id": {"fields": {"display_name": {}}}}
        )
        self.assertEqual(res["parent_id"], {"id": home.id})
        [values] = record.with_user(user).read(["parent_id"])
        self.assertFalse(values["parent_id"])


@common.tagged("post_install", "-at_install", "web_unit", "web_read")
class TestWebResequence(common.TransactionCase):
    def test_resequence_calls_write_on_overriding_model(self):
        from unittest.mock import patch

        Partner = self.env["res.partner"]
        recs = Partner.create([{"name": f"P{i}", "color": 9} for i in range(3)])
        self.env.flush_all()

        real_write = type(Partner).write
        calls = []

        def counting_write(self, vals):
            if self._name == "res.partner":
                calls.append((tuple(self.ids), dict(vals)))
            return real_write(self, vals)

        with patch.object(type(Partner), "write", counting_write):
            recs.web_resequence({"id": {}}, field_name="color")

        self.assertEqual(
            len(calls), 3, "write() must fire once per record on an overriding model"
        )
        self.assertEqual(recs.mapped("color"), [0, 1, 2])

    def test_resequence_persists_values(self):
        Partner = self.env["res.partner"]
        recs = Partner.create([{"name": f"Q{i}", "color": 5} for i in range(4)])
        recs.web_resequence({"id": {}}, field_name="color", offset=10)
        self.env.flush_all()
        self.assertEqual(recs.mapped("color"), [10, 11, 12, 13])


@common.tagged("post_install", "-at_install", "web_unit", "web_read")
class TestWebReadFieldContext(common.TransactionCase):
    def test_ordered_x2many_with_active_test_context(self):
        parent = self.env["res.partner"].create({"name": "Parent"})
        self.env["res.partner"].create(
            [
                {"name": "C1", "parent_id": parent.id},
                {"name": "C2", "parent_id": parent.id},
            ]
        )
        self.env.flush_all()
        res = parent.with_context(active_test=False).web_read(
            {"child_ids": {"fields": {"display_name": {}}, "order": "id desc"}}
        )
        child_ids = [c["id"] for c in res[0]["child_ids"]]
        self.assertEqual(child_ids, sorted(child_ids, reverse=True))


@common.tagged("post_install", "-at_install", "web_unit", "web_read")
class TestWebReadIdOnlyAccessCheck(common.TransactionCase):
    def test_id_only_spec_enforces_access(self):
        parameter = (
            self.env["ir.config_parameter"]
            .sudo()
            .create({"key": "web_read.test", "value": "secret"})
        )
        user = new_test_user(self.env, login="web_read_unprivileged")
        record = parameter.with_user(user)
        with self.assertRaises(AccessError):
            record.web_read({"id": {}})

    def test_an_empty_recordset_reads_as_empty_without_access(self):
        user = new_test_user(self.env, login="web_read_unprivileged_empty")
        nothing = self.env["ir.config_parameter"].with_user(user).browse()
        self.assertEqual(nothing.web_read({"id": {}}), [])
        self.assertEqual(nothing.web_read({"key": {}}), [])
