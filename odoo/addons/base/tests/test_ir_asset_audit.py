import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from psycopg.errors import NotNullViolation

from odoo import tools
from odoo.exceptions import ValidationError
from odoo.modules import Manifest
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.base.models.ir_asset import Resolution
from odoo.addons.base.models.ir_asset_paths import _get_static_files


@tagged("post_install", "-at_install")
class TestGetPathsEscapeWarning(TransactionCase):
    def test_escape_outside_static_warns(self):
        IrAsset = self.env["ir.asset"]
        installed = Resolution(active=IrAsset._get_addons_installed())
        escaping = "/base/static/../../../../etc/passwd"
        with self.assertLogs("odoo.addons.base.models", level="WARNING") as cm:
            result = IrAsset._resolve_paths(escaping, installed)
        joined = "\n".join(cm.output)
        self.assertIn("resolves outside the static/", joined)
        self.assertEqual(result, ((escaping, None, None),))

    def test_missing_literal_inside_static_warns_typo(self):
        IrAsset = self.env["ir.asset"]
        installed = Resolution(active=IrAsset._get_addons_installed())
        inside = "/base/static/src/scss/__does_not_exist__.scss"
        with self.assertLogs("odoo.addons.base.models", level="WARNING") as cm:
            result = IrAsset._resolve_paths(inside, installed)
        joined = "\n".join(cm.output)
        self.assertIn("matches no bundleable file in the static/", joined)
        self.assertNotIn("resolves outside the static/", joined)
        self.assertEqual(result, ((inside, None, None),))

    def test_existing_literal_inside_static_does_not_warn(self):
        IrAsset = self.env["ir.asset"]
        installed = Resolution(active=IrAsset._get_addons_installed())
        inside = "/base/static/src/scss/res_users.scss"
        with self.assertNoLogs("odoo.addons.base.models", level="WARNING"):
            result = IrAsset._resolve_paths(inside, installed)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], inside)
        self.assertIsNotNone(result[0][1])


@tagged("post_install", "-at_install")
class TestAttachmentBackedPath(TransactionCase):
    URL = "/base/static/src/scss/__served_by_an_attachment__.scss"

    def _resolve(self, path_def):
        IrAsset = self.env["ir.asset"]
        resolution = Resolution(active=IrAsset._get_addons_installed())
        return IrAsset._resolve_paths(path_def, resolution)

    def _attach(self, url):
        return self.env["ir.attachment"].create(
            {"name": "probe", "type": "binary", "url": url, "raw": b""}
        )

    def test_a_matching_attachment_silences_the_warning(self):
        self._attach(self.URL)
        with self.assertNoLogs("odoo.addons.base.models", level="WARNING"):
            resolved = self._resolve(self.URL)
        self.assertEqual(resolved[0].path, self.URL)

    def test_both_spellings_keep_working_when_each_backs_itself(self):
        unslashed = self.URL.lstrip("/")
        self._attach(unslashed)
        with self.assertNoLogs("odoo.addons.base.models", level="WARNING"):
            resolved = self._resolve(unslashed)
        self.assertEqual(resolved[0].path, unslashed)
        self.assertTrue(
            self.env["ir.attachment"].sudo()._get_serve_attachment(resolved[0].path)
        )

    def test_the_other_spelling_is_reported_instead_of_certified(self):
        self._attach(self.URL)
        with self.assertLogs("odoo.addons.base.models", level="WARNING") as cm:
            resolved = self._resolve(self.URL.lstrip("/"))
        joined = "\n".join(cm.output)
        self.assertIn("registered as", joined)
        self.assertIn(self.URL, joined)
        self.assertNotIn("typo in the path", joined)
        self.assertFalse(
            self.env["ir.attachment"].sudo()._get_serve_attachment(resolved[0].path),
            "the warning must fire exactly when the bundle lookup will miss",
        )

    def test_no_attachment_at_all_still_reads_as_a_typo(self):
        with self.assertLogs("odoo.addons.base.models", level="WARNING") as cm:
            self._resolve(self.URL)
        self.assertIn("typo in the path", "\n".join(cm.output))

    def test_a_path_outside_every_addon_is_diagnosed_too(self):
        custom = "/_custom/web.assets_frontend/web/static/src/scss/probe.scss"
        with self.assertLogs("odoo.addons.base.models", level="WARNING") as cm:
            resolved = self._resolve(custom)
        self.assertEqual(resolved[0].path, custom)
        self.assertIn("no attachment claims that URL", "\n".join(cm.output))

        self.env["ir.attachment"].create(
            {"name": "custom", "type": "binary", "url": custom, "raw": b""}
        )
        with self.assertNoLogs("odoo.addons.base.models", level="WARNING"):
            self._resolve(custom)


