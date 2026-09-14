import warnings

from odoo.exceptions import AccessError
from odoo.fields import Command, Domain
from odoo.tests.common import TransactionCase, new_test_user


class TestReadGroupGroupKeyRoundTrip(TransactionCase):
    def test_text_null_and_empty_string_are_one_group(self):
        partner = self.env["res.partner"]
        records = partner.create(
            [
                {"name": "rg-null", "ref": False},
                {"name": "rg-empty", "ref": ""},
                {"name": "rg-set", "ref": "R"},
            ]
        )
        self.env.flush_all()
        domain = [("id", "in", records.ids)]

        self.env.cr.execute(
            "SELECT COUNT(*) FROM res_partner WHERE id = ANY(%s) AND ref IS NULL",
            (records.ids,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1, "expected one NULL ref")
        self.env.cr.execute(
            "SELECT COUNT(*) FROM res_partner WHERE id = ANY(%s) AND ref = ''",
            (records.ids,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1, "expected one empty-string ref")

        groups = partner._read_group(domain, ["ref"], ["id:array_agg", "__count"])
        keys = [key for key, _ids, _count in groups]
        self.assertEqual(
            sorted(keys, key=repr),
            sorted([False, "R"], key=repr),
            "NULL and '' must form a single empty group, keyed False",
        )
        for key, ids, count in groups:
            with self.subTest(key=key):
                self.assertEqual(count, len(ids))
                drilldown = partner.search([*domain, ("ref", "=", key)])
                self.assertEqual(
                    set(drilldown.ids),
                    set(ids),
                    "opening the group must show exactly the records it counted",
                )

    def test_a_never_written_boolean_aggregates_as_false(self):
        Message = self.env["test_orm.message"]
        discussion = self.env["test_orm.discussion"].create(
            {"name": "booleans", "participants": [Command.link(self.env.user.id)]}
        )
        records = Message.create(
            [
                {"discussion": discussion.id, "body": "t", "important": True},
                {"discussion": discussion.id, "body": "n"},
                {"discussion": discussion.id, "body": "f", "important": False},
            ]
        )
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT COUNT(*) FROM test_orm_message"
            " WHERE id = ANY(%s) AND important IS NULL",
            (records.ids,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1, "expected one NULL important")
        [(every, any_, counted, distinct, values)] = Message._read_group(
            [("id", "in", records.ids)],
            [],
            [
                "important:bool_and",
                "important:bool_or",
                "important:count",
                "important:count_distinct",
                "important:array_agg",
            ],
        )
        self.assertEqual(
            (every, any_, counted, distinct, sorted(values)),
            (False, True, 3, 2, [False, False, True]),
            "the NULL is False to the ORM, as it is to a domain and to a groupby",
        )
        self.assertEqual(
            Message._read_group(
                [("id", "in", records.ids)], ["important"], ["__count"]
            ),
            [(False, 2), (True, 1)],
        )


class TestReadGroupAuditFixes(TransactionCase):
    def _read_group_deprecated(self, model, domain, fields, groupby, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return model.read_group(domain, fields, groupby, **kwargs)

    def test_read_group_empty_groupby_with_dict_fill_temporal(self):
        model = self.env["test_orm.lesson"].with_context(fill_temporal={})
        rows = self._read_group_deprecated(model, [], ["__count"], [])
        self.assertEqual(len(rows), 1)
        self.assertIn("__count", rows[0])

    def test_read_group_fill_temporal_unknown_keys_ignored(self):
        lessons = self.env["test_orm.lesson"].create(
            [
                {"name": "jan", "date": "2024-01-15"},
                {"name": "mar", "date": "2024-03-15"},
            ]
        )
        model = self.env["test_orm.lesson"].with_context(
            fill_temporal={
                "fill_from": "2024-01-01",
                "fill_to": "2024-04-30",
                "bogus_key": 42,
            }
        )
        rows = self._read_group_deprecated(
            model, [("id", "in", lessons.ids)], ["__count"], ["date:month"]
        )
        self.assertEqual(len(rows), 4)

    def test_read_group_range_accumulates_across_temporal_groupbys(self):
        discussion = self.env["test_orm.discussion"].create(
            {
                "name": "range accumulation",
                "participants": [Command.set([self.env.user.id])],
                "attributes_definition": [
                    {"name": "pdate", "type": "date", "string": "P Date"},
                ],
            }
        )
        Message = self.env["test_orm.message"]
        Message.create(
            [
                {
                    "discussion": discussion.id,
                    "name": "m1",
                    "attributes": {"pdate": "2024-03-10"},
                },
                {
                    "discussion": discussion.id,
                    "name": "m2",
                    "attributes": {"pdate": "2024-05-20"},
                },
                {
                    "discussion": discussion.id,
                    "name": "m3",
                    "attributes": {"pdate": False},
                },
            ]
        )
        rows = self._read_group_deprecated(
            Message.with_context(active_test=False),
            [("discussion", "=", discussion.id)],
            [],
            ["create_date:month", "attributes.pdate:month"],
            lazy=False,
        )
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertIn(
                "create_date:month",
                row["__range"],
                "the date field's __range entry was dropped by the property group",
            )
            self.assertIn("attributes.pdate:month", row["__range"])

    def test_formatted_read_group_malformed_having_raises_valueerror(self):
        model = self.env["test_orm.lesson"]
        model.create({"name": "l"})
        for having in (
            ["|", ("__count", ">", 1)],
            ["&"],
            ["!"],
        ):
            with (
                self.subTest(having=having),
                self.assertRaisesRegex(ValueError, "Invalid having clause"),
            ):
                model.formatted_read_group([], [], ["__count"], having=having)
        result = model.formatted_read_group(
            [], [], ["__count"], having=[("__count", ">", 0)]
        )
        self.assertTrue(result)

    def test_read_group_empty_query_checks_field_access(self):
        user = new_test_user(self.env, "audit_fix_user")
        course = self.env["test_orm.course"].with_user(user)
        empty_domain = [("id", "in", [])]

        with self.assertRaises(AccessError):
            course._read_group([], ["private_field"], ["__count"])

        with self.assertRaises(AccessError):
            course._read_group(empty_domain, ["private_field"], ["__count"])
        with self.assertRaises(AccessError):
            course._read_group(empty_domain, [], ["private_field:count"])
        with self.assertRaises(AccessError):
            course._read_grouping_sets(
                empty_domain, [["private_field"], []], ["__count"]
            )
        with self.assertRaises(ValueError):
            course._read_group(empty_domain, ["nonexistent_field"], [])
        with self.assertRaises(ValueError):
            course._read_group(empty_domain, [], ["name:bogus_agg"])

        self.assertEqual(course._read_group(empty_domain, ["name"], ["__count"]), [])
        self.assertEqual(
            course._read_group(empty_domain, [], ["__count"]),
            [(0,)],
        )


class TestGroupingSetsPropertiesComodel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.holder_a = cls.env["test_orm.properties.holder.a"].create({"name": "A"})
        cls.holder_b = cls.env["test_orm.properties.holder.b"].create({"name": "B"})
        cls.holder_a.definition = [
            {"name": "kind", "type": "char", "string": "Kind"},
        ]
        cls.holder_b.definition = [
            {
                "name": "kind",
                "type": "tags",
                "string": "Kind",
                "tags": [["x", "X", 1], ["y", "Y", 2]],
            },
        ]
        cls.target = cls.env["test_orm.properties.target"].create(
            {
                "name": "target",
                "holder_id": cls.holder_b.id,
                "attributes": {"kind": ["x", "y"]},
            }
        )
        cls.source = cls.env["test_orm.properties.source"].create(
            {
                "name": "source",
                "amount": 100.0,
                "target_id": cls.target.id,
                "holder_id": cls.holder_a.id,
            }
        )
        cls.env.flush_all()

    def test_the_definition_is_read_from_the_comodel(self):
        source = self.env["test_orm.properties.source"]
        target = self.env["test_orm.properties.target"]
        self.assertTrue(
            target._can_groupby_spec_duplicate_rows(target, "attributes.kind"),
            "a tags property duplicates rows; this is the ground truth",
        )
        self.assertTrue(
            source._can_groupby_spec_duplicate_rows(
                source, "target_id.attributes.kind"
            ),
            "reached through a many2one it must give the same answer -- reading "
            "the definition on the calling model instead answers False, because "
            "holder A declares 'kind' as a char",
        )

    def test_a_tags_property_behind_a_many2one_does_not_duplicate_aggregates(self):
        result = self.env["test_orm.properties.source"]._read_grouping_sets(
            [("id", "=", self.source.id)],
            [["target_id"], ["target_id.attributes.kind"]],
            ["amount:sum"],
        )
        by_target, by_tag = result
        self.assertEqual(
            by_target,
            [(self.target, 100.0)],
            "one record of 100.0 grouped by a plain many2one is 100.0; the "
            "tags expansion must not leak into this grouping set",
        )
        self.assertEqual(
            sorted(by_tag),
            [("x", 100.0), ("y", 100.0)],
            "the record carries both tags, so it legitimately appears once per tag",
        )

    def test_grouping_by_a_bare_properties_field_says_so(self):
        source = self.env["test_orm.properties.source"]
        with self.assertRaisesRegex(ValueError, "group by one of its properties"):
            source._can_groupby_spec_duplicate_rows(source, "attributes")


class TestExportXidDeterminism(TransactionCase):
    def test_ensure_xml_ids_oldest_wins_and_matches_get_metadata(self):
        record = self.env["test_orm.lesson"].create({"name": "xid lesson"})
        imd = self.env["ir.model.data"]
        first = imd.create(
            {
                "module": "__export__",
                "name": "audit_xid_first",
                "model": record._name,
                "res_id": record.id,
            }
        )
        second = imd.create(
            {
                "module": "__export__",
                "name": "audit_xid_second",
                "model": record._name,
                "res_id": record.id,
            }
        )
        self.assertLess(first.id, second.id)

        [(rec, xid)] = list(record._get_or_create_xml_ids())
        self.assertEqual(rec, record)
        self.assertEqual(xid, "__export__.audit_xid_first")
        self.assertEqual(
            record.get_metadata()[0]["xmlid"], "__export__.audit_xid_first"
        )


class TestWithCompanyNewId(TransactionCase):
    def test_with_company_unsaved_company_raises(self):
        model = self.env["test_orm.lesson"]
        ghost = self.env["res.company"].new({"name": "Ghost Co"})
        with self.assertRaisesRegex(ValueError, "saved .real-id. company"):
            model.with_company(ghost)
        self.assertIs(model.with_company(None), model)
        self.assertIs(model.with_company(self.env["res.company"].browse()), model)
        result = model.with_company(self.env.company)
        self.assertEqual(result.env.company, self.env.company)


class TestSearchDisplayNameRobustness(TransactionCase):
    def test_unconvertible_scalar_value_does_not_raise(self):
        model = self.env["test_orm.lesson"]
        self.patch(self.registry["test_orm.lesson"], "_rec_names_search", ["date"])
        domain = model._search_display_name("=", object())
        self.assertTrue(Domain(domain).is_false())


class TestCopyTranslationsAlignment(TransactionCase):
    def test_copy_translations_skips_on_o2m_length_mismatch(self):
        Discussion = self.env["test_orm.discussion"]
        participants = [Command.link(self.env.user.id)]
        old = Discussion.create(
            {
                "name": "old",
                "participants": participants,
                "messages": [
                    Command.create({"body": "first"}),
                    Command.create({"body": "second"}),
                ],
            }
        )
        new = Discussion.create(
            {
                "name": "new",
                "participants": participants,
                "messages": [Command.create({"body": "first"})],
            }
        )
        with self.assertLogs("odoo.models", level="DEBUG") as capture:
            old.copy_translations(new)
        self.assertTrue(
            any(
                "skipping one2many field 'messages'" in line for line in capture.output
            ),
            capture.output,
        )

    def test_copy_translations_aligned_lines_still_copied(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        Discussion = self.env["test_orm.discussion"]
        old = Discussion.create(
            {
                "name": "old",
                "participants": [Command.link(self.env.user.id)],
                "messages": [
                    Command.create({"body": "b1", "label": "Label A"}),
                    Command.create({"body": "b2", "label": "Label B"}),
                ],
            }
        )
        old.messages.sorted(key="id")[0].with_context(
            lang="fr_FR"
        ).label = "Etiquette A"
        copied = old.copy()
        copied_lines = copied.messages.sorted(key="id")
        self.assertEqual(len(copied_lines), 2)
        self.assertEqual(
            copied_lines[0].with_context(lang="fr_FR").label, "Etiquette A"
        )
