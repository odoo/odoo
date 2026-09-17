import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from odoo import api
from odoo.api import SUPERUSER_ID
from odoo.db import db_connect
from odoo.exceptions import MissingError
from odoo.modules.registry import Registry
from odoo.tests.common import BaseCase, TransactionCase, get_db_name, tagged
from odoo.tools.assets.constants import like_escape
from odoo.tools.misc import file_path

from .common import asset_file, make_cursor_readonly
from odoo.addons.base.models.assetsbundle import (
    ANY_UNIQUE,
    AssetAttachmentStore,
    AssetsBundle,
    JavascriptAsset,
)
from odoo.addons.base.models.assetsbundle import bundle as bundle_module
from odoo.addons.base.models.assetsbundle.common import _pipeline_fingerprint
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.addons.base.models.ir_attachment_assets import (
    IrAttachment as AssetIrAttachment,
)

PLAIN_JS = "(function () {\n    window.auditX = 1;\n})();\n"


class _FakeIrAsset:
    def __init__(self, calls):
        self.calls = calls

    def _get_asset_bundle_url(self, bundle_name, unique, assets_params):
        self.calls.append((bundle_name, unique, assets_params))
        return f"/web/assets/{unique}/{bundle_name}"

    def _get_asset_bundle_url_pattern(self, filename, unique, assets_params):
        return self._get_asset_bundle_url(like_escape(filename), unique, assets_params)


class _FakeIrAttachment:
    _prepare_generated_asset_vals = AssetIrAttachment._prepare_generated_asset_vals


class _FakeEnv:
    def __init__(self, calls):
        self._models = {
            "ir.asset": _FakeIrAsset(calls),
            "ir.attachment": _FakeIrAttachment(),
        }

    def __getitem__(self, model):
        assert model in self._models, model
        return self._models[model]


class TestAssetAttachmentStoreUnit(BaseCase):
    def _store(self, calls, *, rtl=False, autoprefix=False, params=None):
        return AssetAttachmentStore(
            _FakeEnv(calls),
            "web.assets_web",
            assets_params=params or {},
            rtl=rtl,
            autoprefix=autoprefix,
            version_provider=lambda asset_type: "abc1234",
        )

    def test_pure_helpers_need_no_env(self):
        store = self._store([])
        self.assertTrue(store.is_css("min.css"))
        self.assertTrue(store.is_css("css.map"))
        self.assertFalse(store.is_css("min.js"))
        self.assertFalse(hasattr(store, "bundle"))

    def test_get_asset_url_uses_plain_name(self):
        calls = []
        url = self._store(calls).get_asset_url("abc1234", "min.js")
        bundle_name, unique, _params = calls[-1]
        self.assertEqual(bundle_name, "web.assets_web.min.js")
        self.assertEqual(unique, "abc1234")
        self.assertEqual(url, "/web/assets/abc1234/web.assets_web.min.js")

    def test_pattern_like_escapes_bundle_name(self):
        calls = []
        self._store(calls).get_asset_url_pattern(extension="min.js")
        bundle_name, unique, _params = calls[-1]
        self.assertEqual(bundle_name, r"web.assets\_web.min.js")
        self.assertEqual(unique, ANY_UNIQUE)

    def test_url_encodes_rtl_and_autoprefix_for_css_only(self):
        calls = []
        store = self._store(calls, rtl=True, autoprefix=True)
        store.get_asset_url("v", "min.css")
        self.assertEqual(calls[-1][0], "web.assets_web.rtl.autoprefixed.min.css")
        store.get_asset_url("v", "min.js")
        self.assertEqual(calls[-1][0], "web.assets_web.min.js")

    def test_attachment_values_pins_the_write_side_identity(self):
        values = self._store([])._attachment_values(
            name="web.assets_web.min.css",
            mimetype="text/css",
            raw=b"x{}",
            url="/web/assets/abc1234/web.assets_web.min.css",
        )
        self.assertEqual(
            values,
            {
                "name": "web.assets_web.min.css",
                "mimetype": "text/css",
                "res_model": "ir.ui.view",
                "res_id": False,
                "type": "binary",
                "public": True,
                "raw": b"x{}",
                "url": "/web/assets/abc1234/web.assets_web.min.css",
            },
        )