@tagged("post_install", "-at_install")
class TestResolvedPathsAreShared(TransactionCase):
    BUNDLE = "web.assets_backend"

    def test_a_second_resolution_reuses_the_first_strings(self):
        IrAsset = self.env["ir.asset"]
        first = IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})
        second = IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})
        self.assertTrue(first, "the probe bundle must resolve to something")
        pairs = list(zip(first, second, strict=True))
        self.assertTrue(all(a.path is b.path for a, b in pairs))
        self.assertTrue(
            all(
                a.full_path is b.full_path
                for a, b in pairs
                if isinstance(a.full_path, str)
            )
        )

    def test_a_pattern_is_globbed_once_per_process_across_bundles(self):
        from odoo.addons.base.models import ir_asset as ir_asset_module

        IrAsset = self.env["ir.asset"]
        if not ir_asset_module._CACHE_ASSET_LOOKUPS:
            self.skipTest("dev_mode=xml disables the asset lookup caches")
        self.registry.clear_cache("assets")
        calls = []
        real = ir_asset_module._get_static_files

        def counting(pattern, static_dir, symlink_memo=None):
            calls.append(pattern)
            return real(pattern, static_dir, symlink_memo)

        with patch.object(ir_asset_module, "_get_static_files", counting):
            IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})
            first = len(calls)
            IrAsset._get_asset_paths.__wrapped__(IrAsset, "web.assets_common", {})
            IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})
        self.assertTrue(first, "the probe bundle must glob something")
        self.assertEqual(
            len(set(calls)),
            len(calls),
            "a pattern globbed once must be served from the assets cache after",
        )

    def test_the_two_resolutions_are_still_distinct_objects(self):
        IrAsset = self.env["ir.asset"]
        first = IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})
        second = IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})
        self.assertIsNot(first, second)
        self.assertEqual(first, second)


@tagged("post_install", "-at_install")
class TestProcessCommandMalformed(TransactionCase):
    def test_int_command_raises_valueerror_naming_command(self):
        with self.assertRaises(ValueError) as cm:
            self.env["ir.asset"]._parse_manifest_command(123)
        self.assertIn("123", str(cm.exception))

    def test_dict_command_raises_valueerror_naming_command(self):
        with self.assertRaises(ValueError) as cm:
            self.env["ir.asset"]._parse_manifest_command({"path": "x"})
        self.assertIn("path", str(cm.exception))

    def test_wrong_arity_raises_valueerror_naming_command(self):
        with self.assertRaises(ValueError) as cm:
            self.env["ir.asset"]._parse_manifest_command(["after", "only_two"])
        self.assertIn("only_two", str(cm.exception))

    def test_a_non_string_member_is_rejected_here_not_two_frames_down(self):
        IrAsset = self.env["ir.asset"]
        for command in (["append", 123], ["append", ["a", "b"]], ["after", 7, "/x.js"]):
            with self.subTest(command=command), self.assertRaises(ValueError) as cm:
                IrAsset._parse_manifest_command(command)
            self.assertIn("non-string", str(cm.exception))

    def test_a_non_string_path_is_attributed_to_its_addon(self):
        IrAsset = self.env["ir.asset"]
        with patch.object(
            type(IrAsset),
            "_get_manifest_assets",
            lambda _s, addons: {"probe.bundle": (("culprit", ["append", 123]),)},
        ):
            with self.assertRaises(ValueError) as cm:
                IrAsset._get_asset_paths.__wrapped__(IrAsset, "probe.bundle", {})
        message = str(cm.exception)
        self.assertIn("culprit", message)
        self.assertIn("probe.bundle", message)


@tagged("post_install", "-at_install")
class TestTopologicalSort(TransactionCase):
    def _sort(self, manifests, addons):
        IrAsset = self.env["ir.asset"]
        IrAsset.env.registry.clear_cache()
        with patch.object(
            Manifest, "for_addon", lambda name, **kw: manifests.get(name)
        ):
            return IrAsset._get_addons_sorted_topologically(tuple(addons))

    def test_dependency_precedes_dependents(self):
        manifests = {
            "base": {"depends": []},
            "app_mod": {"depends": ["base"], "application": True},
            "mid_mod": {"depends": ["app_mod"]},
            "leaf_mod": {"depends": ["mid_mod", "base"]},
        }
        order = self._sort(manifests, manifests)
        self.assertEqual(set(order), set(manifests), "all inputs returned")
        pos = {name: order.index(name) for name in manifests}
        self.assertLess(pos["base"], pos["app_mod"])
        self.assertLess(pos["app_mod"], pos["mid_mod"])
        self.assertLess(pos["mid_mod"], pos["leaf_mod"])
        self.assertLess(pos["base"], pos["leaf_mod"])

    def test_missing_depends_falls_back_to_base(self):
        manifests = {"base": {"depends": []}, "orphan": {}}
        order = self._sort(manifests, ["orphan", "base"])
        self.assertLess(order.index("base"), order.index("orphan"))


@tagged("post_install", "-at_install")
class TestAssetPathsCacheCanonical(TransactionCase):
    def test_addons_are_sorted_into_manifest_index_key(self):
        IrAsset = self.env["ir.asset"]
        captured = []

        def spy_index(_self, addons):
            captured.append(addons)
            return {}

        cls = type(IrAsset)
        with (
            patch.object(
                cls,
                "_get_addons_active",
                lambda _self, **k: ["web", "base", "mail"],
            ),
            patch.object(
                cls, "_get_assets", lambda _self, domain, **k: IrAsset.browse()
            ),
            patch.object(cls, "_get_manifest_assets", spy_index),
        ):
            IrAsset._get_asset_paths("irasset_p1_probe.bundle", {})

        self.assertTrue(captured, "_get_manifest_assets was invoked")
        self.assertEqual(captured[0], ("base", "mail", "web"))

    def test_topological_sort_key_is_the_sorted_tuple(self):
        IrAsset = self.env["ir.asset"]
        captured = []

        def spy_topo(_self, addons_tuple):
            captured.append(addons_tuple)
            return ()

        with patch.object(type(IrAsset), "_get_addons_sorted_topologically", spy_topo):
            IrAsset._get_manifest_assets.__wrapped__(IrAsset, ("base", "mail", "web"))

        self.assertEqual(captured, [("base", "mail", "web")])


