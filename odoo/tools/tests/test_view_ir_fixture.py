import json
import unittest
from pathlib import Path

from odoo.tools import view_ir

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "addons/web/static/tests/views/view_ir_fixture.js"
)
MARKER = "export const VIEW_IR_FIXTURE = "


def load_fixture():
    text = FIXTURE.read_text(encoding="utf-8")
    start = text.index(MARKER) + len(MARKER)
    return json.loads(text[start:].rstrip().removesuffix(";"))


class TestViewIrFixture(unittest.TestCase):
    def test_the_fixture_is_the_cross_language_contract(self):
        entries = load_fixture()
        self.assertGreaterEqual(len(entries), 12)
        for entry in entries:
            with self.subTest(entry=entry["name"]):
                node = view_ir.from_string(entry["arch"])
                self.assertEqual(node.to_dict(), entry["ir"])
                self.assertEqual(
                    view_ir.canonical(
                        view_ir.to_arch(view_ir.Node.from_dict(entry["ir"]))
                    ),
                    view_ir.canonical(view_ir.to_arch(node)),
                )

    def test_the_fixture_covers_the_edge_cases_the_client_must_match(self):
        names = {entry["name"] for entry in load_fixture()}
        self.assertLessEqual(
            {
                "edge-text-tail-comment",
                "edge-nbsp-and-entities",
                "edge-namespaces",
                "edge-empty-attr-and-cdata",
            },
            names,
        )
