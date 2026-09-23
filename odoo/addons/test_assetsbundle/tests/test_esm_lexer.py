import shutil
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests.common import BaseCase
from odoo.tools.assets.esm_bridges import BridgeShimManager
from odoo.tools.json import scriptsafe as json

from .common import _Mod


class TestLexerWorkerDegradation(BaseCase):
    def _worker(self):
        from odoo.tools.assets.esm_lexer import _LexerWorker

        return _LexerWorker()

    def test_a_worker_that_cannot_spawn_disables_itself_once(self):
        from odoo.tools.assets import esm_lexer

        worker = self._worker()
        with patch.object(esm_lexer._LexerWorker, "_spawn", return_value=None):
            with self.assertLogs("odoo.assets.lexer", level="INFO") as logged:
                self.assertIsNone(worker.request("export const a = 1;"))
            self.assertIsNone(worker.request("export const a = 1;"))
        self.assertIn("worker_unavailable", "\n".join(logged.output))
        self.assertEqual(len(logged.output), 1, "the notice must not repeat per call")
        self.assertTrue(worker._disabled())

    def test_a_desynchronised_reply_is_retried_then_gives_up(self):
        from odoo.tools.assets import esm_lexer

        worker = self._worker()
        alive = SimpleNamespace(poll=lambda: None)
        with (
            patch.object(esm_lexer._LexerWorker, "_spawn", return_value=alive),
            patch.object(esm_lexer._LexerWorker, "_write_all"),
            patch.object(esm_lexer._LexerWorker, "_kill"),
            patch.object(
                esm_lexer._LexerWorker,
                "_read_line",
                return_value=json.dumps({"id": -1, "ok": True}),
            ),
            self.assertLogs("odoo.assets.lexer", level="DEBUG") as logged,
        ):
            self.assertIsNone(worker.request("export const a = 1;"))

        attempts = [ln for ln in logged.output if "worker_request_failed" in ln]
        self.assertEqual(len(attempts), 2, "one retry, then disabled")
        self.assertTrue(worker._disabled())
        self.assertIn("disabled=True", attempts[-1])

    def test_a_transient_failure_does_not_disable_the_worker(self):
        from odoo.tools.assets import esm_lexer

        worker = self._worker()
        alive = SimpleNamespace(poll=lambda: None)
        replies = [
            json.dumps({"id": -1, "ok": True}),
            json.dumps(
                {"id": 2, "ok": True, "imports": [], "names": [], "starFrom": []}
            ),
        ]
        with (
            patch.object(esm_lexer._LexerWorker, "_spawn", return_value=alive),
            patch.object(esm_lexer._LexerWorker, "_write_all"),
            patch.object(esm_lexer._LexerWorker, "_kill"),
            patch.object(esm_lexer._LexerWorker, "_read_line", side_effect=replies),
            self.assertLogs("odoo.assets.lexer", level="DEBUG"),
        ):
            response = worker.request("export const a = 1;")

        self.assertIsNotNone(response, "the retry must be allowed to succeed")
        self.assertFalse(worker._disabled())
        self.assertEqual(worker._consec_failures, 0, "the counter must reset")

    def test_source_the_worker_cannot_lex_is_not_a_worker_failure(self):
        from odoo.tools.assets import esm_lexer

        worker = self._worker()
        alive = SimpleNamespace(poll=lambda: None)
        with (
            patch.object(esm_lexer._LexerWorker, "_spawn", return_value=alive),
            patch.object(esm_lexer._LexerWorker, "_write_all"),
            patch.object(
                esm_lexer._LexerWorker,
                "_read_line",
                return_value=json.dumps({"id": 1, "ok": False, "error": "bad syntax"}),
            ),
            self.assertLogs("odoo.assets.lexer", level="DEBUG") as logged,
        ):
            response = worker.request("this is not javascript {")

        self.assertIs(response["ok"], False, "a refusal is an answer, not an outage")
        self.assertIn("source_unlexable", "\n".join(logged.output))
        self.assertFalse(
            worker._disabled(), "one unparseable file must not blind the whole run"
        )

    @unittest.skipUnless(shutil.which("node"), "node binary not available")
    def test_the_real_worker_lexes_a_module(self):
        response = self._worker().request(
            "import { a } from '@x/y';\nexport const b = 1;\nexport * from '@x/z';\n"
        )
        if response is None:
            self.skipTest("es-module-lexer worker unavailable (npm install?)")
        self.assertEqual([imp["n"] for imp in response["imports"]], ["@x/y"])
        self.assertEqual(response["starFrom"], ["@x/z"])
        self.assertEqual(response["reexports"], [{"n": "@x/z", "kind": "star"}])
        self.assertIn("b", response["names"])

    @unittest.skipUnless(shutil.which("node"), "node binary not available")
    def test_the_worker_types_every_re_export_form(self):
        response = self._worker().request(
            "export { a } from '@x/named';\n"
            "export { default as d } from '@x/dflt';\n"
            "export * as ns from '@x/ns';\n"
        )
        if response is None:
            self.skipTest("es-module-lexer worker unavailable (npm install?)")
        self.assertEqual(
            response["reexports"],
            [
                {"n": "@x/named", "kind": "named"},
                {"n": "@x/dflt", "kind": "default"},
                {"n": "@x/ns", "kind": "star"},
            ],
        )
        self.assertEqual(response["imports"], [], "a re-export is not an import")

    @unittest.skipUnless(shutil.which("node"), "node binary not available")
    def test_the_union_of_both_lists_is_what_discovery_uses(self):
        from odoo.tools.assets.esm_graph import _get_import_specifiers

        specs = _get_import_specifiers(
            "import { a } from '@x/y';\nexport * from '@x/z';\n"
        )
        self.assertEqual(specs, {"@x/y", "@x/z"})