@tagged("post_install", "-at_install")
class TestManifestAssetsIndex(TransactionCase):
    def test_index_groups_commands_by_bundle_in_addon_order(self):
        IrAsset = self.env["ir.asset"]
        manifests = {
            "alpha": {"a.bundle": ["/alpha/one.js"], "b.bundle": ["/alpha/two.js"]},
            "beta": {"a.bundle": ["/beta/one.js", ["remove", "/alpha/one.js"]]},
        }

        class FakeManifest(dict):
            pass

        with (
            patch.object(
                type(IrAsset),
                "_get_addons_sorted_topologically",
                lambda _s, addons: ("alpha", "beta"),
            ),
            patch.object(
                Manifest,
                "for_addon",
                staticmethod(lambda name, **k: FakeManifest(assets=manifests[name])),
            ),
        ):
            index = IrAsset._get_manifest_assets.__wrapped__(IrAsset, ("alpha", "beta"))

        self.assertEqual(
            index["a.bundle"],
            (
                ("alpha", "/alpha/one.js"),
                ("beta", "/beta/one.js"),
                ("beta", ["remove", "/alpha/one.js"]),
            ),
        )
        self.assertEqual(index["b.bundle"], (("alpha", "/alpha/two.js"),))

    def test_a_malformed_command_does_not_break_the_include_prefetch(self):
        IrAsset = self.env["ir.asset"]
        for command in (123, None, {"path": "x"}, ["include"], ["include", "a", "b"]):
            with self.subTest(command=command):
                closure = IrAsset._get_bundles_in_include_closure(
                    "probe.bundle", {"probe.bundle": (("an_addon", command),)}
                )
                self.assertEqual(closure, {"probe.bundle"})
        self.assertEqual(
            IrAsset._get_bundles_in_include_closure(
                "probe.bundle",
                {"probe.bundle": (("an_addon", ["include", "other.bundle"]),)},
            ),
            {"probe.bundle", "other.bundle"},
        )

    def test_index_skips_addons_without_a_manifest(self):
        IrAsset = self.env["ir.asset"]
        with (
            patch.object(
                type(IrAsset),
                "_get_addons_sorted_topologically",
                lambda _s, addons: ("ghost",),
            ),
            patch.object(Manifest, "for_addon", staticmethod(lambda name, **k: None)),
        ):
            self.assertEqual(
                IrAsset._get_manifest_assets.__wrapped__(IrAsset, ("ghost",)), {}
            )

    def test_a_broken_manifest_directive_names_its_addon(self):
        IrAsset = self.env["ir.asset"]
        broken = ["after", "/nowhere/absent.js", "/culprit/new.js"]

        with (
            patch.object(
                type(IrAsset),
                "_get_manifest_assets",
                lambda _s, addons: {"probe.bundle": (("culprit", broken),)},
            ),
            patch.object(
                type(IrAsset),
                "_resolve_paths",
                lambda _s, path_def, resolution: [(path_def, "/full" + path_def, 1)],
            ),
            patch.object(type(IrAsset), "_get_assets", lambda _s, domain, **k: IrAsset),
        ):
            with self.assertRaises(ValueError) as cm:
                IrAsset._get_asset_paths.__wrapped__(IrAsset, "probe.bundle", {})

        message = str(cm.exception)
        self.assertIn("culprit", message)
        self.assertIn("probe.bundle", message)
        self.assertIn("/nowhere/absent.js", message)


@tagged("post_install", "-at_install")
class TestCachedResultsAreImmutable(TransactionCase):
    def test_cached_accessors_return_immutable_collections(self):
        IrAsset = self.env["ir.asset"]
        self.assertIsInstance(IrAsset._get_asset_paths("web.assets_backend", {}), tuple)
        self.assertIsInstance(IrAsset._get_addons_installed(), frozenset)
        self.assertIsInstance(
            IrAsset._get_addons_sorted_topologically(("base",)), tuple
        )

    def test_the_manifest_index_is_read_only(self):
        IrAsset = self.env["ir.asset"]
        index = IrAsset._get_manifest_assets(("base", "web"))
        with self.assertRaises(TypeError):
            index["injected.bundle"] = ()
        with self.assertRaises(TypeError):
            del index["web.assets_backend"]
        self.assertNotIn(
            "injected.bundle", IrAsset._get_manifest_assets(("base", "web"))
        )

    def test_repeated_calls_return_the_identical_object(self):
        IrAsset = self.env["ir.asset"]
        self.assertIs(
            IrAsset._get_asset_paths("web.assets_backend", {}),
            IrAsset._get_asset_paths("web.assets_backend", {}),
        )
        self.assertIs(
            IrAsset._get_manifest_assets(("base", "web")),
            IrAsset._get_manifest_assets(("base", "web")),
        )


