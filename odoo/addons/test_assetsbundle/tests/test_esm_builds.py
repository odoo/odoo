import importlib.util
from datetime import timedelta
from unittest.mock import patch

from psycopg.errors import UniqueViolation

from odoo import fields
from odoo.api import SUPERUSER_ID
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import file_path, mute_logger

from odoo.addons.base.models import ir_qweb_assets


@tagged("post_install", "-at_install", "assets_bundle")
class TestEsmBuildLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Build = cls.env["ir.asset.build"].sudo()

    def _row(self, directory, name="b.esm.js"):
        IrAttachment = self.env["ir.attachment"].with_user(SUPERUSER_ID)
        return IrAttachment.create(
            IrAttachment._prepare_generated_asset_vals(
                name=name,
                mimetype="text/javascript",
                raw=b"export {};",
                url=f"{directory}{name}",
            )
        )

    def _publish(self, directory, variant="default", bundle="test.builds", **extra):
        return self.Build._publish(
            {
                "kind": "bundle",
                "bundle": bundle,
                "variant": variant,
                "directories": [directory],
                **extra,
            }
        )

    def _age(self, build, days):
        build.superseded_at = fields.Datetime.now() - timedelta(days=days)

    def test_a_variant_never_supersedes_another(self):
        plain = self._publish("/web/assets/esm/aaaa/")
        paged = self._publish("/web/assets/esm/bbbb/", variant="page=web.assets_web")
        self.assertEqual((plain | paged).mapped("state"), ["current", "current"])

    def test_a_rebuild_supersedes_and_keeps_the_previous_build_served(self):
        row = self._row("/web/assets/esm/aaaa/")
        first = self._publish("/web/assets/esm/aaaa/")
        second = self._publish("/web/assets/esm/bbbb/")
        self.assertEqual(first.state, "superseded")
        self.assertTrue(first.superseded_at)
        self.assertEqual(second.state, "current")
        self.assertTrue(row.exists(), "a page rendered a minute ago still asks for it")

    def test_a_revert_recurrents_the_earlier_build(self):
        first = self._publish("/web/assets/esm/aaaa/")
        second = self._publish("/web/assets/esm/bbbb/")
        again = self._publish("/web/assets/esm/aaaa/")
        self.assertEqual(again, first)
        self.assertEqual(first.state, "current")
        self.assertFalse(first.superseded_at)
        self.assertEqual(second.state, "superseded")

    def test_the_sweep_waits_for_the_grace(self):
        kept_row = self._row("/web/assets/esm/aaaa/")
        old = self._publish("/web/assets/esm/aaaa/")
        self._publish("/web/assets/esm/bbbb/")
        self._age(old, 1)
        self.Build._sweep()
        self.assertTrue(old.exists())
        self.assertTrue(kept_row.exists())
        self._age(old, 30)
        self.Build._sweep()
        self.assertFalse(old.exists())
        self.assertFalse(kept_row.exists())

    def test_the_sweep_keeps_a_directory_another_build_still_owns(self):
        shared = self._row("/web/assets/esm/cccc/")
        old = self._publish("/web/assets/esm/cccc/")
        self._publish("/web/assets/esm/dddd/")
        self._publish("/web/assets/esm/cccc/", variant="page=web.assets_frontend")
        self._age(old, 30)
        self.Build._sweep()
        self.assertFalse(old.exists())
        self.assertTrue(shared.exists(), "the page variant compiled the same bytes")

    def test_one_current_build_per_variant_is_a_constraint(self):
        self._publish("/web/assets/esm/aaaa/")
        with (
            mute_logger("odoo.db.cursor"),
            self.assertRaises(UniqueViolation),
            self.env.cr.savepoint(),
        ):
            self.Build.create(
                {
                    "kind": "bundle",
                    "bundle": "test.builds",
                    "variant": "default",
                    "directories": ["/web/assets/esm/eeee/"],
                    "fingerprint": "eeee",
                }
            )

    def test_reuse_prefers_the_current_build_then_one_in_grace(self):
        old = self._publish("/web/assets/esm/aaaa/", source_key="k1")
        current = self._publish("/web/assets/esm/bbbb/", source_key="k2")
        self.assertEqual(
            self.Build._find_reusable("bundle", "test.builds", "default", "k2"),
            current,
        )
        self.assertEqual(
            self.Build._find_reusable("bundle", "test.builds", "default", "k1"), old
        )
        self.assertFalse(
            self.Build._find_reusable("bundle", "test.builds", "page=x", "k2")
        )

    def test_a_bundle_no_installed_addon_declares_is_retired(self):
        gone = self._publish(
            "/web/assets/esm/ffff/", bundle="test_builds_not_an_addon.assets"
        )
        kept = self._publish("/web/assets/esm/abab/", bundle="web.assets_web")
        self.Build._retire_uninstalled()
        self.assertEqual(gone.state, "superseded")
        self.assertEqual(kept.state, "current")

    def test_an_unchanged_publish_writes_nothing(self):
        build = self._publish("/web/assets/esm/aaaa/", source_key="k")
        Model = type(self.Build)
        refuse = AssertionError("an unchanged publish must not write")
        with (
            patch.object(Model, "write", side_effect=refuse),
            patch.object(Model, "create", side_effect=refuse),
        ):
            again = self._publish("/web/assets/esm/aaaa/", source_key="k")
        self.assertEqual(again, build)