class TestBridgeDiscoveryWithoutTheLexer(BaseCase):
    def _discover(self, source, native=(), ext=()):
        from odoo.tools.assets import esm_bridges

        manager = BridgeShimManager.__new__(BridgeShimManager)
        manager.bundle_name = "test.nolexer"
        manager.native_modules = [_Mod("@a/one", source)]
        with patch.object(esm_bridges, "lex_module", return_value=None):
            return manager._discover_bridge_specifiers(set(native), set(ext))

    def test_the_regex_fallback_reads_the_same_kinds(self):
        discovered, _ext = self._discover(
            'import def from "@web/core/a";\n'
            'import * as ns from "@web/core/b";\n'
            'import { named } from "@web/core/c";\n'
            'import "@web/core/d";\n'
        )
        self.assertEqual(discovered["@web/core/a"], {"__default__"})
        self.assertEqual(discovered["@web/core/b"], {"__star__"})
        self.assertEqual(discovered["@web/core/c"], set())
        self.assertEqual(discovered["@web/core/d"], set())

    def test_the_fallback_still_honours_the_ignore_sets(self):
        discovered, ext_seen = self._discover(
            'import { a } from "@web/core/a";\nimport { o } from "@odoo/owl";\n',
            native={"@web/core/a"},
            ext={"@odoo/owl"},
        )
        self.assertEqual(discovered, {})
        self.assertEqual(ext_seen, {"@odoo/owl"})

    def test_the_two_paths_agree_on_the_same_source(self):
        source = (
            'import def from "@web/core/a";\n'
            'import * as ns from "@web/core/b";\n'
            'import { named } from "@web/core/c";\n'
        )
        manager = BridgeShimManager.__new__(BridgeShimManager)
        manager.bundle_name = "test.agree"
        manager.native_modules = [_Mod("@a/one", source)]

        lexed, _ = manager._discover_bridge_specifiers(set(), set())
        regexed, _ = self._discover(source)
        if not lexed:
            self.skipTest("es-module-lexer worker unavailable")
        self.assertEqual(lexed, regexed)


