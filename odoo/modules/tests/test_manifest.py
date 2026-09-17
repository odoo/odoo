import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odoo.modules.module import (
    Manifest,
    MissingDependencyError,
    _normalize_manifest,
    check_python_external_dependency,
    get_module_icon_path,
)
from odoo.release import major_version
from odoo.tools import mute_logger

import odoo.addons

BaseCase = unittest.TestCase


class _ManifestCase(BaseCase):
    def _found_manifest(self, module_name: str) -> Manifest:
        manifest = Manifest.for_addon(module_name)
        if manifest is None:
            self.fail(f"no manifest for {module_name!r}")
        return manifest


class TestModuleManifest(_ManifestCase):
    _tmp_dir: tempfile.TemporaryDirectory
    addons_path: str
    module_root: str
    module_name: str

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="odoo_test_addons_")
        cls.addClassCleanup(cls._tmp_dir.cleanup)
        cls.addons_path = cls._tmp_dir.name

        patcher = patch.object(odoo.addons, "__path__", [cls.addons_path])
        cls.enterClassContext(patcher)

    def setUp(self):
        self.module_root = tempfile.mkdtemp(
            prefix="odoo_test_module_", dir=self.addons_path
        )
        self.module_name = Path(self.module_root).name

    def test_default_manifest(self):
        Path(str(Path(self.module_root, "__manifest__.py"))).write_text(
            str(
                {
                    "name": f"Temp {self.module_name}",
                    "license": "MIT",
                    "author": "Fapi",
                }
            ),
            encoding="utf-8",
        )

        with self.assertNoLogs("odoo.modules.module", "WARNING"):
            manifest = dict(self._found_manifest(self.module_name))

        self.maxDiff = None
        self.assertDictEqual(
            manifest,
            {
                "addons_path": self.addons_path,
                "application": False,
                "assets": {},
                "author": "Fapi",
                "auto_install": False,
                "bootstrap": False,
                "category": "Uncategorized",
                "cloc_exclude": [],
                "configurator_snippets": {},
                "configurator_snippets_addons": {},
                "countries": [],
                "data": [],
                "demo": [],
                "demo_xml": [],
                "depends": ["base"],
                "description": "",
                "esm": {},
                "external_dependencies": {},
                "icon": "/base/static/description/icon.png",
                "init_xml": [],
                "installable": True,
                "iot_handlers_in_image": False,
                "images": [],
                "images_preview_theme": {},
                "license": "MIT",
                "live_test_url": "",
                "name": f"Temp {self.module_name}",
                "new_page_templates": {},
                "post_init_hook": "",
                "post_load": "",
                "pre_init_hook": "",
                "sequence": 100,
                "static_path": None,
                "summary": "",
                "test": [],
                "theme_customizations": {},
                "update_xml": [],
                "uninstall_hook": "",
                "version": f"{major_version}.1.0",
                "web": False,
                "website": "",
            },
        )

    def test_change_manifest(self):
        Path(self.module_root, "__manifest__.py").write_text(
            str({"name": "X", "license": "MIT", "author": "x"}), encoding="utf-8"
        )
        manifest = self._found_manifest(self.module_name)
        orig_auto_install = manifest["auto_install"]
        with self.assertRaisesRegex(TypeError, r"does not support item assignment"):
            manifest["auto_install"] = not orig_auto_install  # type: ignore[index]
        self.assertIs(Manifest.for_addon(self.module_name), manifest)

    def test_missing_manifest(self):
        with self.assertLogs("odoo.modules.module", "DEBUG") as capture:
            manifest = Manifest.for_addon(self.module_name)
        self.assertIs(manifest, None)
        self.assertIn("manifest not found", capture.output[0])

    def test_missing_license(self):
        Path(str(Path(self.module_root, "__manifest__.py"))).write_text(
            str({"name": f"Temp {self.module_name}"}), encoding="utf-8"
        )
        with self.assertLogs("odoo.modules.module", "WARNING") as capture:
            manifest = self._found_manifest(self.module_name)
            manifest._force_parse()
        self.assertEqual(manifest["license"], "LGPL-3")
        self.assertEqual(manifest["author"], "")
        self.assertIn("Missing `author` key", capture.output[0])
        self.assertIn("Missing `license` key", capture.output[1])

    def test_missing_name_defaults_to_technical_name(self):
        with self.assertLogs("odoo.modules.module", "WARNING") as capture:
            manifest = _normalize_manifest(
                "m", {"author": "x", "license": "MIT", "version": "1.0"}
            )
        self.assertEqual(manifest["name"], "m")
        self.assertIn("Missing `name` key", capture.output[0])