class TestSaveAttachmentGuard(TransactionCase):
    def test_invalid_extension_rejected(self):
        bundle = AssetsBundle("test_assetsbundle.extguard", [], env=self.env)
        with self.assertRaisesRegex(ValueError, "Invalid asset extension"):
            bundle.save_attachment("exe", "content")

    def test_mimetypes_match_extension(self):
        bundle = AssetsBundle("test_assetsbundle.extguard2", [], env=self.env)
        self.assertEqual(bundle.save_attachment("min.css", "b{}").mimetype, "text/css")
        self.assertEqual(
            bundle.save_attachment("js.map", "{}").mimetype, "application/json"
        )
        # the same mimetype the ESM route and the bridge shims serve
        self.assertEqual(
            bundle.save_attachment("min.js", "x").mimetype, "text/javascript"
        )

    def test_xml_extensions_rejected(self):
        bundle = AssetsBundle("test_assetsbundle.extguard3", [], env=self.env)
        for extension in ("xml", "min.xml"):
            with self.assertRaisesRegex(ValueError, "Invalid asset extension"):
                bundle.save_attachment(extension, "<t/>")


class TestAuditReadonlyAsymmetry(TransactionCase):
    def _make_cursor_readonly(self):
        make_cursor_readonly(self)

    def test_save_attachment_ignores_readonly_flag(self):
        bundle = AssetsBundle(
            "test_assetsbundle.audit_ro",
            [asset_file("/test_assetsbundle/static/src/js/audit_ro.js", PLAIN_JS)],
            env=self.env,
            css=False,
        )
        self._make_cursor_readonly()
        attachment = bundle.save_attachment("min.js", "/* ro */")
        self.assertTrue(attachment.exists())


class TestAuditLikeUnderscoreWildcard(TransactionCase):
    FILES = [asset_file("/test_assetsbundle/static/src/js/audit_like.js", PLAIN_JS)]

    def test_sibling_bundle_not_matched(self):
        sibling = AssetsBundle("test.auditXa", self.FILES, env=self.env, css=False)
        sibling.save_attachment("min.js", "/* sibling */")
        bundle = AssetsBundle("test.audit_a", self.FILES, env=self.env, css=False)
        matched = bundle.get_attachments("min.js", ignore_version=True)
        self.assertNotIn("test.auditXa.min.js", matched.mapped("name"))

    def test_clean_attachments_spares_sibling(self):
        sibling_att = AssetsBundle(
            "test.auditXb", self.FILES, env=self.env, css=False
        ).save_attachment("min.js", "/* sibling */")
        self.assertTrue(sibling_att.exists())
        own_att = AssetsBundle(
            "test.audit_b", self.FILES, env=self.env, css=False
        ).save_attachment("min.js", "/* own */")
        self.assertTrue(sibling_att.exists())
        self.assertTrue(own_att.exists())

    def test_ignore_version_returns_only_own(self):
        bundle = AssetsBundle("test.audit_c", self.FILES, env=self.env, css=False)
        bundle.save_attachment("min.js", "/* own */")
        AssetsBundle(
            "test.auditXc", self.FILES, env=self.env, css=False
        ).save_attachment("min.js", "/* sibling */")
        matched = bundle.get_attachments("min.js", ignore_version=True)
        self.assertEqual(matched.mapped("name"), ["test.audit_c.min.js"])
        self.assertEqual(matched.raw, b"/* own */")

    def test_clean_attachments_still_cleans_own_versions(self):
        files_v1 = [
            asset_file("/test_assetsbundle/static/src/js/audit_v.js", PLAIN_JS, 1.0)
        ]
        old_att = AssetsBundle(
            "test.audit_v", files_v1, env=self.env, css=False
        ).save_attachment("min.js", "/* v1 */")
        self.assertTrue(old_att.exists())
        files_v2 = [
            asset_file("/test_assetsbundle/static/src/js/audit_v.js", PLAIN_JS, 2.0)
        ]
        new_att = AssetsBundle(
            "test.audit_v", files_v2, env=self.env, css=False
        ).save_attachment("min.js", "/* v2 */")
        self.assertFalse(old_att.exists())
        self.assertTrue(new_att.exists())