class TestExportExtractionWithoutTheLexer(BaseCase):
    @staticmethod
    def _names(src, source_map=None, importer="@w/leaf"):
        from odoo.tools.assets import esm_graph

        with patch.object(esm_graph, "lex_module", return_value=None):
            return esm_graph._extract_esm_exports(
                src, source_map=source_map, importing_specifier=importer
            )

    def test_every_declaration_form_is_found(self):
        names, _ = self._names(
            "export const a = 1;\n"
            "export let b = 2;\n"
            "export var c = 3;\n"
            "export function d() {}\n"
            "export function* e() {}\n"
            "export async function f() {}\n"
            "export class g {}\n"
        )
        self.assertEqual(names, set("abcdefg"))

    def test_an_export_list_publishes_the_alias_not_the_local(self):
        names, _ = self._names("const x = 1;\nexport { x as publicName, y };\n")
        self.assertEqual(names, {"publicName", "y"})

    def test_a_re_export_list_is_read_the_same_way(self):
        names, _ = self._names('export { a, b as c } from "./other";\n')
        self.assertEqual(names, {"a", "c"})

    def test_a_destructured_export_publishes_the_bound_names(self):
        names, _ = self._names("export const { a, b: renamed, c = 3 } = obj;\n")
        self.assertEqual(
            names,
            {"a", "renamed", "c"},
            "a rename publishes the new name and a default publishes the key",
        )

    def test_a_namespace_re_export_publishes_the_namespace(self):
        names, _ = self._names('export * as ns from "./other";\n')
        self.assertIn("ns", names)

    def test_default_is_reported_separately_and_never_as_a_name(self):
        for src in (
            "export default 1;\n",
            "export default function () {}\n",
            "export default function* gen() {}\n",
            "export default async function go() {}\n",
            "export default class Thing {}\n",
        ):
            names, has_default = self._names(src)
            self.assertTrue(has_default, src)
            self.assertNotIn("default", names, src)

    def test_export_star_is_followed_through_the_source_map(self):
        names, _ = self._names(
            'export * from "./base";\nexport const C = 3;\n',
            source_map={"@w/base": "export const A = 1;\nexport const B = 2;\n"},
        )
        self.assertEqual(names, {"A", "B", "C"})

    def test_block_comments_and_template_literals_are_opaque(self):
        names, has_default = self._names(
            "/* export const commented = 1; */\n"
            "const t = `export const templated = 2;`;\n"
            "export const real = 3;\n"
        )
        self.assertEqual(names, {"real"})
        self.assertFalse(has_default)

    def test_a_quoted_string_is_NOT_opaque__documented_divergence(self):
        names, _ = self._names(
            'const s = "export const stringy = 2;";\nexport const real = 3;\n'
        )
        self.assertEqual(names, {"real", "stringy"})

    def test_the_divergence_never_costs_a_real_export(self):
        src = 'const s = "export const stringy = 2;";\nexport const real = 3;\n'
        from odoo.tools.assets import esm_graph

        lexed, _ = esm_graph._extract_esm_exports(src)
        if not lexed:
            self.skipTest("es-module-lexer worker unavailable")
        fallback, _ = self._names(src)
        self.assertLessEqual(
            lexed, fallback, "the fallback must never publish FEWER names"
        )

    def test_the_two_extractors_agree_on_an_ordinary_module(self):
        src = (
            "export const a = 1;\n"
            "export function b() {}\n"
            "export class c {}\n"
            "const local = 4;\n"
            "export { local as d };\n"
            "export default 5;\n"
        )
        from odoo.tools.assets import esm_graph

        lexed = esm_graph._extract_esm_exports(src)
        if not lexed[0]:
            self.skipTest("es-module-lexer worker unavailable")
        self.assertEqual(lexed, self._names(src))


class TestLexModuleIsMemoised(BaseCase):
    def test_the_same_source_is_lexed_once(self):
        from odoo.tools.assets import esm_lexer

        esm_lexer.clear_lex_cache()
        self.addCleanup(esm_lexer.clear_lex_cache)
        calls = []

        def _spy(src):
            calls.append(src)
            return {"imports": [], "names": [], "starFrom": [], "hasDefault": False}

        with patch.object(esm_lexer._worker, "request", _spy):
            src = "export const memo_probe = 1;\n"
            first = esm_lexer.lex_module(src)
            second = esm_lexer.lex_module(src)
            esm_lexer.lex_module("export const other_probe = 2;\n")
        self.assertEqual(len(calls), 2, "identical sources must reach the worker once")
        self.assertIs(first, second)