@tagged("post_install", "-at_install")
class TestAssetsCacheInvalidatedAtCommit(TransactionCase):
    BUNDLE = "web.assets_backend"

    def _asset_cache_keys(self):
        return [
            key
            for key in self.env.registry.ormcache_lrus["assets"]
            if key[0] == "ir.asset" and "_get_asset_paths" in str(key[1])
        ]

    def _make_asset(self):
        return self.env["ir.asset"].create(
            {"name": "probe", "bundle": self.BUNDLE, "path": "/web/static/src/probe.js"}
        )

    def test_write_registers_a_post_commit_clear(self):
        self.env.cr.postcommit.clear()
        self._make_asset()
        self.assertTrue(
            self.env.cr.postcommit.data.get("ir_asset_cache_invalidated"),
            "a post-commit clear must be queued",
        )
        self.assertEqual(len(self.env.cr.postcommit), 1)

    def test_post_commit_clear_evicts_an_entry_cached_before_commit(self):
        self.env.cr.postcommit.clear()
        self._make_asset()
        self.env["ir.asset"]._get_asset_paths(self.BUNDLE, {})
        self.assertTrue(self._asset_cache_keys(), "entry cached inside the txn")

        self.env.cr.postcommit.run()

        self.assertFalse(
            self._asset_cache_keys(),
            "the pre-commit entry must not outlive the commit",
        )

    def test_repeated_writes_queue_a_single_clear(self):
        self.env.cr.postcommit.clear()
        assets = self._make_asset()
        assets.write({"sequence": 5})
        assets.unlink()
        self.assertEqual(len(self.env.cr.postcommit), 1)


@tagged("post_install", "-at_install")
class TestDirectiveTargetValidation(TransactionCase):
    def test_positional_directive_requires_a_target(self):
        for directive in ("after", "before", "replace"):
            with self.subTest(directive=directive), self.assertRaises(ValidationError):
                self.env["ir.asset"].create(
                    {
                        "name": "no target",
                        "bundle": "probe.bundle",
                        "path": "/web/static/src/x.js",
                        "directive": directive,
                    }
                )

    def test_clearing_the_target_of_a_positional_directive_is_rejected(self):
        asset = self.env["ir.asset"].create(
            {
                "name": "with target",
                "bundle": "probe.bundle",
                "path": "/web/static/src/x.js",
                "directive": "after",
                "target": "/web/static/src/y.js",
            }
        )
        with self.assertRaises(ValidationError):
            asset.write({"target": False})

    def test_directive_cannot_be_blanked(self):
        asset = self.env["ir.asset"].create(
            {
                "name": "plain",
                "bundle": "probe.bundle",
                "path": "/web/static/src/x.js",
            }
        )
        with self.assertRaises(NotNullViolation):
            asset.write({"directive": False})
            asset.flush_recordset()

    def test_target_is_optional_for_non_positional_directives(self):
        asset = self.env["ir.asset"].create(
            {
                "name": "plain",
                "bundle": "probe.bundle",
                "path": "/web/static/src/x.js",
                "directive": "prepend",
            }
        )
        self.assertFalse(asset.target)


def _fake_get_paths(_self, path_def, resolution):
    return [(path_def, "/full" + path_def, 1)]


@tagged("post_install", "-at_install")
class TestDirectiveAttribution(TransactionCase):
    BUNDLE = "attribution.probe"

    def _resolve(self):
        IrAsset = self.env["ir.asset"]
        with patch.object(type(IrAsset), "_resolve_paths", _fake_get_paths):
            IrAsset._get_asset_paths.__wrapped__(IrAsset, self.BUNDLE, {})

    def test_a_broken_record_names_itself(self):
        asset = self.env["ir.asset"].create(
            {
                "name": "the culprit",
                "bundle": self.BUNDLE,
                "directive": "after",
                "path": "/some/new.js",
                "target": "/some/absent.js",
            }
        )
        with self.assertRaises(ValueError) as cm:
            self._resolve()
        message = str(cm.exception)
        self.assertIn("the culprit", message)
        self.assertIn(str(asset.id), message)
        self.assertIn("/some/absent.js", message)
        self.assertIn(self.BUNDLE, message)

    def test_attribution_happens_once_across_includes(self):
        self.env["ir.asset"].create(
            {
                "name": "outer include",
                "bundle": self.BUNDLE,
                "directive": "include",
                "path": "attribution.inner",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "inner culprit",
                "bundle": "attribution.inner",
                "directive": "before",
                "path": "/some/new.js",
                "target": "/some/absent.js",
            }
        )
        with self.assertRaises(ValueError) as cm:
            self._resolve()
        message = str(cm.exception)
        self.assertIn("inner culprit", message)
        self.assertNotIn("outer include", message)
        self.assertEqual(message.count("raised by"), 1)