class TestCleanAttachmentsIdentityFilter(TransactionCase):
    def test_rogue_same_url_row_survives_clean(self):
        bundle = AssetsBundle("test_assetsbundle.c2filter", [], env=self.env)
        store = bundle._store
        real = store.save_attachment("min.css", "body{color:red}")
        rogue = self.env["ir.attachment"].create(
            {
                "name": "rogue",
                "type": "binary",
                "raw": b"x",
                "res_model": "ir.attachment",
                "res_id": 0,
                "public": True,
                "url": real.url,
            }
        )
        store._clean_attachments("min.css", keep_id=0)
        self.assertFalse(real.exists(), "the real outdated artifact is GC'd")
        self.assertTrue(rogue.exists(), "the rogue non-ir.ui.view row is left alone")


class TestUnlinkAttachmentsReturning(TransactionCase):
    def test_deleted_rows_drive_file_marks(self):
        attachments = self.env["ir.attachment"].create(
            [
                {
                    "name": f"hardening_{i}.js",
                    "type": "binary",
                    "raw": f"// hardening test {i}".encode(),
                    "res_model": "ir.ui.view",
                    "res_id": 0,
                    "public": True,
                    "url": f"/web/assets/hardeningtest/{i}.js",
                }
                for i in range(2)
            ]
        )
        expected_fnames = set(attachments.mapped("store_fname")) - {False}
        bundle = AssetsBundle("test_assetsbundle.unlink", [], env=self.env)
        with patch.object(IrAttachment, "_mark_for_gc_multi") as file_delete:
            bundle._store._unlink_attachments(attachments)
        marked = {
            fname for call in file_delete.call_args_list for fname in call.args[-1]
        }
        self.assertEqual(marked, expected_fnames)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [("url", "like", "/web/assets/hardeningtest/%")]
            )
        )


class TestSaveKeepsOneRowPerUrl(TransactionCase):
    FILES = [asset_file("/test_assetsbundle/static/src/js/audit_one.js", PLAIN_JS)]

    def test_a_second_save_of_the_same_version_replaces_the_first(self):
        bundle = AssetsBundle("test.audit_one", self.FILES, env=self.env, css=False)
        first = bundle.save_attachment("min.js", "/* first */")
        first_url = first.url
        second = bundle.save_attachment("min.js", "/* second */")

        self.assertEqual(first_url, second.url)
        self.assertFalse(first.exists(), "a same-url twin is superseded, not kept")
        self.assertEqual(
            bundle.get_attachments("min.js", ignore_version=True).ids, [second.id]
        )

    def test_a_debug_build_writes_its_map_once_with_content(self):
        bundle = AssetsBundle(
            "test.audit_map", self.FILES, env=self.env, css=False, debug_assets=True
        )
        with patch.object(
            IrAttachment, "write", autospec=True, side_effect=IrAttachment.write
        ) as write:
            js = bundle.js()
        maps = bundle.get_attachments("js.map", ignore_version=True)

        self.assertEqual(len(maps), 1)
        self.assertEqual(js.url + ".map", maps.url)
        self.assertIn(b'"version"', maps.raw)
        self.assertFalse(
            [c for c in write.call_args_list if "raw" in c.args[1]],
            "the map is created with its content, never written after the fact",
        )


class TestUnlinkAttachmentsLeavesNoCache(TransactionCase):
    def test_a_deleted_row_stops_answering_from_the_cache(self):
        env = self.env
        attachment = env["ir.attachment"].create(
            {
                "name": "cachetest.js",
                "type": "binary",
                "raw": b"// cache " + b"x" * 200,
                "res_model": "ir.ui.view",
                "res_id": 0,
                "public": True,
                "url": "/web/assets/cachetest/cachetest.js",
            }
        )
        self.assertEqual(attachment.name, "cachetest.js")
        store = AssetsBundle("test_assetsbundle.cachetest", [], env=env)._store

        with patch.object(IrAttachment, "_mark_for_gc_multi"):
            store._unlink_attachments(attachment)

        self.assertFalse(attachment.exists())
        with self.assertRaises(MissingError):
            attachment.name


