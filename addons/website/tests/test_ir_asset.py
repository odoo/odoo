import logging
from unittest.mock import patch

import odoo.tests

_logger = logging.getLogger(__name__)


@odoo.tests.common.tagged("post_install", "-at_install")
class TestIrAsset(odoo.tests.HttpCase):
    def test_01_website_specific_assets(self):
        IrAsset = self.env["ir.asset"]
        Website = self.env["website"]

        website_1 = Website.create({"name": "Website 1"})
        website_2 = Website.create({"name": "Website 2"})

        assets = IrAsset.create(
            [
                {
                    "key": "test0",
                    "name": "0",
                    "bundle": "test_bundle.irasset",
                    "path": "/website/test/base0.css",
                },
                {
                    "key": "test1",
                    "name": "1",
                    "bundle": "test_bundle.irasset",
                    "path": "/website/test/base1.css",
                },
                {
                    "key": "test2",
                    "name": "2",
                    "bundle": "test_bundle.irasset",
                    "path": "/website/test/base2.css",
                },
            ]
        )

        assets[1].with_context(website_id=website_1.id).write(
            {
                "path": "/website/test/specific1.css",
            }
        )
        assets[2].with_context(website_id=website_1.id).write(
            {
                "active": False,
            }
        )

        files = IrAsset._get_asset_paths(
            "test_bundle.irasset", {"website_id": website_1.id}
        )
        self.assertEqual(
            len(files), 2, "There should be two assets in the specific website."
        )
        self.assertEqual(
            files[0][0],
            "/website/test/base0.css",
            "First asset should be the same as the base one.",
        )
        self.assertEqual(
            files[1][0],
            "/website/test/specific1.css",
            "Second asset should be the specific one.",
        )

        files = IrAsset._get_asset_paths(
            "test_bundle.irasset", {"website_id": website_2.id}
        )
        self.assertEqual(
            len(files), 3, "All three assets should be in the unmodified website."
        )
        self.assertEqual(
            files[0][0],
            "/website/test/base0.css",
            "First asset should be the base one.",
        )
        self.assertEqual(
            files[1][0],
            "/website/test/base1.css",
            "Second asset should be the base one.",
        )
        self.assertEqual(
            files[2][0],
            "/website/test/base2.css",
            "Third asset should be the base one.",
        )


