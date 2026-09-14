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