@tagged("post_install", "-at_install")
class TestBundleAssetsFetch(TransactionCase):
    def _spy(self):
        IrAsset = self.env["ir.asset"]
        calls = []
        original = type(IrAsset)._get_assets

        def spy(inner_self, domain, **params):
            calls.append(domain)
            return original(inner_self, domain, **params)

        return calls, patch.object(type(IrAsset), "_get_assets", spy)

    def test_a_manifest_include_chain_costs_one_fetch(self):
        IrAsset = self.env["ir.asset"]
        manifest_assets = {
            f"chain.b{i}": (("an_addon", ["include", f"chain.b{i + 1}"]),)
            for i in range(4)
        }
        calls, spy = self._spy()
        with (
            spy,
            patch.object(
                type(IrAsset),
                "_get_manifest_assets",
                lambda _s, addons: manifest_assets,
            ),
            patch.object(type(IrAsset), "_resolve_paths", _fake_get_paths),
        ):
            IrAsset._get_asset_paths.__wrapped__(IrAsset, "chain.b0", {})
        self.assertEqual(len(calls), 1, f"one fetch expected, got {calls}")
        self.assertEqual(
            sorted(calls[0][0][2]),
            ["chain.b0", "chain.b1", "chain.b2", "chain.b3", "chain.b4"],
        )

    def test_the_prefetch_does_not_read_unrelated_bundles(self):
        IrAsset = self.env["ir.asset"]
        IrAsset.create(
            {"name": "elsewhere", "bundle": "other.bundle", "path": "/some/x.js"}
        )
        calls, spy = self._spy()
        with (
            spy,
            patch.object(type(IrAsset), "_get_manifest_assets", lambda _s, a: {}),
            patch.object(type(IrAsset), "_resolve_paths", _fake_get_paths),
        ):
            IrAsset._get_asset_paths.__wrapped__(IrAsset, "lonely.bundle", {})
        self.assertEqual(calls, [[("bundle", "in", ["lonely.bundle"])]])

    def test_a_record_include_is_fetched_on_demand(self):
        IrAsset = self.env["ir.asset"]
        IrAsset.create(
            {
                "name": "record include",
                "bundle": "rec.outer",
                "directive": "include",
                "path": "rec.inner",
            }
        )
        IrAsset.create({"name": "leaf", "bundle": "rec.inner", "path": "/some/leaf.js"})
        calls, spy = self._spy()
        with (
            spy,
            patch.object(type(IrAsset), "_get_manifest_assets", lambda _s, a: {}),
            patch.object(type(IrAsset), "_resolve_paths", _fake_get_paths),
        ):
            paths = IrAsset._get_asset_paths.__wrapped__(IrAsset, "rec.outer", {})
        self.assertEqual([entry.path for entry in paths], ["/some/leaf.js"])
        self.assertEqual(len(calls), 2, f"one prefetch + one on demand, got {calls}")

    def test_a_record_include_prefetches_its_own_manifest_closure(self):
        IrAsset = self.env["ir.asset"]
        IrAsset.create(
            {
                "name": "record include",
                "bundle": "deep.outer",
                "directive": "include",
                "path": "deep.m0",
            }
        )
        manifest_assets = {
            f"deep.m{i}": (("an_addon", ["include", f"deep.m{i + 1}"]),)
            for i in range(4)
        }
        calls, spy = self._spy()
        with (
            spy,
            patch.object(
                type(IrAsset), "_get_manifest_assets", lambda _s, a: manifest_assets
            ),
            patch.object(type(IrAsset), "_resolve_paths", _fake_get_paths),
        ):
            IrAsset._get_asset_paths.__wrapped__(IrAsset, "deep.outer", {})
        self.assertEqual(len(calls), 2, f"root + one on demand, got {calls}")
        self.assertEqual(
            sorted(calls[1][0][2]),
            ["deep.m0", "deep.m1", "deep.m2", "deep.m3", "deep.m4"],
        )

    def test_each_bundle_is_fetched_at_most_once(self):
        IrAsset = self.env["ir.asset"]
        resolution = Resolution(active=set())
        calls, spy = self._spy()
        with spy:
            IrAsset._update_bundle_assets(resolution, ["a.b", "c.d"])
            IrAsset._update_bundle_assets(resolution, ["a.b"])
            IrAsset._update_bundle_assets(resolution, ["c.d", "e.f"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], [("bundle", "in", ["e.f"])])

    def test_the_index_keeps_the_sequence_order(self):
        IrAsset = self.env["ir.asset"]
        for sequence in (30, 10, 20):
            IrAsset.create(
                {
                    "name": f"seq {sequence}",
                    "bundle": "order.probe",
                    "path": f"/some/f{sequence}.js",
                    "sequence": sequence,
                }
            )
        resolution = Resolution(active=set())
        IrAsset._update_bundle_assets(resolution, ["order.probe"])
        self.assertEqual(
            [a.sequence for a in resolution.bundle_assets["order.probe"]], [10, 20, 30]
        )

    def test_inactive_records_are_left_out(self):
        IrAsset = self.env["ir.asset"]
        IrAsset.create(
            {
                "name": "off",
                "bundle": "active.probe",
                "path": "/some/off.js",
                "active": False,
            }
        )
        resolution = Resolution(active=set())
        IrAsset._update_bundle_assets(resolution, ["active.probe"])
        self.assertNotIn("active.probe", resolution.bundle_assets)


