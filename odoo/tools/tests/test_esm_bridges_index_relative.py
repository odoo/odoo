import unittest

from odoo.tools.assets.esm_bridges import _lexed_imports, _relative_to_specifier

INDEX_SPEC = "@point_of_sale/app/models/related_models"
INDEX_URL = "/point_of_sale/static/src/app/models/related_models/index.js"
INDEX_SOURCE = """
import { Base } from "./base.js";
import { uuidv4 } from "@point_of_sale/utils";
import { helper } from "../utils/helper.js";
"""


class TestIndexModuleRelativeImports(unittest.TestCase):
    def test_a_sibling_of_an_index_module_lives_under_the_index_directory(self):
        self.assertEqual(
            _relative_to_specifier(INDEX_SPEC, "./base.js", INDEX_URL),
            "@point_of_sale/app/models/related_models/base",
        )

    def test_without_the_url_the_specifier_alone_is_a_wrong_guess(self):
        # the fallback that stays for a spec whose source cannot be read
        self.assertEqual(
            _relative_to_specifier(INDEX_SPEC, "./base.js"),
            "@point_of_sale/app/models/base",
        )

    def test_a_plain_module_resolves_the_same_either_way(self):
        spec, url = "@web/core/utils/misc", "/web/static/src/core/utils/misc.js"
        self.assertEqual(
            _relative_to_specifier(spec, "../browser/browser.js", url),
            _relative_to_specifier(spec, "../browser/browser.js"),
        )

    def test_the_lexed_imports_of_an_index_module_are_its_real_siblings(self):
        specs = {
            s
            for s, _kind in _lexed_imports(
                INDEX_SOURCE, base_spec=INDEX_SPEC, base_url=INDEX_URL
            )
        }
        self.assertEqual(
            specs,
            {
                "@point_of_sale/app/models/related_models/base",
                "@point_of_sale/utils",
                "@point_of_sale/app/models/utils/helper",
            },
        )


if __name__ == "__main__":
    unittest.main()


class TestSpecifierUrlIndexFallback(unittest.TestCase):
    def _resolve(self, spec, exists):
        from unittest.mock import patch

        from odoo.tools.assets import esm_graph

        with patch.object(esm_graph, "_static_file_exists", side_effect=exists):
            return esm_graph.resolve_specifier_url(spec, {})

    def test_a_directory_index_specifier_resolves_to_index_js(self):
        # `foo.js` does not exist but `foo/index.js` does: the import map must
        # point at the served file, not a 404 that poisons the whole bundle
        url = self._resolve(INDEX_SPEC, lambda u: u.endswith("/index.js"))
        self.assertEqual(url, INDEX_URL)

    def test_a_plain_module_keeps_its_js_url_without_a_second_stat(self):
        url = self._resolve("@web/core/registry", lambda u: u.endswith(".js"))
        self.assertEqual(url, "/web/static/src/core/registry.js")

    def test_neither_shape_present_keeps_the_js_guess(self):
        url = self._resolve("@web/does/not/exist", lambda u: False)
        self.assertEqual(url, "/web/static/src/does/not/exist.js")

    def test_an_external_lib_specifier_is_untouched(self):
        from odoo.tools.assets import esm_graph

        self.assertEqual(
            esm_graph.resolve_specifier_url(
                "@lib/x", {"@lib/x": "/web/static/lib/x.js"}
            ),
            "/web/static/lib/x.js",
        )


class TestStaticEdgesRegexFallbackParity(unittest.TestCase):
    # With the es-module-lexer worker unavailable (no node, non-posix, or
    # disabled after repeated failures) the regex extractors are the only
    # path. They must see every edge the lexer sees, or the transitive reach
    # walk misses page modules reached through relative imports and esbuild
    # inlines them a second time.
    SRC = (
        'import { helper } from "./sibling";\n'
        'import util from "../util/thing";\n'
        'import "./side_effect";\n'
        'export { reexported } from "./reexp";\n'
        'export { default as Renamed } from "./def";\n'
        'export * from "./everything";\n'
        'export * as ns from "./nsmod";\n'
        'import { widget } from "@web/core/widget";\n'
        'import "@mail/side/patch";\n'
    )
    EXPECTED = {
        ("@web/core/sibling", None),
        ("@web/util/thing", "__default__"),
        ("@web/core/side_effect", None),
        ("@web/core/reexp", None),
        ("@web/core/def", "__default__"),
        ("@web/core/everything", "__star__"),
        ("@web/core/nsmod", "__star__"),
        ("@web/core/widget", None),
        ("@mail/side/patch", None),
    }

    def _lexed_without_worker(self):
        from unittest.mock import patch

        from odoo.tools.assets import esm_bridges, esm_graph

        with (
            patch.object(esm_bridges, "lex_module", return_value=None),
            patch.object(esm_graph, "lex_module", return_value=None),
        ):
            return set(
                _lexed_imports(
                    self.SRC,
                    base_spec="@web/core/foo",
                    base_url="/web/static/src/core/foo.js",
                )
            )

    def test_relative_and_reexport_edges_survive_the_regex_fallback(self):
        self.assertEqual(self._lexed_without_worker(), self.EXPECTED)

    def test_a_named_reexport_is_not_a_star_reexport(self):
        edges = self._lexed_without_worker()
        self.assertIn(("@web/core/reexp", None), edges)
        self.assertNotIn(("@web/core/reexp", "__star__"), edges)


class TestRegexFallbackCommentsAndBounds(unittest.TestCase):
    # More ways the regex fallback used to disagree with the lexer, all fixed
    # so a no-node host resolves the same graph a node host does.
    def _patched(self):
        from unittest.mock import patch

        from odoo.tools.assets import esm_bridges, esm_graph

        return (
            patch.object(esm_bridges, "lex_module", return_value=None),
            patch.object(esm_graph, "lex_module", return_value=None),
        )

    def test_a_jsdoc_import_is_not_a_runtime_import(self):
        from odoo.tools.assets import esm_bridges, esm_graph

        src = (
            '/** @import { DynamicList }'
            ' from "@web/model/relational_model/dynamic_list" */\n'
            'import { real } from "@web/core/registry";\n'
        )
        p1, p2 = self._patched()
        with p1, p2:
            specs = esm_graph._get_import_specifiers(src)
            edges = {s for s, _ in esm_bridges._static_edges(src)}
        self.assertEqual(specs, {"@web/core/registry"})
        self.assertEqual(edges, {"@web/core/registry"})

    def test_a_large_named_import_is_not_truncated_away(self):
        from odoo.tools.assets import esm_graph

        names = ",\n    ".join(f"exportedHelper{i}" for i in range(60))
        src = f"import {{\n    {names},\n}} from '@web/core/utils/big';\n"
        self.assertGreater(len(src), 400)
        p1, p2 = self._patched()
        with p1, p2:
            specs = esm_graph._get_import_specifiers(src)
        self.assertIn("@web/core/utils/big", specs)

    def test_a_default_plus_named_import_is_a_default_edge(self):
        from odoo.tools.assets import esm_bridges

        src = 'import lazyloader, { waitLazy } from "@web/public/lazyloader";\n'
        p1, p2 = self._patched()
        with p1, p2:
            edges = dict(esm_bridges._static_edges(src))
        self.assertEqual(edges.get("@web/public/lazyloader"), "__default__")