@tagged("post_install", "-at_install", "assets_bundle")
class TestEsmBuildVariantsAreServedSideBySide(TransactionCase):
    def test_two_variants_of_one_bundle_both_stay_served(self):
        qweb = self.env["ir.qweb"]
        # the production branch writes rows and the build on this cursor
        with patch.object(ir_qweb_assets._module, "current_test", None):
            plain = qweb._save_esm_attachment("test.builds.side", "export const a=1;")
            paged = qweb._save_esm_attachment(
                "test.builds.side",
                "export const a=2;",
                variant="page=web.assets_frontend",
            )
            plain_again = qweb._save_esm_attachment(
                "test.builds.side", "export const a=1;"
            )
        self.assertEqual(plain_again, plain)
        IrAttachment = self.env["ir.attachment"].sudo()
        for url in (plain, paged):
            with self.subTest(url=url):
                self.assertTrue(
                    IrAttachment.search_count(
                        IrAttachment._get_domain_generated_assets(url)
                    )
                )
        builds = (
            self.env["ir.asset.build"]
            .sudo()
            .search([("bundle", "=", "test.builds.side")])
        )
        self.assertEqual(builds.mapped("state"), ["current", "current"])


@tagged("post_install", "-at_install", "assets_bundle")
class TestEsmBuildAdoption(TransactionCase):
    def _migration(self):
        path = file_path("base/migrations/1.98/post-migrate_esm_asset_builds.py")
        spec = importlib.util.spec_from_file_location("esm_asset_builds", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _row(self, url):
        IrAttachment = self.env["ir.attachment"].with_user(SUPERUSER_ID)
        return IrAttachment.create(
            IrAttachment._prepare_generated_asset_vals(
                name=url.rsplit("/", 1)[-1],
                mimetype="text/javascript",
                raw=b"export {};",
                url=url,
            )
        )

    def test_every_stored_directory_becomes_one_superseded_build(self):
        Build = self.env["ir.asset.build"].sudo()
        self._row("/web/assets/esm/zzad01/x.adopt.esm.js")
        self._row("/web/assets/esm/zzad01/x.adopt.meta.json")
        self._row("/web/assets/esm/zzad02/chunk-ABCDEFGH.esm.js")
        self._row("/web/assets/esm/zzad02/group.meta.json")
        self._row("/web/assets/lib/zzad03/web/static/lib/x.js")
        bridge = self._row("/web/assets/esm/bridges/zzad04.js")
        pointer = self._row("/web/assets/esm/by-source/k/x.adopt.json")
        self._row("/web/assets/esm/zzad05/x.owned.esm.js")
        owned = Build._publish(
            {
                "kind": "bundle",
                "bundle": "x.owned",
                "variant": "default",
                "directories": ["/web/assets/esm/zzad05/"],
            }
        )

        self._migration().migrate(self.env.cr, "1.96")

        adopted = Build.search([("variant", "=like", "legacy:%")]).filtered(
            lambda b: b.directories[0].split("/")[4].startswith("zzad")
        )
        self.assertEqual(
            {(b.kind, b.bundle, b.directories[0]) for b in adopted},
            {
                ("bundle", "x.adopt", "/web/assets/esm/zzad01/"),
                ("group", "legacy", "/web/assets/esm/zzad02/"),
                ("lib", "esm.libs", "/web/assets/lib/zzad03/"),
            },
        )
        self.assertEqual(set(adopted.mapped("state")), {"superseded"})
        self.assertEqual(owned.state, "current", "an owned directory is left alone")
        self.assertTrue(bridge.exists(), "a bridge belongs to no build")
        self.assertFalse(pointer.exists(), "the build carries the source key now")
