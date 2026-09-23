from unittest.mock import patch

from psycopg.errors import UniqueViolation

from odoo.exceptions import ValidationError
from odoo.libs.colors import TAG_COLORS
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestTagTag(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Tag = cls.env["tag.tag"]
        cls.root = Tag.create({"name": "Rootag"})
        cls.mid = Tag.create({"name": "Midtag", "parent_id": cls.root.id})
        cls.leaf = Tag.create({"name": "Leaftag", "parent_id": cls.mid.id})
        cls.other = Tag.create({"name": "Loosetag"})

    def test_a_code_computed_earlier_in_the_transaction_is_taken(self):
        Tag = self.env["tag.tag"]
        first = Tag.create({"name": "Crimson Dup"})
        self.assertTrue(first.code)
        second = Tag.create({"name": "crimson dup"})
        self.assertNotEqual(first.code, second.code)
        self.env.flush_all()

    def test_color_default_is_overridable_and_preserves_explicit_zero(self):
        Tag = self.env["tag.tag"]
        with patch.object(type(Tag), "_default_color", return_value=7):
            self.assertEqual(Tag.create({"name": "Default color"}).color, 7)
            self.assertEqual(Tag.create({"name": "No color", "color": 0}).color, 0)

    def test_shared_hex_validation_checks_every_record(self):
        Tag = self.env["tag.tag"]
        valid = Tag.new({"name": "#aBc"}) | Tag.new({"name": "#123456"})
        valid._check_hex_color_fields("name")
        self.assertEqual(valid.mapped("name"), ["#aBc", "#123456"])
        for value in ("#123456\n", "#abc\n", "red", "123456", "#123; color:red"):
            records = valid | Tag.new({"name": value})
            with self.subTest(value=value), self.assertRaises(ValidationError):
                records._check_hex_color_fields("name")
        with self.assertRaises(ValidationError):
            Tag.new({"name": "#abc"})._check_hex_color_fields("name", lengths=(6,))

    def test_shared_palette_validation_and_conversion(self):
        Tag = self.env["tag.tag"]
        for index, expected in enumerate(TAG_COLORS):
            tag = Tag.new({"color": index})
            tag._check_palette_color_fields("color", palette=TAG_COLORS)
            self.assertEqual(
                tag._color_index_to_hex(index, palette=TAG_COLORS), expected
            )
        for index in (-1, len(TAG_COLORS)):
            with self.subTest(index=index), self.assertRaises(ValidationError):
                Tag.new({"color": index})._check_palette_color_fields(
                    "color", palette=TAG_COLORS
                )
            self.assertEqual(
                Tag._color_index_to_hex(index, palette=TAG_COLORS, fallback="#8F8F8F"),
                "#8F8F8F",
            )

    def test_display_name_is_full_ancestor_path(self):
        self.assertEqual(self.root.display_name, "Rootag")
        self.assertEqual(self.mid.display_name, "Rootag / Midtag")
        self.assertEqual(self.leaf.display_name, "Rootag / Midtag / Leaftag")
        self.assertEqual(self.other.display_name, "Loosetag")

    def test_display_name_batched_recompute(self):
        tags = self.root + self.mid + self.leaf + self.other
        tags.invalidate_recordset(["display_name"])
        self.assertEqual(
            tags.mapped("display_name"),
            ["Rootag", "Rootag / Midtag", "Rootag / Midtag / Leaftag", "Loosetag"],
        )

    def test_display_name_follows_ancestor_rename(self):
        self.root.name = "Renamedtag"
        self.assertEqual(self.leaf.display_name, "Renamedtag / Midtag / Leaftag")

    def test_display_name_includes_archived_ancestor(self):
        self.root.active = False
        (self.mid + self.leaf).invalidate_recordset(["display_name"])
        self.assertEqual(self.leaf.display_name, "Rootag / Midtag / Leaftag")

    def test_display_name_newid_cycle_terminates(self):
        Tag = self.env["tag.tag"]
        first = Tag.new({"name": "Firstag"})
        second = Tag.new({"name": "Secondtag"})
        first.parent_id = second
        second.parent_id = first
        self.assertEqual(first.display_name, "Secondtag / Firstag")
        self.assertEqual(second.display_name, "Firstag / Secondtag")

    def test_display_name_newid_without_parent(self):
        self.assertEqual(self.env["tag.tag"].new({"name": "Solo"}).display_name, "Solo")

    def test_display_name_resolved_in_constant_queries(self):
        Tag = self.env["tag.tag"]
        parent = self.env["tag.tag"]
        deep_ids = []
        for level in range(10):
            parent = Tag.create({"name": f"Deep{level}", "parent_id": parent.id})
            deep_ids.append(parent.id)
        self.env.flush_all()
        self.env.invalidate_all()
        leaf = Tag.browse(deep_ids[-1])
        self.assertEqual(
            leaf.display_name,
            " / ".join(f"Deep{level}" for level in range(10)),
        )

    def test_search_display_name_like_expands_to_subtree(self):
        found = self.env["tag.tag"].search([("display_name", "like", "Midtag")])
        self.assertEqual(set(found.ids), {self.mid.id, self.leaf.id})

        found = self.env["tag.tag"].search([("display_name", "like", "Rootag")])
        self.assertEqual(set(found.ids), {self.root.id, self.mid.id, self.leaf.id})

    def test_search_display_name_like_archived_root(self):
        self.root.active = False
        found = self.env["tag.tag"].search([("display_name", "like", "Rootag")])
        self.assertFalse(found)
        found = (
            self.env["tag.tag"]
            .with_context(active_test=False)
            .search([("display_name", "like", "Rootag")])
        )
        self.assertEqual(set(found.ids), {self.root.id, self.mid.id, self.leaf.id})

    def test_search_display_name_not_like_excludes_subtree(self):
        scope = (self.root + self.mid + self.leaf + self.other).ids
        found = self.env["tag.tag"].search(
            [("display_name", "not like", "Midtag"), ("id", "in", scope)]
        )
        self.assertEqual(set(found.ids), {self.root.id, self.other.id})

    def test_name_search_matches_subtree(self):
        found_ids = [rid for rid, _name in self.env["tag.tag"].name_search("Midtag")]
        self.assertIn(self.mid.id, found_ids)
        self.assertIn(self.leaf.id, found_ids)
        self.assertNotIn(self.root.id, found_ids)
        self.assertNotIn(self.other.id, found_ids)


class TestTagCode(TransactionCase):
    def _tag(self, **vals):
        return self.env["tag.tag"].create({"name": "Some Tag", **vals})

    def test_a_code_is_derived_from_the_name(self):
        self.assertEqual(self._tag(name="Hot Lead").code, "HOT_LEAD")

    def test_punctuation_and_case_are_normalised(self):
        self.assertEqual(self._tag(name="  très-Chaud!! ").code, "TR_S_CHAUD")

    def test_name_create_gets_a_code(self):
        tag_id, _label = self.env["tag.tag"].name_create("Widget Made")
        self.assertEqual(self.env["tag.tag"].browse(tag_id).code, "WIDGET_MADE")

    def test_an_explicit_code_is_kept(self):
        self.assertEqual(self._tag(name="Anything", code="MY_CODE").code, "MY_CODE")

    def test_renaming_does_not_move_the_code(self):
        tag = self._tag(name="Original")
        self.assertEqual(tag.code, "ORIGINAL")
        tag.name = "Renamed Entirely"
        self.assertEqual(tag.code, "ORIGINAL")

    def test_two_names_slugging_alike_do_not_collide(self):
        first = self._tag(name="Hot!")
        second = self._tag(name="Hot?")
        self.assertEqual(first.code, "HOT")
        self.assertEqual(second.code, "HOT_2")

    def test_the_same_name_under_two_parents_does_not_collide(self):
        left = self._tag(name="Region")
        right = self._tag(name="Zone")
        first = self._tag(name="North", parent_id=left.id)
        second = self._tag(name="North", parent_id=right.id)
        self.assertNotEqual(first.code, second.code)

    @mute_logger("odoo.db.cursor")
    def test_a_duplicate_code_is_refused(self):
        self._tag(name="First", code="SHARED")
        with self.assertRaises(UniqueViolation):
            self._tag(name="Second", code="SHARED")
            self.env.flush_all()

    def test_a_code_survives_a_batch_create(self):
        tags = self.env["tag.tag"].create(
            [{"name": "Bulk!"}, {"name": "Bulk?"}, {"name": "Bulk."}]
        )
        self.assertEqual(len(set(tags.mapped("code"))), 3)

    def test_a_strict_query_finds_the_tag_whatever_the_language(self):
        tag = self._tag(name="Findable", code="FINDABLE")
        self.assertEqual(
            self.env["tag.tag"].search([("code", "=", "FINDABLE")]),
            tag,
        )