@odoo.tests.common.tagged("post_install", "-at_install")
class TestSpecificAssetScope(odoo.tests.common.TransactionCase):
    def test_false_key_in_first_copy_does_not_drop_generated_identity(self):
        website = self.env.ref("website.default_website")
        assets = self.env["ir.asset"]
        generic = assets.create(
            {
                "name": "empty key",
                "bundle": "challenge.empty-key",
                "path": "/web/static/src/core/utils/objects.js",
            }
        )
        generic.with_context(website_id=website.id).write(
            {"key": False, "active": False}
        )
        overrides = assets.with_context(active_test=False).search(
            [
                ("website_id", "=", website.id),
                ("bundle", "=", "challenge.empty-key"),
            ]
        )
        self.assertTrue(generic.key)
        self.assertEqual(overrides.key, generic.key)
        self.assertEqual(
            (generic | overrides)._filtered_most_specific(website.id), overrides
        )

    def test_unkeyed_copy_preserves_an_explicit_identity(self):
        website = self.env.ref("website.default_website")
        assets = self.env["ir.asset"]
        generic = assets.create(
            {
                "name": "explicit identity",
                "bundle": "challenge.identity",
                "path": "/web/static/src/core/utils/objects.js",
            }
        )
        generic.with_context(website_id=website.id).write(
            {
                "key": "challenge.explicit",
                "path": "/web/static/src/core/utils/arrays.js",
            }
        )
        self.assertEqual(generic.key, "challenge.explicit")
        generic.with_context(website_id=website.id).write({"active": False})
        overrides = assets.with_context(active_test=False).search(
            [
                ("website_id", "=", website.id),
                ("bundle", "=", "challenge.identity"),
            ]
        )
        _logger.debug(
            "Explicit asset identity: source=%s key=%s overrides=%s",
            generic.id,
            generic.key,
            overrides.ids,
        )
        self.assertEqual(len(overrides), 1)
        self.assertFalse(overrides.active)

    def test_unkeyed_asset_overrides_are_independent_between_websites(self):
        website = self.env.ref("website.default_website")
        other = self.env["website"].create({"name": "Asset challenge"})
        assets = self.env["ir.asset"]
        generic = assets.create(
            {
                "name": "two sites",
                "bundle": "challenge.sites",
                "path": "/web/static/src/core/utils/objects.js",
            }
        )
        generic.with_context(website_id=website.id).write(
            {"path": "/web/static/src/core/utils/arrays.js"}
        )
        first_key = generic.key
        generic.with_context(website_id=other.id).write(
            {"path": "/web/static/src/core/utils/strings.js"}
        )
        self.assertEqual(generic.key, first_key)
        candidates = assets.search([("bundle", "=", "challenge.sites")])
        self.assertEqual(len(candidates), 3)
        self.assertEqual(
            candidates._filtered_most_specific(website.id).path,
            "/web/static/src/core/utils/arrays.js",
        )
        self.assertEqual(
            candidates._filtered_most_specific(other.id).path,
            "/web/static/src/core/utils/strings.js",
        )
        self.assertEqual(candidates._filtered_most_specific(False), generic)

    def test_unkeyed_asset_copy_does_not_overwrite_an_unrelated_asset(self):
        website = self.env.ref("website.default_website")
        assets = self.env["ir.asset"]
        generic = assets.create(
            {
                "name": "unkeyed generic",
                "bundle": "audit.unkeyed",
                "path": "/web/static/src/core/utils/objects.js",
            }
        )
        unrelated = assets.create(
            {
                "name": "unkeyed specific",
                "bundle": "audit.unkeyed",
                "path": "/web/static/src/core/utils/arrays.js",
                "website_id": website.id,
            }
        )
        new_path = "/web/static/src/core/utils/strings.js"
        generic.with_context(website_id=website.id).write({"path": new_path})
        _logger.debug(
            "Unkeyed asset copy: source=%s key=%s unrelated=%s path=%s",
            generic.id,
            generic.key,
            unrelated.id,
            unrelated.path,
        )
        self.assertEqual(unrelated.path, "/web/static/src/core/utils/arrays.js")
        self.assertEqual(generic.path, "/web/static/src/core/utils/objects.js")
        specific = assets.search(
            [("website_id", "=", website.id), ("key", "=", generic.key)]
        )
        self.assertEqual(specific.path, new_path)
        generic.with_context(website_id=website.id).write({"active": False})
        self.assertFalse(specific.active)
        self.assertTrue(unrelated.active)
        selected = (
            assets.with_context(active_test=False)
            .search(
                [
                    ("bundle", "=", "audit.unkeyed"),
                ]
            )
            ._filtered_most_specific(website.id)
        )
        self.assertEqual(set(selected.ids), {specific.id, unrelated.id})

    def test_a_specific_record_does_not_hide_a_generic_one_in_another_bundle(self):
        IrAsset = self.env["ir.asset"]
        website = self.env["website"].create({"name": "Scope"})
        path = "/web/static/src/core/utils/objects.js"
        other = "/web/static/src/core/utils/arrays.js"

        generic = IrAsset.create(
            {
                "key": "scope.probe",
                "name": "generic",
                "bundle": "scope.outer",
                "path": path,
            }
        )
        generic.with_context(website_id=website.id).write(
            {"bundle": "scope.inner", "path": other}
        )
        specific = IrAsset.search(
            [("key", "=", "scope.probe"), ("website_id", "=", website.id)]
        )
        self.assertTrue(specific)
        self.assertEqual(generic.bundle, "scope.outer")
        self.assertEqual(specific.bundle, "scope.inner")

        closure = {
            "scope.outer": (("an_addon", ["include", "scope.inner"]),),
        }
        with patch.object(
            type(IrAsset), "_get_manifest_assets", lambda _s, addons: closure
        ):
            self.env.registry.clear_cache("assets")
            resolved = IrAsset._get_asset_paths.__wrapped__(
                IrAsset, "scope.outer", {"website_id": website.id}
            )

        self.assertEqual(
            [entry.path for entry in resolved],
            [other, path],
            "the generic record still owns its own bundle's slot",
        )
