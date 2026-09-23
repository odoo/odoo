import sys
import unittest
from unittest import mock

from rjsmin import jsmin

from odoo.tools.assets import esm_bridges, esm_graph
from odoo.tools.assets.js_scan import rjsmin_misreads, scrub

from odoo.addons.base.models.assetsbundle import assets
from odoo.addons.base.models.assetsbundle.assets import JavascriptAsset


class TestNestedTemplateLiteral(unittest.TestCase):
    CORRUPTED_BY_RJSMIN = (
        ("// a lone ` in a comment\nvar r = `x ${ `in  ner` } y`;", "in  ner"),
        ('const c = "a ` b";\nconst a = `${`n  o`}`;', "n  o"),
        ('var r = `a ${ "}" + `in  ner` } b`;', "in  ner"),
        ("var r = `a ${ /`/.source }  b`;", "}  b"),
        ("var r = `a ${ '`' }  b`;", "}  b"),
    )

    def test_a_backtick_outside_a_substitution_does_not_hide_nesting(self):
        for source, intact in self.CORRUPTED_BY_RJSMIN:
            with self.subTest(source=source):
                self.assertNotIn(intact, jsmin(source, keep_bang_comments=True))
                self.assertTrue(rjsmin_misreads(source))

    def test_what_rjsmin_keeps_is_not_flagged(self):
        for source in (
            "const a = `x ${y}  z`;",
            'const a = `x ${ obj["k}"] }  y`;',
            "const a = `${ 1/2 } // not  a comment`;",
            "const a = `esc \\` still  one ${x}`;",
            "const r = /`/; const t = `${x}  y`;",
            "const d = a / b / c; const t = `${x}  y`;",
            "// a lone ` here\nconst t = `${x}  y`;",
            "const c = 'a ` b';\nconst t = `${x}  y`;",
        ):
            with self.subTest(source=source):
                self.assertFalse(rjsmin_misreads(source))
                self.assertIn("  ", jsmin(source, keep_bang_comments=True))

    def test_an_unterminated_literal_is_left_to_esbuild(self):
        self.assertTrue(rjsmin_misreads("const a = `x ${y}"))

    def test_nesting_deeper_than_the_recursion_limit_is_still_scanned(self):
        depth = sys.getrecursionlimit()
        source = "const a = " + "`${" * depth + "1" + "}`" * depth + ";\nconst b = 2;"
        self.assertTrue(rjsmin_misreads(source))
        self.assertEqual(scrub(source), 'const a = "";\nconst b = 2;')

    def test_the_minifier_hands_deep_nesting_to_esbuild(self):
        depth = sys.getrecursionlimit()
        source = "const a = " + "`${" * depth + "1" + "}`" * depth + ";"
        asset = JavascriptAsset.__new__(JavascriptAsset)
        asset.url = "/probe/deep.js"
        with (
            mock.patch.object(JavascriptAsset, "content", source),
            mock.patch.object(JavascriptAsset, "name", "deep.js"),
            mock.patch.object(JavascriptAsset, "with_header", lambda _self, c: c),
            mock.patch.object(assets, "minify_js", return_value="min") as esbuild,
        ):
            self.assertEqual(asset.minify(), "min")
        esbuild.assert_called_once()


class TestScrub(unittest.TestCase):
    def test_only_a_specifier_keeps_its_text(self):
        self.assertEqual(
            scrub(
                'import a from "@x/a";\nimport \'@x/b\';\nexport * from "./c";\n'
                "const s = \"import d from '@x/evil'\";\n"
            ),
            'import a from "@x/a";\nimport \'@x/b\';\nexport * from "./c";\n'
            'const s = "";\n',
        )

    def test_comments_templates_and_regexes_are_opaque(self):
        self.assertEqual(
            scrub("// the ` char\nconst t = `a\n${b}`;\nconst r = /[\"'`]/g;\n"),
            ' \nconst t = "";\nconst r = /r/;\n',
        )

    def test_a_block_comment_keeps_its_lines(self):
        self.assertEqual(scrub("/* a\nb */export {};"), "\nexport {};")


class TestRegexFallbackMatchesTheLexer(unittest.TestCase):
    def setUp(self):
        for module in (esm_graph, esm_bridges):
            patcher = mock.patch.object(module, "lex_module", return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_a_backtick_in_a_line_comment_hides_nothing(self):
        src = '// the ` character\nexport const a = 1;\nimport x from "@web/x";\n'
        src += "const t = `y`;\n"
        self.assertEqual(esm_graph._extract_esm_exports(src), ({"a"}, False))
        self.assertEqual(esm_graph._get_import_specifiers(src), {"@web/x"})
        self.assertEqual(esm_bridges._static_edges(src), [("@web/x", "__default__")])

    def test_an_import_inside_a_string_is_not_an_edge(self):
        src = "const s = \"import x from '@web/evil'\";\nexport const ok = 1;\n"
        self.assertEqual(esm_graph._get_import_specifiers(src), set())
        self.assertEqual(esm_bridges._static_edges(src), [])

    def test_an_array_destructuring_export_names_its_bindings(self):
        self.assertEqual(
            esm_graph._extract_esm_exports(
                "export const [first, , ...rest] = pair;\n"
                "export const { a, b: c, ...d } = obj;\n"
            ),
            ({"first", "rest", "a", "c", "d"}, False),
        )

    def test_a_list_export_as_default_is_a_default(self):
        self.assertEqual(
            esm_graph._extract_esm_exports("const a = 1;\nexport { a as default };\n"),
            (set(), True),
        )
        self.assertEqual(
            esm_graph._extract_esm_exports('export { default, b } from "./x";\n'),
            ({"b"}, True),
        )

    def test_module_syntax_in_a_template_is_not_module_syntax(self):
        src = '// the ` character\nconst t = `\nimport x from "y"\n`;\n'
        self.assertFalse(esm_graph.has_module_syntax(src))
        self.assertTrue(esm_graph.has_module_syntax("/* a */\nexport {};\n"))


if __name__ == "__main__":
    unittest.main()
