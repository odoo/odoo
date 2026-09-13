import json
import unittest

from odoo.tools import view_ir
from odoo.tools.view_ir import _generate


class TestViewIrSchema(unittest.TestCase):
    def setUp(self):
        self.schema = view_ir.schema()

    def test_every_view_type_declares_its_root_and_the_root_resolves_back(self):
        for name, spec in self.schema.types.items():
            with self.subTest(view_type=name):
                self.assertIn(spec.root, spec.nodes)
                self.assertEqual(self.schema.view_type_of(spec.root), name)

    def test_the_seven_relaxng_types_and_the_two_without_a_schema_are_all_present(self):
        self.assertLessEqual(
            {
                "activity",
                "calendar",
                "graph",
                "list",
                "pivot",
                "search",
                "form",
                "kanban",
            },
            set(self.schema.types),
        )

    def test_every_declared_attribute_type_is_a_known_type_or_an_enum(self):
        tables = [
            self.schema.common_attrs,
            self.schema.html_attrs,
            self.schema.patch_attrs,
        ]
        tables += [n.attrs for n in self.schema.patch_nodes.values()]
        tables += [
            n.attrs for t in self.schema.types.values() for n in t.nodes.values()
        ]
        for table in tables:
            for attr, attr_type in table.items():
                with self.subTest(attr=attr):
                    if isinstance(attr_type, list):
                        self.assertTrue(attr_type)
                    else:
                        self.assertIn(attr_type, self.schema.attr_types)

    def test_attribute_lookup_falls_through_node_html_common_and_patch_tables(self):
        self.assertEqual(self.schema.attr_type("form", "field", "readonly"), "pyexpr")
        self.assertEqual(self.schema.attr_type("form", "field", "invisible"), "pyexpr")
        self.assertEqual(self.schema.attr_type("form", "div", "class"), "str")
        self.assertEqual(
            self.schema.attr_type("form", "div", "position"),
            ["after", "before", "inside", "replace", "attributes", "move"],
        )
        self.assertEqual(
            self.schema.attr_type("form", "field", "decoration-danger"), "pyexpr"
        )
        self.assertEqual(self.schema.attr_type("kanban", "t", "t-if"), "qweb")
        self.assertEqual(self.schema.attr_type(None, "xpath", "expr"), "str")
        self.assertIsNone(self.schema.attr_type("form", "field", "no_such_attribute"))

    def test_html_tags_are_never_view_node_kinds(self):
        for name, spec in self.schema.types.items():
            with self.subTest(view_type=name):
                self.assertFalse(self.schema.html_tags & set(spec.nodes))

    def test_children_lists_only_name_declared_kinds_or_html(self):
        for name, spec in self.schema.types.items():
            allowed = set(spec.nodes) | {"html"} | set(self.schema.patch_nodes)
            for kind, node in spec.nodes.items():
                if node.children is None:
                    continue
                with self.subTest(view_type=name, kind=kind):
                    self.assertLessEqual(node.children, allowed)

    def test_the_json_schema_rendition_is_a_draft_2020_12_document_per_view_type(self):
        rendered = _generate.render_json_schema(self.schema)
        self.assertEqual(
            rendered["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )
        self.assertEqual(set(rendered["$defs"]), {"node", *self.schema.types})
        json.dumps(rendered)

    def test_the_typescript_rendition_names_every_view_type(self):
        rendered = _generate.render_dts(self.schema)
        for name in self.schema.types:
            self.assertIn(
                f"export type {_generate._ts_type_name(name)}Kind =", rendered
            )
        self.assertIn("export interface ViewIRNode {", rendered)

    def test_generated_files_are_fresh(self):
        self.assertEqual(
            _generate.stale(),
            [],
            "regenerate with: python -m odoo.tools.view_ir._generate",
        )