class TestUnlinkAttachmentsSkipLockedPartial(BaseCase):
    URL_PREFIX = "/web/assets/skiplocktest/"

    def setUp(self):
        super().setUp()
        self._cleanup_rows()

    def _cleanup_rows(self):
        with Registry(get_db_name()).cursor() as cr:
            cr.execute(
                "DELETE FROM ir_attachment WHERE url LIKE %s", (self.URL_PREFIX + "%",)
            )
            cr.commit()

    def test_locked_row_survives_and_is_not_marked(self):
        db = get_db_name()
        reg = Registry(db)
        ids = []
        locker = None
        try:
            with reg.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                atts = env["ir.attachment"].create(
                    [
                        {
                            "name": f"skiplock_{i}.js",
                            "type": "binary",
                            "raw": (f"// skip locked {i} " + "x" * 200).encode(),
                            "res_model": "ir.ui.view",
                            "res_id": 0,
                            "public": True,
                            "url": f"/web/assets/skiplocktest/{i}.js",
                        }
                        for i in range(2)
                    ]
                )
                env.flush_all()
                ids = atts.ids
                fname_by_id = {a.id: a.store_fname for a in atts}
                cr.commit()
            self.assertTrue(
                all(fname_by_id.values()), "fixture rows must use the filestore"
            )
            locked_id, free_id = ids[0], ids[1]

            locker = db_connect(db).cursor()
            locker.execute("SET lock_timeout = '2000ms'")
            locker.execute(
                "SELECT id FROM ir_attachment WHERE id = %s FOR NO KEY UPDATE",
                (locked_id,),
            )

            with reg.cursor() as cr:
                cr.execute("SET lock_timeout = '3000ms'")
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = AssetsBundle("test_assetsbundle.skiplock", [], env=env)._store
                attachments = env["ir.attachment"].browse(ids)
                with patch.object(IrAttachment, "_mark_for_gc_multi") as file_delete:
                    store._unlink_attachments(attachments)
                marked = {
                    fname
                    for call in file_delete.call_args_list
                    for fname in call.args[-1]
                }
                cr.commit()

            self.assertEqual(
                marked,
                {fname_by_id[free_id]},
                "only the row SKIP LOCKED actually deleted may be filestore-marked",
            )
            with reg.cursor() as cr:
                cr.execute("SELECT id FROM ir_attachment WHERE id = ANY(%s)", (ids,))
                survivors = {r[0] for r in cr.fetchall()}
            self.assertEqual(
                survivors, {locked_id}, "the locked row must survive SKIP LOCKED"
            )
        finally:
            if locker is not None:
                locker.connection.rollback()
                locker.close()
            if ids:
                with reg.cursor() as cr:
                    cr.execute("DELETE FROM ir_attachment WHERE id = ANY(%s)", (ids,))
                    cr.commit()


