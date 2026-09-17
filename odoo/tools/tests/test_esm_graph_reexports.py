import unittest
from unittest.mock import patch

from odoo.tools.assets import esm_graph
from odoo.tools.assets.esm_graph import (
    _TRANSITIVE_IMPORT_RE,
    _get_import_specifiers,
    get_escaping_relative_imports,
)
from odoo.tools.assets.esm_lexer import lex_module

SOURCE = """
import { a } from "./sibling";
export { b } from "../outside/thing";
export * from "../outside/star";
export const c = 1;
"""


class _Module:
    module_path = "@web/dir/mod"
    url = "/web/static/src/dir/mod.js"
    raw_content = SOURCE


class TestNamedReExportsAreSeen(unittest.TestCase):
    def test_the_regex_half_carries_named_re_exports(self):
        specs = {
            m.group("spec") or m.group("side")
            for m in _TRANSITIVE_IMPORT_RE.finditer(SOURCE)
        }
        self.assertIn("../outside/thing", specs)

    def test_the_lexer_reports_named_re_exports_itself(self):
        lexed = lex_module(SOURCE)
        if lexed is None:
            self.skipTest("no node on PATH; the lexer half cannot be exercised")
        self.assertEqual(lexed["reexportFrom"], ["../outside/thing"])
        self.assertEqual(lexed["starFrom"], ["../outside/star"])
        self.assertNotIn(
            "../outside/thing",
            {imp["n"] for imp in lexed["imports"]},
            "a re-export is not an import binding",
        )

    def test_the_regex_runs_only_when_the_lexer_cannot(self):
        with patch.object(esm_graph, "lex_module", return_value=None):
            self.assertEqual(
                _get_import_specifiers(SOURCE),
                {"./sibling", "../outside/thing", "../outside/star"},
            )

    def test_the_scan_reports_every_static_specifier(self):
        self.assertEqual(
            _get_import_specifiers(SOURCE),
            {"./sibling", "../outside/thing", "../outside/star"},
        )

    def test_an_escaping_named_re_export_is_reported(self):
        escapes = get_escaping_relative_imports([_Module()])
        self.assertIn(
            "../outside/thing",
            {spec for _path, spec, _resolved in escapes},
            "the escape this check exists to find",
        )


class TestTransitiveImportGuard(unittest.TestCase):
    def _specs(self, source):
        return {
            m.group("spec") or m.group("side")
            for m in _TRANSITIVE_IMPORT_RE.finditer(source)
        }

    def test_a_keyword_inside_a_longer_name_is_not_a_statement(self):
        source = (
            'reimport { a } from "not/a/statement";\n'
            'obj.import { b } from "not/a/member";\n'
            '$export { c } from "not/a/dollar";\n'
            'foo.import "not/a/side";\n'
            'import { d } from "real";\n'
            'export * from "real/star";\n'
            'import "real/side";\n'
        )
        self.assertEqual(self._specs(source), {"real", "real/star", "real/side"})

    def test_a_statement_at_the_start_of_the_source_is_seen(self):
        self.assertEqual(self._specs('import "first";'), {"first"})
        self.assertEqual(self._specs('export {a} from "first";'), {"first"})