class TestManifestAutoInstall(BaseCase):
    BASE = {"author": "x", "license": "MIT"}

    def test_auto_install_string_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "forget.*brackets"):
            _normalize_manifest(
                "m", {**self.BASE, "auto_install": "sale", "depends": ["sale"]}
            )

    def test_auto_install_non_bool_non_collection_rejected(self):
        with self.assertRaisesRegex(TypeError, "must be a bool"):
            _normalize_manifest(
                "m", {**self.BASE, "auto_install": 5, "depends": ["base"]}
            )

    def test_auto_install_trigger_must_be_a_dependency(self):
        with self.assertRaisesRegex(ValueError, "must be dependencies"):
            _normalize_manifest(
                "m", {**self.BASE, "auto_install": ["sale"], "depends": ["base"]}
            )

    def test_auto_install_true_expands_to_all_depends(self):
        manifest = _normalize_manifest(
            "m", {**self.BASE, "auto_install": True, "depends": ["base", "sale"]}
        )
        self.assertEqual(manifest["auto_install"], {"base", "sale"})

    def test_auto_install_list_subset_of_depends_is_kept(self):
        manifest = _normalize_manifest(
            "m", {**self.BASE, "auto_install": ["base"], "depends": ["base", "sale"]}
        )
        self.assertEqual(manifest["auto_install"], {"base"})

    def test_base_depends_forced_empty(self):
        self.assertEqual(_normalize_manifest("base", dict(self.BASE))["depends"], [])

    def test_non_base_empty_depends_forced_to_base(self):
        self.assertEqual(_normalize_manifest("m", dict(self.BASE))["depends"], ["base"])


class TestManifestCache(_ManifestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="odoo_test_cache_")
        self.addCleanup(self._tmp.cleanup)
        p = patch.object(odoo.addons, "__path__", [self._tmp.name])
        p.start()
        self.addCleanup(p.stop)
        saved = dict(Manifest._parse_cache)
        saved_resolution = dict(Manifest._resolution_cache)
        Manifest.clear_caches()

        def _restore():
            Manifest._parse_cache.clear()
            Manifest._parse_cache.update(saved)
            Manifest._resolution_cache.clear()
            Manifest._resolution_cache.update(saved_resolution)

        self.addCleanup(_restore)

    def _make(self, name, **extra):
        d = Path(self._tmp.name, name)
        d.mkdir(exist_ok=True)
        self._write(name, {"name": "X", "license": "LGPL-3", "author": "x", **extra})
        return name

    def _write(self, name, content):
        path = Path(self._tmp.name, name, "__manifest__.py")
        path.write_text(str(content), encoding="utf-8")
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    def test_miss_is_not_cached_so_a_later_module_is_found(self):
        name = "probe_appears_later"
        self.assertIsNone(Manifest.for_addon(name, display_warning=False))
        self._make(name)
        found = self._found_manifest(name)
        self.assertEqual(found.name, name)

    def test_found_manifest_is_cached(self):
        name = self._make("probe_cached")
        first = Manifest.for_addon(name)
        self.assertIs(Manifest.for_addon(name), first)

    def test_a_manifest_edited_on_disk_is_seen_by_the_next_lookup(self):
        name = self._make("probe_edited", version="1.0")
        self.assertEqual(self._found_manifest(name)["version"], f"{major_version}.1.0")
        self._write(
            name,
            {"name": "X", "license": "LGPL-3", "author": "x", "version": "9.9"},
        )
        self.assertEqual(self._found_manifest(name)["version"], f"{major_version}.9.9")

    def test_a_manifest_edited_on_disk_is_seen_by_the_full_scan(self):
        name = self._make("probe_scanned", version="1.0")
        found = {m.name: m for m in Manifest.get_all_addon_manifests()}
        self.assertEqual(found[name]["version"], f"{major_version}.1.0")
        self._write(
            name,
            {"name": "X", "license": "LGPL-3", "author": "x", "version": "9.9"},
        )
        found = {m.name: m for m in Manifest.get_all_addon_manifests()}
        self.assertEqual(found[name]["version"], f"{major_version}.9.9")

    def test_a_manifest_removed_from_disk_stops_resolving(self):
        name = self._make("probe_removed")
        self.assertIsNotNone(Manifest.for_addon(name))
        Path(self._tmp.name, name, "__manifest__.py").unlink()
        self.assertIsNone(Manifest.for_addon(name, display_warning=False))

    def test_an_unchanged_manifest_is_not_reparsed(self):
        name = self._make("probe_stable")
        first = Manifest.for_addon(name)
        with patch.object(
            Manifest, "_parse_from_path", side_effect=AssertionError("reparsed")
        ):
            self.assertIs(Manifest.for_addon(name), first)
            self.assertIs(
                next(m for m in Manifest.get_all_addon_manifests() if m.name == name),
                first,
            )

    def test_clear_caches_drops_found_entries(self):
        name = self._make("probe_clear")
        first = Manifest.for_addon(name)
        Manifest.clear_caches()
        again = Manifest.for_addon(name)
        self.assertIsNotNone(again)
        self.assertIsNot(again, first)