class TestChecksumSeparator(TransactionCase):
    def test_pipeline_change_invalidates_the_version(self):
        spec = [asset_file("/a.css", "a{}", 1.0)]
        before = AssetsBundle("test.fp", spec, env=self.env).get_version("css")
        with patch.object(
            bundle_module, "_pipeline_fingerprint", return_value="pretend-new-code"
        ):
            after = AssetsBundle("test.fp", spec, env=self.env).get_version("css")
        self.assertNotEqual(before, after)

    def test_the_superseded_attachment_is_not_left_behind(self):
        name = "test.supersede"
        spec = [asset_file("/mod/static/src/a.css", "a{color:red}")]

        def urls():
            return set(
                self.env["ir.attachment"]
                .sudo()
                .search([("name", "=like", f"{name}%")])
                .mapped("url")
            )

        with patch.object(
            bundle_module, "_pipeline_fingerprint", return_value="previous-code"
        ):
            AssetsBundle(name, spec, env=self.env).css()
        before = urls()
        self.assertEqual(len(before), 1)

        served = AssetsBundle(name, spec, env=self.env).css()
        after = urls()

        self.assertEqual(len(after), 1, "exactly one version survives")
        self.assertEqual(after, {served.url})
        self.assertFalse(before & after, "the superseded row was deleted")

    def test_fingerprint_is_stable_within_a_release(self):
        _pipeline_fingerprint.cache_clear()
        first = _pipeline_fingerprint()
        _pipeline_fingerprint.cache_clear()
        self.assertEqual(first, _pipeline_fingerprint())
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_ambiguous_split_is_not_a_collision(self):
        two = AssetsBundle(
            "test.sep",
            [asset_file("/a.js", "//a", 1.0), asset_file("/b.js", "//b", 2.0)],
            env=self.env,
        )
        one = AssetsBundle(
            "test.sep",
            [asset_file("/a.js,1.0/b.js", "//ab", 2.0)],
            env=self.env,
        )
        self.assertEqual(
            "".join(a.unique_descriptor for a in two.javascripts),
            "".join(a.unique_descriptor for a in one.javascripts),
            "precondition: the descriptors concatenate to the same string",
        )
        self.assertNotEqual(two.get_version("js"), one.get_version("js"))


class TestAuditEpochMtime(TransactionCase):
    def _tmp_js(self, mtime):
        fd, path = tempfile.mkstemp(suffix=".js")
        with os.fdopen(fd, "w") as handle:
            handle.write(PLAIN_JS)
        self.addCleanup(os.unlink, path)
        os.utime(path, (mtime, mtime))
        return path

    def _asset(self, filename):
        bundle = AssetsBundle("test_assetsbundle.audit_mtime", [], env=self.env)
        return JavascriptAsset(bundle, url="/test/audit_mtime.js", filename=filename)

    def test_epoch_zero_is_preserved(self):
        asset = self._asset(self._tmp_js(0))
        self.assertEqual(asset.last_modified, 0.0)

    def test_nonzero_mtime_passes_through(self):
        path = self._tmp_js(1234)
        asset = self._asset(path)
        self.assertEqual(asset.last_modified, Path(path).stat().st_mtime)


class TestLastModifiedFallback(TransactionCase):
    def test_missing_mtime_stats_file(self):
        bundle = AssetsBundle("test_assetsbundle.mtime", [], env=self.env)
        asset = JavascriptAsset(
            bundle,
            url="/web/static/src/module_loader.js",
            filename=file_path("web/static/src/module_loader.js"),
        )
        self.assertGreater(asset.last_modified, 0)

    def test_missing_file_keeps_sentinel(self):
        bundle = AssetsBundle("test_assetsbundle.mtime2", [], env=self.env)
        asset = JavascriptAsset(
            bundle,
            url="/web/static/src/gone.js",
            filename="/nonexistent/definitely_gone.js",
        )
        self.assertEqual(asset.last_modified, -1)


class TestEsmAttachmentSidecars(TransactionCase):
    def _att(self, url):
        return (
            self.env["ir.attachment"]
            .sudo()
            .search([("url", "=", url), ("public", "=", True)])
        )

    def test_main_bundle_save_writes_both_sidecars(self):
        url = self.env["ir.qweb"]._save_esm_attachment(
            "test_assetsbundle.sidecar_main",
            "export const main = 1;\n//# sourceMappingURL=x.map",
            metafile='{"inputs":{}}',
            sourcemap='{"version":3}',
        )
        self.assertTrue(url.endswith(".esm.js"))
        self.assertTrue(self._att(url), "the main bundle attachment must exist")
        meta_url = url[: -len(".esm.js")] + ".meta.json"
        self.assertTrue(self._att(meta_url), "metafile sidecar must be persisted")
        self.assertTrue(self._att(url + ".map"), "sourcemap sidecar must be persisted")

    def test_template_save_writes_no_sidecars(self):
        url = self.env["ir.qweb"]._save_esm_attachment(
            "test_assetsbundle.sidecar_tpl.templates",
            "export const tpl = 2;",
        )
        self.assertTrue(self._att(url), "the templates attachment must exist")
        meta_url = url[: -len(".esm.js")] + ".meta.json"
        self.assertFalse(self._att(meta_url), "no metafile sidecar without a metafile")
        self.assertFalse(self._att(url + ".map"), "no sourcemap sidecar without one")


