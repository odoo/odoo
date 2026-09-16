import json

from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tests.common import HttpCase, TransactionCase, tagged


@tagged("web_unit", "web_search_panel")
class TestSearchPanelVersion(TransactionCase):
    def setUp(self):
        super().setUp()
        self.parent = self.env["res.partner"].create(
            {
                "name": "Plan-C Parent",
                "is_company": True,
            }
        )
        self.child = self.env["res.partner"].create(
            {
                "name": "Plan-C Child",
                "is_company": False,
                "parent_id": self.parent.id,
            }
        )

    def _call_select_range(self):
        return self.env["res.partner"].search_panel_select_range(
            "parent_id",
            search_domain=[("name", "ilike", "Plan-C")],
            enable_counters=True,
        )

    def test_select_range_returns_version(self):
        result = self._call_select_range()
        self.assertIn("__version", result)
        self.assertEqual(len(result["__version"]), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result["__version"]))

    def test_select_range_same_query_same_version(self):
        v1 = self._call_select_range()["__version"]
        v2 = self._call_select_range()["__version"]
        self.assertEqual(
            v1, v2, "Identical queries must produce identical version stamps"
        )

    def test_select_range_record_change_changes_version(self):
        v1 = self._call_select_range()["__version"]
        self.parent.name = "Plan-C Parent (renamed)"
        v2 = self._call_select_range()["__version"]
        self.assertNotEqual(
            v1, v2, "Record mutation must produce a different version stamp"
        )

    def test_select_multi_range_returns_version(self):
        result = self.env["res.partner"].search_panel_select_multi_range(
            "parent_id",
            search_domain=[("name", "ilike", "Plan-C")],
        )
        self.assertIn("__version", result)
        self.assertEqual(len(result["__version"]), 64)

    def test_version_field_does_not_collide_with_response_keys(self):
        result = self._call_select_range()
        self.assertTrue("values" in result or "error_msg" in result)


@tagged("web_unit", "web_search_panel")
class TestSearchPanelStaleSelection(TransactionCase):
    def test_select_range_on_removed_selection_value(self):
        partner = self.env["res.partner"].create({"name": "Stale Sel"})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET type = 'obsolete_value' WHERE id = %s",
            [partner.id],
        )
        partner.invalidate_recordset(["type"])
        result = self.env["res.partner"].search_panel_select_range("type")
        labels = {v.get("display_name") for v in result["values"]}
        self.assertIn("obsolete_value", labels)