class TestExternalDependency(BaseCase):
    @mute_logger("odoo.modules.module")
    def test_specced_importable_module_name_is_accepted(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        Path(tmp, "odoo_probe_legacy_dep.py").write_text("#\n", encoding="utf-8")
        sys.path.insert(0, tmp)
        self.addCleanup(lambda: sys.path.remove(tmp) if tmp in sys.path else None)
        importlib.invalidate_caches()
        check_python_external_dependency("odoo_probe_legacy_dep>=1.0")

    def test_genuinely_missing_dependency_raises(self):
        with self.assertRaises(MissingDependencyError):
            check_python_external_dependency("odoo_definitely_absent_pkg_zzz>=1.0")

    def test_error_renders_message_and_keeps_dependency(self):
        err = MissingDependencyError("Unable to find 'foo>=1' in path", "foo>=1")
        self.assertEqual(str(err), "Unable to find 'foo>=1' in path")
        self.assertEqual(err.dependency, "foo>=1")
        self.assertNotIn("{dependency", str(err))


class TestManifestVersionResilience(_ManifestCase):
    BASE = {"author": "x", "license": "MIT", "name": "X"}

    def test_malformed_version_demotes_to_uninstallable(self):
        with self.assertLogs("odoo.modules.module", "WARNING") as capture:
            manifest = _normalize_manifest("m", {**self.BASE, "version": "1.0-beta"})
        self.assertFalse(manifest["installable"])
        self.assertIn("invalid version", capture.output[0])

    def test_malformed_version_on_uninstallable_module_is_tolerated(self):
        manifest = _normalize_manifest(
            "m", {**self.BASE, "version": "1.0-beta", "installable": False}
        )
        self.assertFalse(manifest["installable"])

    def test_non_string_version_is_normalised_to_str(self):
        with self.assertLogs("odoo.modules.module", "WARNING"):
            manifest = _normalize_manifest("m", {**self.BASE, "version": 19})
        self.assertFalse(manifest["installable"])
        self.assertIsInstance(manifest["version"], str)

    def test_non_string_version_on_uninstallable_module_is_normalised_to_str(self):
        manifest = _normalize_manifest(
            "m", {**self.BASE, "version": 19, "installable": False}
        )
        self.assertFalse(manifest["installable"])
        self.assertIsInstance(manifest["version"], str)

    def test_string_depends_rejected(self):
        with self.assertRaisesRegex(TypeError, "forget.*brackets"):
            _normalize_manifest("m", {**self.BASE, "depends": "base"})


class TestModuleIcon(_ManifestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="odoo_test_icon_")
        self.addCleanup(self._tmp.cleanup)
        p = patch.object(odoo.addons, "__path__", [self._tmp.name])
        p.start()
        self.addCleanup(p.stop)
        saved = dict(Manifest._parse_cache)
        saved_resolution = dict(Manifest._resolution_cache)
        Manifest.clear_caches()

        def _restore():
            Manifest._parse_cache.clear()
            Manifest._parse_cache.update(saved)
            Manifest._resolution_cache.clear()
            Manifest._resolution_cache.update(saved_resolution)

        self.addCleanup(_restore)

    def _make(self, name, **extra):
        d = Path(self._tmp.name, name)
        d.mkdir()
        (d / "__manifest__.py").write_text(
            str({"name": "X", "license": "LGPL-3", "author": "x", **extra})
        )
        return name

    def test_missing_icon_falls_back_to_base_default(self):
        name = self._make("probe_icon")
        self.assertEqual(
            get_module_icon_path(name), "/base/static/description/icon.png"
        )

    def test_icon_for_unknown_module_is_base_default(self):
        self.assertEqual(
            get_module_icon_path("no_such_module_xyz"),
            "/base/static/description/icon.png",
        )

    def test_the_manifest_resolves_its_own_icon_without_looking_itself_up(self):
        name = self._make("probe_no_self_lookup")
        manifest = self._found_manifest(name)
        with patch.object(
            Manifest, "for_addon", side_effect=AssertionError("looked itself up")
        ):
            self.assertEqual(manifest["icon"], "/base/static/description/icon.png")

    def test_a_declared_icon_agrees_between_both_entry_points(self):
        name = self._make(
            "probe_declared_icon", icon="/base/static/description/icon.png"
        )
        self.assertEqual(
            self._found_manifest(name)["icon"], "/base/static/description/icon.png"
        )
        self.assertEqual(get_module_icon_path(name), self._found_manifest(name)["icon"])


class TestManifestMapping(BaseCase):
    def _manifest(self):
        return Manifest(
            path="/tmp/odoo_probe_map",
            manifest_content={"name": "P", "license": "LGPL-3", "author": "x"},
        )

    def test_computed_keys_present_in_iter(self):
        keys = set(self._manifest())
        for key in Manifest._COMPUTED_KEYS:
            self.assertIn(key, keys)

    def test_len_matches_iteration(self):
        manifest = self._manifest()
        self.assertEqual(len(manifest), len(list(iter(manifest))))

    def test_computed_keys_reachable_via_getitem(self):
        manifest = self._manifest()
        for key in Manifest._COMPUTED_KEYS:
            manifest[key]
