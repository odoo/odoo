import unittest
from types import SimpleNamespace
from unittest import mock

from odoo.tools.assets import esm_bridges, esm_graph, esm_registry
from odoo.tools.assets.esm_graph import _extract_esm_exports, _resolve_export_specifier


def _module(spec, url, src):
    return SimpleNamespace(module_path=spec, url=url, raw_content=src)


class TestAStarCycleCachesOnlyWholeAnswers(unittest.TestCase):
    SOURCES = {
        "@x/a": 'export const a = 1;\nexport * from "./b";\n',
        "@x/b": 'export const b = 1;\nexport * from "./a";\n',
        "@x/c": 'export * from "./a";\n',
    }

    def _names(self, spec, cache):
        names, _ = _extract_esm_exports(
            self.SOURCES[spec],
            source_map=self.SOURCES,
            importing_specifier=spec,
            _exports_cache=cache,
        )
        return names

    def test_a_module_walked_after_the_cycle_sees_every_name(self):
        cache = {}
        for spec in ("@x/a", "@x/b"):
            self.assertEqual(self._names(spec, cache), {"a", "b"})
        self.assertEqual(self._names("@x/c", cache), {"a", "b"})

    def test_a_cached_entry_is_never_a_partial_one(self):
        cache = {}
        for spec in ("@x/a", "@x/b", "@x/c"):
            self._names(spec, cache)
        for spec, names in cache.items():
            with self.subTest(spec=spec):
                self.assertEqual(names, self._names(spec, {}))


class TestTheParentSelfBridgeResolvesAnIndexBesideItsFile(unittest.TestCase):
    MODULES = (
        _module("@x/top", "/x/static/src/top.js", 'export * from "./geometry";\n'),
        _module(
            "@x/geometry",
            "/x/static/src/geometry/index.js",
            'export * from "./nodes.js";\n',
        ),
        _module(
            "@x/geometry/nodes",
            "/x/static/src/geometry/nodes.js",
            "export const node = 1;\n",
        ),
    )

    def test_a_star_through_an_index_reaches_its_siblings(self):
        manager = esm_bridges.BridgeShimManager(None, "x.bundle", self.MODULES)
        with (
            mock.patch.object(
                manager, "_persist_bridge_shims", side_effect=lambda shims: shims
            ),
            mock.patch.object(
                esm_bridges,
                "esm_registry",
                return_value=SimpleNamespace(import_map_includes=()),
            ),
        ):
            shims = manager._prepare_parent_self_bridge()
        self.assertIn("_m.node;", shims["@x/top"])
        self.assertIn("_m.node;", shims["@x/geometry"])


class TestOneRelativeResolver(unittest.TestCase):
    def test_parent_segments_are_normalised_without_a_url(self):
        self.assertEqual(_resolve_export_specifier("@x/a/b", "./c/../d.js"), "@x/a/d")

    def test_an_index_file_is_its_directory(self):
        self.assertEqual(_resolve_export_specifier("@x/a/b", "./index.js"), "@x/a")
        self.assertEqual(
            _resolve_export_specifier("@x/a/b", "./c/index.js", "/x/static/src/a/b.js"),
            "@x/a/c",
        )

    def test_a_path_climbing_out_stays_in_the_addon_to_be_reported(self):
        self.assertEqual(_resolve_export_specifier("@x/a", "../../y.js"), "@x/y")
        self.assertEqual(
            _resolve_export_specifier("@x/dir/a", "../../service.js"), "@x/service"
        )
        self.assertIsNone(_resolve_export_specifier("x/a", "./y.js"))

    def test_the_lexed_edges_use_the_same_resolver(self):
        with mock.patch.object(esm_bridges, "lex_module", return_value=None):
            edges = esm_bridges._lexed_imports(
                'import "./c/../d.js";\nimport "./index.js";\n', base_spec="@x/a/b"
            )
        self.assertEqual([spec for spec, _kind in edges], ["@x/a/d", "@x/a"])


class TestInvalidatingTheRegistryForgetsWhichFilesExist(unittest.TestCase):
    def test_a_rename_to_an_index_is_seen_after_invalidation(self):
        on_disk = {"x/static/src/foo.js"}

        def file_path(rel):
            if rel not in on_disk:
                raise FileNotFoundError(rel)
            return rel

        esm_graph._static_file_exists.cache_clear()
        self.addCleanup(esm_graph._static_file_exists.cache_clear)
        with (
            mock.patch.object(esm_graph, "file_path", file_path),
            mock.patch.object(esm_registry, "_cache", [None]),
        ):
            self.assertEqual(
                esm_graph.resolve_specifier_url("@x/foo", {}), "/x/static/src/foo.js"
            )
            on_disk.clear()
            on_disk.add("x/static/src/foo/index.js")
            esm_registry.invalidate_esm_registry()
            self.assertEqual(
                esm_graph.resolve_specifier_url("@x/foo", {}),
                "/x/static/src/foo/index.js",
            )


class TestPageProvidedBridgesReadEachSourceOnce(unittest.TestCase):
    SOURCES = {
        "x/static/src/helper.js": "export const help = 1;\n",
        "x/static/src/face.js": 'export * from "@x/helper";\n',
    }

    def test_a_helper_both_the_walk_and_the_surface_reach_is_read_once(self):
        reads = []

        def file_path(rel):
            if rel not in self.SOURCES:
                raise FileNotFoundError(rel)
            reads.append(rel)
            return rel

        consumer = _module(
            "@y/page",
            "/y/static/src/page.js",
            'import "@x/helper";\nimport { help } from "@x/face";\n',
        )
        manager = esm_bridges.BridgeShimManager(None, "y.bundle", [consumer])
        with (
            mock.patch.object(esm_graph, "file_path", file_path),
            mock.patch.object(esm_graph, "_static_file_exists", return_value=True),
            mock.patch.object(
                esm_graph.Path, "read_text", lambda path, **_kw: self.SOURCES[str(path)]
            ),
            mock.patch.object(esm_bridges, "external_libs", return_value={}),
            mock.patch.object(
                manager, "_persist_bridge_shims", side_effect=lambda shims: shims
            ),
        ):
            bridges, per_file = manager.prepare_page_provided_bridges(
                {"@y/page"}, frozenset({"@x/face"})
            )
        self.assertIn("_m.help;", bridges["@x/face"])
        self.assertEqual(per_file, {"@x/helper"})
        self.assertEqual(reads.count("x/static/src/helper.js"), 1)


if __name__ == "__main__":
    unittest.main()