class TestLikePatternHasOneSpelling(TransactionCase):
    def test_the_two_sides_build_the_same_pattern(self):
        store = AssetAttachmentStore(
            self.env,
            "web.assets_web",
            assets_params={},
            rtl=False,
            autoprefix=False,
            version_provider=lambda _t: ANY_UNIQUE,
        )
        writer = store.get_asset_url_pattern(extension="min.css")
        reader = self.env["ir.asset"]._get_asset_bundle_url_pattern(
            "web.assets_web.min.css", ANY_UNIQUE, {}
        )
        self.assertEqual(writer, reader)

    def test_the_reader_pattern_does_not_match_a_near_miss(self):
        canonical = "/web/assets/abc1234/web.assets_web.min.css"
        near_miss = "/web/assets/abc1234/web.assetsXweb.min.css"
        pattern = self.env["ir.asset"]._get_asset_bundle_url_pattern(
            "web.assets_web.min.css", "abc1234", {}
        )
        self.env.cr.execute(
            "SELECT %s LIKE %s, %s LIKE %s",
            [canonical, pattern, near_miss, pattern],
        )
        matches_canonical, matches_near_miss = self.env.cr.fetchone()
        self.assertTrue(matches_canonical)
        self.assertFalse(matches_near_miss, "an unescaped `_` is a LIKE wildcard")