@tagged("web_unit", "web_search_panel")
class TestWebSearchReadVersion(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partners = self.env["res.partner"].create(
            [
                {"name": "Plan-C WSR A", "is_company": True},
                {"name": "Plan-C WSR B", "is_company": False},
            ]
        )

    def _call(self):
        return self.env["res.partner"].web_search_read(
            [("name", "ilike", "Plan-C WSR")],
            {"display_name": {}, "is_company": {}},
        )

    def test_returns_version(self):
        result = self._call()
        self.assertIn("__version", result)
        self.assertEqual(len(result["__version"]), 64)
        self.assertEqual(result["length"], 2)
        self.assertEqual(len(result["records"]), 2)

    def test_same_query_same_version(self):
        self.assertEqual(self._call()["__version"], self._call()["__version"])

    def test_record_change_changes_version(self):
        v1 = self._call()["__version"]
        self.partners[0].name = "Plan-C WSR A (renamed)"
        v2 = self._call()["__version"]
        self.assertNotEqual(v1, v2)


@tagged("web_unit", "web_search_panel")
class TestSearchPanelUnknownField(TransactionCase):
    def test_select_range_unknown_field_raises_usererror(self):
        with self.assertRaises(UserError):
            self.env["res.partner"].search_panel_select_range("no_such_field_xyz")

    def test_select_multi_range_unknown_field_raises_usererror(self):
        with self.assertRaises(UserError):
            self.env["res.partner"].search_panel_select_multi_range("no_such_field_xyz")

    def test_known_field_still_works(self):
        result = self.env["res.partner"].search_panel_select_range("parent_id")
        self.assertIn("values", result)


@tagged("post_install", "-at_install", "web_http", "web_search_panel")
class TestWebReadEnvelopeVersion(HttpCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Plan-C Envelope Partner",
                "is_company": True,
            }
        )

    def _call_web_read(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/web/dataset/call_kw/res.partner/web_read",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": "res.partner",
                        "method": "web_read",
                        "args": [[self.partner.id]],
                        "kwargs": {
                            "specification": {"display_name": {}, "is_company": {}}
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_envelope_carries_version_sibling(self):
        envelope = self._call_web_read()
        self.assertIn("version", envelope, "envelope must carry version sibling")
        self.assertEqual(len(envelope["version"]), 64)
        self.assertIsInstance(envelope["result"], list)

    def test_same_query_same_version(self):
        v1 = self._call_web_read()["version"]
        v2 = self._call_web_read()["version"]
        self.assertEqual(v1, v2)

    def test_record_change_changes_version(self):
        v1 = self._call_web_read()["version"]
        self.partner.name = "Plan-C Envelope Partner (renamed)"
        v2 = self._call_web_read()["version"]
        self.assertNotEqual(v1, v2)


@tagged("web_unit", "web_search_panel")
class TestWebReadGroupVersion(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["res.partner"].create(
            [
                {"name": "Plan-C RG A1", "is_company": True},
                {"name": "Plan-C RG A2", "is_company": True},
                {"name": "Plan-C RG B1", "is_company": False},
            ]
        )

    def _call(self):
        return self.env["res.partner"].web_read_group(
            [("name", "ilike", "Plan-C RG")],
            ["is_company"],
            ["__count"],
        )

    def test_returns_version(self):
        result = self._call()
        self.assertIn("__version", result)
        self.assertEqual(len(result["__version"]), 64)
        self.assertIn("groups", result)
        self.assertIn("length", result)

    def test_same_query_same_version(self):
        self.assertEqual(self._call()["__version"], self._call()["__version"])

    def test_group_change_changes_version(self):
        v1 = self._call()["__version"]
        self.env["res.partner"].create(
            {
                "name": "Plan-C RG A3",
                "is_company": True,
            }
        )
        v2 = self._call()["__version"]
        self.assertNotEqual(v1, v2)


@tagged("web_unit", "web_search_panel")
class TestSearchPanelHierarchy(TransactionCase):
    def test_cycle_terminates_without_mutating_input(self):
        class BoundedRecord(dict):
            reads = 0

            def __getitem__(self, key):
                if key == "parent_id":
                    self.reads += 1
                    if self.reads > 10:
                        raise AssertionError(
                            "cyclic hierarchy repeatedly revisited a row"
                        )
                return super().__getitem__(key)

        for parents in ([1], [2, 1], [2, 1, 2]):
            with self.subTest(parents=parents):
                records = [
                    BoundedRecord(id=index, parent_id=(parent, "Parent"))
                    for index, parent in enumerate(parents, 1)
                ]
                original = [dict(record) for record in records]
                result = self.env[
                    "res.partner"
                ]._search_panel_filter_parent_hierarchy(
                    records,
                    "parent_id",
                    [record["id"] for record in records],
                )
                DebugLog("web.search.improve").logic("sanitized-cycle", records=result)
                self.assertEqual(records, original)
                by_id = {record["id"]: record for record in result}
                self.assertEqual(len(result), len(records))
                for start in by_id:
                    seen = set()
                    current = start
                    while current:
                        self.assertNotIn(current, seen)
                        seen.add(current)
                        parent = by_id[current]["parent_id"]
                        current = parent and parent[0]

    def test_missing_ancestor_still_excludes_its_whole_branch(self):
        records = [
            {"id": 1, "parent_id": (99, "Hidden")},
            {"id": 2, "parent_id": (1, "Child")},
            {"id": 3, "parent_id": False},
        ]
        result = self.env["res.partner"]._search_panel_filter_parent_hierarchy(
            records,
            "parent_id",
            [1, 2, 3],
        )
        self.assertEqual(result, [records[2]])

    def test_shared_ancestors_keep_input_order(self):
        records = [
            {"id": 2, "parent_id": (1, "Parent")},
            {"id": 1, "parent_id": False},
            {"id": 3, "parent_id": (1, "Parent")},
        ]
        result = self.env["res.partner"]._search_panel_filter_parent_hierarchy(
            records,
            "parent_id",
            [2, 3],
        )
        self.assertEqual(result, records)