@tagged("post_install", "-at_install")
class TestStaticContainment(TransactionCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.static = Path(self.tmp, "an_addon", "static")
        (self.static / "src" / "real").mkdir(parents=True)
        (self.static / "src" / "real" / "in.js").write_text("var a;")
        self.outside = Path(self.tmp, "elsewhere")
        self.outside.mkdir()
        (self.outside / "secret.js").write_text("var s;")
        Path(self.static, "src", "linked").symlink_to(self.static / "src" / "real")
        Path(self.static, "src", "escape").symlink_to(self.outside)
        Path(self.static, "src", "file_link.js").symlink_to(
            self.static / "src" / "real" / "in.js"
        )

    def _glob(self, pattern):
        return [
            os.path.relpath(path, self.static)
            for path, _mtime in _get_static_files(
                str(self.static / pattern), str(self.static)
            )
        ]

    def test_symlink_landing_inside_static_is_followed(self):
        self.assertEqual(self._glob("src/linked/in.js"), ["src/real/in.js"])
        self.assertEqual(self._glob("src/linked/*.js"), ["src/real/in.js"])
        self.assertEqual(self._glob("src/file_link.js"), ["src/real/in.js"])

    def test_symlink_landing_outside_static_is_refused(self):
        with self.assertLogs("odoo.addons.base.models.ir_asset_paths", level="WARNING"):
            self.assertEqual(self._glob("src/escape/secret.js"), [])
        with self.assertLogs("odoo.addons.base.models.ir_asset_paths", level="WARNING"):
            self.assertEqual(self._glob("src/escape/*.js"), [])

    def test_a_link_and_its_target_collapse_to_one_entry(self):
        self.assertEqual(self._glob("src/*/*.js"), ["src/real/in.js"])


@tagged("post_install", "-at_install")
class TestPerBundleFiltering(TransactionCase):
    def test_the_hook_sees_one_bundle_at_a_time(self):
        IrAsset = self.env["ir.asset"]
        for bundle in ("split.a", "split.b"):
            for index in (1, 2):
                IrAsset.create(
                    {
                        "name": f"{bundle} {index}",
                        "bundle": bundle,
                        "path": f"/some/{bundle}_{index}.js",
                    }
                )
        seen = []
        original = type(IrAsset)._filter_bundle_assets

        def spy(inner_self, assets, **params):
            seen.append(sorted(assets.mapped("bundle")))
            return original(inner_self, assets, **params)

        resolution = Resolution(active=set())
        with patch.object(type(IrAsset), "_filter_bundle_assets", spy):
            IrAsset._update_bundle_assets(resolution, ["split.a", "split.b"])

        self.assertEqual(sorted(seen), [["split.a", "split.a"], ["split.b", "split.b"]])
        self.assertEqual(len(resolution.bundle_assets["split.a"]), 2)
        self.assertEqual(len(resolution.bundle_assets["split.b"]), 2)

    def test_the_hook_can_drop_records(self):
        IrAsset = self.env["ir.asset"]
        IrAsset.create(
            {"name": "kept", "bundle": "drop.probe", "path": "/some/kept.js"}
        )
        IrAsset.create(
            {"name": "dropped", "bundle": "drop.probe", "path": "/some/dropped.js"}
        )
        resolution = Resolution(active=set())
        with patch.object(
            type(IrAsset),
            "_filter_bundle_assets",
            lambda _s, assets, **p: assets.filtered(lambda a: a.name == "kept"),
        ):
            IrAsset._update_bundle_assets(resolution, ["drop.probe"])
        self.assertEqual(
            [a.name for a in resolution.bundle_assets["drop.probe"]], ["kept"]
        )


@tagged("post_install", "-at_install")
class TestInvalidationIsNarrow(TransactionCase):
    BUNDLE = "narrow.probe"

    def _cached_keys(self):
        return [
            key
            for key in self.env.registry.ormcache_lrus["assets"]
            if key[0] == "ir.asset" and "_get_asset_paths" in str(key[1])
        ]

    def _warm(self, asset):
        self.env.registry.clear_cache("assets")
        self.env["ir.asset"]._get_asset_paths(self.BUNDLE, {})
        self.assertTrue(self._cached_keys(), "cache should be warm")

    def _make(self):
        return self.env["ir.asset"].create(
            {"name": "probe", "bundle": self.BUNDLE, "path": "/some/probe.js"}
        )

    def test_renaming_keeps_the_cache(self):
        asset = self._make()
        self._warm(asset)
        asset.write({"name": "renamed"})
        self.assertTrue(self._cached_keys(), "a rename must not drop the cache")

    def test_every_resolution_field_drops_the_cache(self):
        asset = self._make()
        for field, value in (
            ("path", "/some/other.js"),
            ("bundle", "narrow.other"),
            ("sequence", 99),
            ("directive", "prepend"),
            ("active", False),
        ):
            with self.subTest(field=field):
                asset.write({"bundle": self.BUNDLE, "active": True})
                self._warm(asset)
                asset.write({field: value})
                self.assertFalse(
                    self._cached_keys(), f"writing {field} must drop the cache"
                )

    def test_target_counts_as_a_resolution_field(self):
        self.assertIn(
            "target", self.env["ir.asset"]._get_fields_invalidating_assets_cache()
        )


@tagged("post_install", "-at_install")
class TestExternalUrlShortCircuit(TransactionCase):
    def test_an_external_url_never_consults_a_manifest(self):
        IrAsset = self.env["ir.asset"]
        resolution = Resolution(active=IrAsset._get_addons_installed())
        for url in (
            "http://external.link/external.js",
            "https://cdn.example.com/a.css",
            "//cdn.example.com/b.js",
            "/web/content/1234/some.js",
        ):
            with self.subTest(url=url):
                resolved = IrAsset._resolve_paths(url, resolution)
                self.assertEqual(len(resolved), 1)
                self.assertTrue(resolved[0].is_external)
                self.assertEqual(resolved[0].path, url)
        self.assertEqual(
            resolution._manifests, {}, "no manifest lookup should have happened"
        )

    def test_a_bundleable_path_still_resolves(self):
        IrAsset = self.env["ir.asset"]
        resolution = Resolution(active=IrAsset._get_addons_installed())
        resolved = IrAsset._resolve_paths(
            "/base/static/src/scss/res_users.scss", resolution
        )
        self.assertEqual(len(resolved), 1)
        self.assertFalse(resolved[0].is_external)
        self.assertIn("base", resolution._manifests)


@tagged("post_install", "-at_install")
class TestEveryServableBundleResolves(TransactionCase):
    @staticmethod
    def _is_include_only(bundle):
        return bundle.split(".", 1)[1].startswith("_")

    def test_every_publicly_named_bundle_resolves_standalone(self):
        IrAsset = self.env["ir.asset"]
        addons = tuple(sorted(IrAsset._get_addons_active()))
        servable = sorted(
            bundle
            for bundle in IrAsset._get_manifest_assets(addons)
            if bundle.count(".") == 1 and not self._is_include_only(bundle)
        )
        self.assertGreater(len(servable), 20, "the probe must see real bundles")
        broken = {}
        for bundle in servable:
            try:
                IrAsset._get_asset_paths(bundle, {})
            except Exception as exc:
                broken[bundle] = f"{type(exc).__name__}: {exc}"
        self.assertEqual(broken, {})

    def test_an_include_only_fragment_may_legitimately_need_its_parent(self):
        IrAsset = self.env["ir.asset"]
        addons = tuple(sorted(IrAsset._get_addons_active()))
        fragments = [
            bundle
            for bundle in IrAsset._get_manifest_assets(addons)
            if bundle.count(".") == 1 and self._is_include_only(bundle)
        ]
        self.assertTrue(fragments, "the convention must actually be in use")
        for bundle in fragments:
            with self.subTest(bundle=bundle):
                self.assertTrue(bundle.split(".", 1)[1].startswith("_"))


@tagged("post_install", "-at_install")
class TestUnservableBundleNameWarns(TransactionCase):
    def test_a_dotless_bundle_warns(self):
        with self.assertLogs("odoo.addons.base.models.ir_asset", level="WARNING") as cm:
            self.env["ir.asset"].create(
                {"name": "probe", "bundle": "no_dot", "path": "/some/x.js"}
            )
        self.assertIn("no_dot", " ".join(cm.output))
        self.assertIn("<addon>.<name>", " ".join(cm.output))

    def test_a_conforming_bundle_is_silent(self):
        with self.assertNoLogs("odoo.addons.base.models.ir_asset", level="WARNING"):
            self.env["ir.asset"].create(
                {"name": "probe", "bundle": "an_addon.a_bundle", "path": "/some/x.js"}
            )

    def test_the_warning_matches_what_the_parser_accepts(self):
        IrAsset = self.env["ir.asset"]
        for bundle in ("one.dot",):
            IrAsset._parse_bundle_name(f"{bundle}.min.js", False)
        for bundle in ("no_dot", "three.dots.here"):
            with self.assertRaises(ValueError):
                IrAsset._parse_bundle_name(f"{bundle}.min.js", False)


@tagged("post_install", "-at_install")
class TestAssetsCacheStores(TransactionCase):
    BUNDLES = ["cachestore.a", "cachestore.b", "cachestore.c"]

    def _lrus(self):
        return self.env.registry.ormcache_lrus

    def test_the_two_stores_are_separate_and_sized_apart(self):
        lrus = self._lrus()
        self.assertIn("assets", lrus)
        self.assertIn("assets.links", lrus)
        self.assertIsNot(lrus["assets"], lrus["assets.links"])
        self.assertGreater(lrus["assets.links"].count, lrus["assets"].count)

    def test_variants_multiply_only_the_sibling_store(self):
        IrQweb = self.env["ir.qweb"]
        self.env.registry.clear_cache("assets")
        for bundle in self.BUNDLES:
            for css, js in ((True, False), (False, True)):
                for rtl in (False, True):
                    for autoprefix in (False, True):
                        IrQweb._get_asset_links_cached(
                            bundle,
                            css=css,
                            js=js,
                            assets_params={},
                            rtl=rtl,
                            autoprefix=autoprefix,
                        )
        resolutions = len(self._lrus()["assets"])
        urls = len(self._lrus()["assets.links"])
        self.assertEqual(
            resolutions,
            len(self.BUNDLES),
            "one resolution per bundle, whatever the variant count",
        )
        self.assertEqual(urls, len(self.BUNDLES) * 8)
        self.assertGreater(
            urls,
            resolutions,
            "the many cheap entries no longer occupy the resolution store",
        )

    def test_clearing_the_group_still_drops_both(self):
        IrAsset = self.env["ir.asset"]
        IrQweb = self.env["ir.qweb"]
        IrAsset._get_asset_paths(self.BUNDLES[0], {})
        IrQweb._get_asset_links_cached(
            self.BUNDLES[0], css=True, js=False, assets_params={}
        )
        self.assertTrue(self._lrus()["assets"])
        self.assertTrue(self._lrus()["assets.links"])

        self.env["ir.asset"].create(
            {"name": "probe", "bundle": self.BUNDLES[0], "path": "/some/x.js"}
        )

        self.assertFalse(self._lrus()["assets"])
        self.assertFalse(self._lrus()["assets.links"])

    def test_the_sibling_is_not_a_clear_group_of_its_own(self):
        with self.assertRaises(ValueError):
            self.env.registry.clear_cache("assets.links")

    def test_the_static_file_globs_do_not_occupy_the_resolution_store(self):
        IrAsset = self.env["ir.asset"]
        self.env.registry.clear_cache("assets")
        IrAsset._get_asset_paths("web.assets_backend", {})
        self.assertTrue(self._lrus()["assets.files"])
        self.assertLess(
            len(self._lrus()["assets"]),
            len(self._lrus()["assets.files"]),
            "a page's hundreds of globs must not evict its compiled bundles",
        )
        self.env["ir.asset"].create(
            {"name": "probe", "bundle": self.BUNDLES[0], "path": "/some/x.js"}
        )
        self.assertFalse(self._lrus()["assets.files"])


@tagged("post_install", "-at_install")
class TestInstalledAddonGate(TransactionCase):
    EXISTING_FILE = "/base/static/src/scss/res_users.scss"

    def _uninstalled_addon_file(self):
        installed = self.env["ir.asset"]._get_addons_installed()
        resolution = Resolution(active=installed)
        for manifest in Manifest.get_all_addon_manifests():
            if manifest.name in installed:
                continue
            paths = self.env["ir.asset"]._resolve_paths(
                f"/{manifest.name}/static/src/**/*.js",
                Resolution(active=installed | {manifest.name}),
            )
            if paths and paths[0].full_path:
                return paths[0].path, resolution
        return None, resolution

    def test_the_file_exists_but_the_addon_does_not_resolve(self):
        IrAsset = self.env["ir.asset"]
        installed = Resolution(active=IrAsset._get_addons_installed())

        resolved = IrAsset._resolve_paths(self.EXISTING_FILE, installed)
        gated = IrAsset._resolve_paths(
            self.EXISTING_FILE, Resolution(active=frozenset())
        )

        self.assertEqual(len(resolved), 1)
        self.assertIsNotNone(resolved[0].full_path)
        self.assertEqual(gated, ())

    def test_a_gated_addon_yields_nothing_rather_than_an_attachment_url(self):
        gated = self.env["ir.asset"]._resolve_paths(
            "/base/static/src/scss/__no_such_file__.scss",
            Resolution(active=frozenset()),
        )

        self.assertEqual(gated, ())

    def test_wildcards_do_not_expand_into_a_gated_addon(self):
        IrAsset = self.env["ir.asset"]
        installed = Resolution(active=IrAsset._get_addons_installed())

        expanded = IrAsset._resolve_paths("/base/static/src/scss/*.scss", installed)
        gated = IrAsset._resolve_paths(
            "/base/static/src/scss/*.scss", Resolution(active=frozenset())
        )

        self.assertTrue(expanded)
        self.assertEqual(gated, ())

    def test_a_record_cannot_pull_in_an_uninstalled_addon(self):
        path, _resolution = self._uninstalled_addon_file()
        if path is None:
            self.skipTest("every addon on the addons path is installed")
        bundle = "base.test_installed_gate"
        self.env["ir.asset"].create(
            {"name": "uninstalled addon probe", "bundle": bundle, "path": path}
        )

        entries = self.env["ir.asset"]._get_asset_paths(bundle, {})

        self.assertEqual(entries, ())

    def test_server_wide_modules_are_treated_as_installed(self):
        IrAsset = self.env["ir.asset"]
        with tools.config.patch(server_wide_modules=["__probe_addon__"]):
            installed = IrAsset._get_addons_installed()

        self.assertIn("__probe_addon__", installed)

    def test_narrowing_the_active_list_narrows_the_bundle(self):
        IrAsset = self.env["ir.asset"]
        bundle = "base.test_active_narrowing"
        self.env["ir.asset"].create(
            {
                "name": "active narrowing probe",
                "bundle": bundle,
                "path": self.EXISTING_FILE,
            }
        )
        self.assertTrue(IrAsset._get_asset_paths(bundle, {}))

        active = set(IrAsset._get_addons_active()) - {"base"}
        with patch.object(
            type(IrAsset), "_get_addons_active", return_value=frozenset(active)
        ):
            self.env.registry.clear_cache("assets")
            narrowed = IrAsset._get_asset_paths(bundle, {})
        self.env.registry.clear_cache("assets")

        self.assertEqual(narrowed, ())