class TestEsmAssetGc(TransactionCase):
    def _mk(self, name: str, url: str, days_old: int = 0):
        att = (
            self.env["ir.attachment"]
            .with_user(SUPERUSER_ID)
            .create(
                {
                    "name": name,
                    "url": url,
                    "type": "binary",
                    "public": True,
                    "res_model": "ir.ui.view",
                    "res_id": False,
                    "raw": b"/* gc probe */",
                    "mimetype": "text/javascript",
                }
            )
        )
        if days_old:
            self.env.cr.execute(
                "UPDATE ir_attachment"
                " SET write_date = write_date - %s::interval,"
                "     create_date = create_date - %s::interval"
                " WHERE id = %s",
                [f"{days_old} days", f"{days_old} days", att.id],
            )
            att.invalidate_recordset()
        return att

    def test_superseded_version_and_sidecar_are_gcd(self):
        old_v1 = self._mk("x.gcb.esm.js", "/web/assets/esm/aaaa/x.gcb.esm.js", 30)
        old_map = self._mk(
            "x.gcb.esm.js.map", "/web/assets/esm/aaaa/x.gcb.esm.js.map", 30
        )
        new_v2 = self._mk("x.gcb.esm.js", "/web/assets/esm/bbbb/x.gcb.esm.js")
        new_map = self._mk("x.gcb.esm.js.map", "/web/assets/esm/bbbb/x.gcb.esm.js.map")

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertFalse(old_v1.exists(), "superseded old version must be GC'd")
        self.assertFalse(old_map.exists(), "superseded old sidecar must be GC'd")
        self.assertTrue(new_v2.exists(), "current version must survive")
        self.assertTrue(new_map.exists(), "current sidecar must survive")

    def test_lone_old_survives_with_no_newer_sibling(self):
        lone_old = self._mk("y.gcb.esm.js", "/web/assets/esm/cccc/y.gcb.esm.js", 400)

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertTrue(lone_old.exists(), "newest-per-name survives any age")

    def test_recent_survives_the_grace_window(self):
        recent_old = self._mk("z.gcb.esm.js", "/web/assets/esm/dddd/z.gcb.esm.js", 2)
        recent_new = self._mk("z.gcb.esm.js", "/web/assets/esm/eeee/z.gcb.esm.js")

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertTrue(recent_old.exists(), "within grace window — survives")
        self.assertTrue(recent_new.exists())

    def test_bridge_past_its_own_grace_is_gcd(self):
        bridge_old = self._mk(
            "aabbccddeeff0011.js", "/web/assets/esm/bridges/aabbccddeeff0011.js", 400
        )

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertFalse(
            bridge_old.exists(),
            "a bridge past its own (much longer) grace must still be GC'd",
        )

    def test_bridge_older_than_artifact_grace_survives(self):
        bridge_mid = self._mk(
            "33445566778899aa.js", "/web/assets/esm/bridges/33445566778899aa.js", 30
        )

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertTrue(
            bridge_mid.exists(),
            "a bridge older than the ARTIFACT grace survives: shims are tiny "
            "(23 rows = 13 kB measured) and content-addressed with no supersession, "
            "so collecting them on the artifact clock deleted live rows for nothing",
        )

    def test_young_bridge_survives(self):
        bridge_new = self._mk(
            "1100ffeeddccbbaa.js", "/web/assets/esm/bridges/1100ffeeddccbbaa.js", 1
        )

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertTrue(bridge_new.exists(), "young bridge survives")

    def test_classic_bundle_out_of_scope(self):
        classic = self._mk("x.gcb.min.js", "/web/assets/0123456/x.gcb.min.js", 400)

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertTrue(classic.exists(), "classic bundles are out of scope")

    def test_a_bridge_still_in_use_is_refreshed_before_it_can_age_out(self):
        from odoo.tools.assets.esm_bridges import BridgeShimManager

        digest = "beef" * 8
        url = f"/web/assets/esm/bridges/{digest}.js"
        aged = self._mk(f"{digest}.js", url, 6)
        before = aged.write_date

        manager = BridgeShimManager(self.env, "test_assetsbundle.gc_probe", [])
        with patch("odoo.tools.assets.esm_bridges.cache_hash", return_value=digest):
            manager._persist_bridge_shims({"@probe/spec": "export const p = 1;\n"})
        aged.invalidate_recordset(["write_date"])

        self.assertGreater(
            aged.write_date,
            before,
            "reusing a shim must push its write_date forward, or the vacuum eats it",
        )
        self.env["ir.attachment"]._gc_esm_assets()
        self.assertTrue(aged.exists(), "a refreshed shim must survive the vacuum")

    def test_a_young_shim_is_not_rewritten_on_every_reuse(self):
        from odoo.tools.assets.esm_bridges import BridgeShimManager

        digest = "cafe" * 8
        url = f"/web/assets/esm/bridges/{digest}.js"
        young = self._mk(f"{digest}.js", url)
        before = young.write_date
        manager = BridgeShimManager(self.env, "test_assetsbundle.gc_probe", [])
        with patch("odoo.tools.assets.esm_bridges.cache_hash", return_value=digest):
            manager._persist_bridge_shims({"@probe/spec": "export const p = 1;\n"})
        young.invalidate_recordset(["write_date"])
        self.assertEqual(young.write_date, before)

    def test_the_refresh_is_skipped_rather_than_raised_when_read_only(self):
        from odoo.tools.assets.esm_bridges import BridgeShimManager

        digest = "deed" * 8
        aged = self._mk(f"{digest}.js", f"/web/assets/esm/bridges/{digest}.js", 6)
        before = aged.write_date
        make_cursor_readonly(self)
        manager = BridgeShimManager(self.env, "test_assetsbundle.gc_probe", [])
        with patch("odoo.tools.assets.esm_bridges.cache_hash", return_value=digest):
            manager._persist_bridge_shims({"@probe/spec": "export const p = 1;\n"})
        aged.invalidate_recordset(["write_date"])
        self.assertEqual(aged.write_date, before)

    def test_the_bridge_grace_is_separately_configurable(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.esm.bridge_gc_grace_days", "10"
        )
        old = self._mk(
            "99887766554433aa.js", "/web/assets/esm/bridges/99887766554433aa.js", 20
        )
        young = self._mk(
            "aa334455667788bb.js", "/web/assets/esm/bridges/aa334455667788bb.js", 5
        )
        self.env["ir.attachment"]._gc_esm_assets()
        self.assertFalse(old.exists())
        self.assertTrue(young.exists())

    def test_gc_grace_window_configurable(self):
        self.env["ir.config_parameter"].sudo().set_param("web.esm.gc_grace_days", "60")
        bridge = self._mk(
            "22334455667788aa.js", "/web/assets/esm/bridges/22334455667788aa.js", 30
        )
        self.env["ir.attachment"]._gc_esm_assets()
        self.assertTrue(
            bridge.exists(), "30-day-old bridge survives a 60-day grace window"
        )

    def test_gc_phantom_non_superuser_row(self):
        stable = self._mk("p.gcb.esm.js", "/web/assets/esm/aaaa/p.gcb.esm.js", 400)
        admin = self.env.ref("base.user_admin")
        self.assertNotEqual(admin.id, SUPERUSER_ID, "phantom must not be superuser")
        phantom = (
            self.env["ir.attachment"]
            .with_user(admin)
            .create(
                {
                    "name": "p.gcb.esm.js",
                    "url": "/web/assets/esm/bbbb/p.gcb.esm.js",
                    "type": "binary",
                    "public": True,
                    "res_model": "ir.ui.view",
                    "res_id": False,
                    "raw": b"/* phantom */",
                    "mimetype": "text/javascript",
                }
            )
        )
        self.assertGreater(phantom.id, stable.id, "phantom must have the higher id")

        self.env["ir.attachment"]._gc_esm_assets()

        self.assertTrue(
            stable.exists(),
            "the genuine stable bundle must survive a non-superuser phantom",
        )

    def test_gc_grace_floor(self):
        self.env["ir.config_parameter"].sudo().set_param("web.esm.gc_grace_days", "0")
        fresh = self._mk(
            "0011223344556677.js", "/web/assets/esm/bridges/0011223344556677.js"
        )
        self.env["ir.attachment"]._gc_esm_assets()
        self.assertTrue(
            fresh.exists(), "a fresh bridge survives grace_days=0 (floored to 1)"
        )


@tagged("post_install", "-at_install")
class TestBundleChangedBroadcastDedup(TransactionCase):
    def setUp(self):
        super().setUp()
        if "bus.bus" not in self.env:
            self.skipTest("bus not installed")
        self.sent = []
        real = type(self.env["bus.bus"])._sendone

        def spy(bus, channel, notification_type, message):
            if notification_type == "bundle_changed":
                self.sent.append(channel)
            return real(bus, channel, notification_type, message)

        self.patch(type(self.env["bus.bus"]), "_sendone", spy)
        AssetAttachmentStore.register_tracked_bundle("test.audit.bcast")
        self.addCleanup(
            AssetAttachmentStore.TRACKED_BUNDLES.discard, "test.audit.bcast"
        )

    def _bundle(self, **kw):
        return AssetsBundle(
            "test.audit.bcast",
            [
                asset_file("/m/a.js", "var a = 1;"),
                asset_file("/m/a.css", ".a{color:red}"),
            ],
            env=self.env,
            **kw,
        )

    def test_a_debug_rebuild_broadcasts_once_not_per_artifact(self):
        self._bundle(debug_assets=True).js()
        self.assertEqual(len(self.sent), 1, self.sent)

    def test_css_and_js_of_one_build_share_the_single_notification(self):
        bundle = self._bundle(debug_assets=True)
        bundle.js()
        bundle.css()
        self.assertEqual(len(self.sent), 1, self.sent)

    def test_an_untracked_bundle_stays_silent(self):
        AssetsBundle(
            "test.audit.untracked",
            [asset_file("/m/a.css", ".a{color:red}")],
            env=self.env,
        ).css()
        self.assertEqual(self.sent, [])

    def test_the_guard_is_scoped_to_the_transaction(self):
        self._bundle(debug_assets=True).js()
        self.assertEqual(len(self.sent), 1)
        self.env.cr.precommit.data.pop(AssetAttachmentStore._BROADCAST_KEY, None)
        self._bundle().js()
        self.assertEqual(len(self.sent), 2)
