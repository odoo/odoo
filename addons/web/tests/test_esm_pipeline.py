import contextlib
import json
import logging
import posixpath
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from psycopg.errors import ReadOnlySqlTransaction

import odoo
from odoo.api import SUPERUSER_ID
from odoo.db import db_connect
from odoo.fields import Domain
from odoo.libs.asset_log import ASSET_ROOT, get_asset_logger, log_event
from odoo.libs.hashing import cache_hash
from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools.assets import esbuild_process, esm_bridges
from odoo.tools.assets.esbuild import EsbuildCompiler, EsbuildResult
from odoo.tools.assets.esm_graph import (
    _IMPORT_ANY_RE,
    _bridge_shim_source,
    _BridgeExportResolver,
    _get_import_specifiers,
    discover_transitive_import_specifiers,
)
from odoo.tools.assets.esm_lexer import lex_module
from odoo.tools.assets.esm_libs import (
    LIB_URL_PREFIX,
    lib_closure,
    lib_unique,
    served_external_libs,
    served_lib_files,
)
from odoo.tools.assets.esm_registry import (
    EsmRegistry,
    esm_registry,
    external_libs,
)
from odoo.tools.misc import file_path

from odoo.addons.base.models import ir_qweb_assets
from odoo.addons.base.models.assetsbundle import AssetsBundle, _parse_odoo_module_header
from odoo.addons.base.models.ir_qweb_assets import (
    _BuildDeclined,
    _EsmFallbackError,
    _EsmReadonlyDeclined,
    _StandaloneBundleDeclined,
)


@tagged("web_unit", "web_assets")
class TestAssetLogHelper(TransactionCase):
    def test_logger_name_under_asset_root(self):
        log = get_asset_logger("esbuild")
        self.assertEqual(log.name, f"{ASSET_ROOT}.esbuild")
        self.assertEqual(get_asset_logger("").name, ASSET_ROOT)

    def test_log_event_format(self):
        log = get_asset_logger("testcat")
        with self.assertLogs(log.name, level=logging.DEBUG) as captured:
            log_event(
                log,
                logging.DEBUG,
                "started",
                bundle="web.assets_web",
                modules=42,
            )
        self.assertEqual(len(captured.records), 1)
        msg = captured.records[0].getMessage()
        self.assertEqual(msg, "event=started bundle=web.assets_web modules=42")

    def test_log_event_suppressed_below_level(self):
        log = get_asset_logger("quiet")
        log.setLevel(logging.WARNING)
        with patch.object(log, "log") as mocked_log:
            log_event(log, logging.DEBUG, "skipped", k="v")
        mocked_log.assert_not_called()


@tagged("web_unit", "web_assets")
class TestEsbuildCircuitBreaker(TransactionCase):
    def setUp(self):
        super().setUp()
        self.IrQweb = self.env["ir.qweb"]
        self.addCleanup(
            self.IrQweb._esbuild_circuit.restore,
            self.IrQweb._esbuild_circuit.snapshot(),
        )
        self.IrQweb._esbuild_circuit.clear()

    def test_initial_state_allows(self):
        allow, reason = self.IrQweb._get_esbuild_circuit_state("web.test_bundle")
        self.assertTrue(allow)
        self.assertEqual(reason, "")

    def test_first_failure_opens_circuit(self):
        with self.assertLogs(
            f"{ASSET_ROOT}.fallback", level=logging.WARNING
        ) as captured:
            self.IrQweb._open_esbuild_circuit(
                "web.test_bundle",
                reason="SubprocessError",
            )
        self.assertEqual(len(captured.records), 1)
        self.assertIn("event=circuit_open", captured.records[0].getMessage())
        self.assertIn("reason=SubprocessError", captured.records[0].getMessage())
        allow, reason = self.IrQweb._get_esbuild_circuit_state("web.test_bundle")
        self.assertFalse(allow)
        self.assertEqual(reason, "SubprocessError")

    def test_second_consecutive_failure_escalates_cooldown(self):
        with self.assertLogs(
            f"{ASSET_ROOT}.fallback", level=logging.WARNING
        ) as captured:
            self.IrQweb._open_esbuild_circuit(
                "web.test_bundle",
                reason="Err1",
            )
            self.IrQweb._open_esbuild_circuit(
                "web.test_bundle",
                reason="Err2",
            )
        self.assertEqual(len(captured.records), 2)
        self.assertIn("fails=1", captured.records[0].getMessage())
        self.assertIn("fails=2", captured.records[1].getMessage())
        entry = self.IrQweb._esbuild_circuit.entry(
            (self.env.cr.dbname, "web.test_bundle")
        )
        self.assertEqual(entry.failures, 2)
        remaining = entry.expiry - time.monotonic()
        self.assertGreater(
            remaining,
            self.IrQweb._ESBUILD_COOLDOWN_S,
            msg="2nd failure should escalate past the base cooldown",
        )

    def test_success_clears_the_circuit(self):
        with self.assertLogs(
            f"{ASSET_ROOT}.fallback", level=logging.WARNING
        ) as captured:
            self.IrQweb._open_esbuild_circuit(
                "web.test_bundle",
                reason="OnceFailed",
            )
            self.IrQweb._close_esbuild_circuit("web.test_bundle")
        self.assertEqual(len(captured.records), 1)
        self.assertIn("event=circuit_open", captured.records[0].getMessage())
        self.assertNotIn(
            (self.env.cr.dbname, "web.test_bundle"),
            self.IrQweb._esbuild_circuit,
        )
        allow, _ = self.IrQweb._get_esbuild_circuit_state("web.test_bundle")
        self.assertTrue(allow)

    def test_circuit_key_is_database_scoped(self):
        with self.assertLogs(f"{ASSET_ROOT}.fallback", level=logging.WARNING):
            self.IrQweb._open_esbuild_circuit(
                "web.test_bundle",
                reason="ScopeCheck",
            )
        self.assertIn(
            (self.env.cr.dbname, "web.test_bundle"),
            self.IrQweb._esbuild_circuit,
            msg="cooldown key must be (db_name, bundle)",
        )
        self.assertNotIn(
            "web.test_bundle",
            self.IrQweb._esbuild_circuit,
            msg="bundle-only key would bleed the breaker across databases",
        )
        self.IrQweb._esbuild_circuit.record_failure(
            ("some_other_db", "web.test_bundle"),
            "OtherDbFail",
            now=time.monotonic(),
            cooldown_s=1e6,
            extended_cooldown_s=1e6,
        )
        allow, reason = self.IrQweb._get_esbuild_circuit_state("web.test_bundle")
        self.assertFalse(
            allow,
            msg="this db's own failure should still gate it",
        )
        self.assertEqual(reason, "ScopeCheck")


@tagged("web_unit", "web_assets")
class TestEsbuildAdvisoryLock(TransactionCase):
    def test_contender_waits_past_the_old_fallback_deadline(self):
        qweb = self.env["ir.qweb"]
        db = db_connect(self.env.cr.dbname)
        ready = threading.Event()
        finished = threading.Event()
        errors = []
        pids = []

        def contend():
            try:
                with db.cursor() as cr:
                    cr.execute("SET LOCAL lock_timeout = '5s'")
                    cr.execute("SELECT pg_backend_pid()")
                    pids.append(cr.fetchone()[0])
                    ready.set()
                    qweb._acquire_esbuild_lock("test.lock.wait", cr=cr)
            except Exception as exc:
                errors.append(exc)
            finally:
                finished.set()

        with self.assertLogs(f"{ASSET_ROOT}.lock", level=logging.DEBUG) as logged:
            with db.cursor() as holder:
                qweb._acquire_esbuild_lock("test.lock.wait", cr=holder)
                contender = threading.Thread(target=contend)
                contender.start()
                try:
                    self.assertTrue(ready.wait(2), "contender did not connect")
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        holder.execute(
                            "SELECT count(*) FROM pg_locks "
                            "WHERE pid = %s AND locktype = 'advisory' AND NOT granted",
                            (pids[0],),
                        )
                        if holder.fetchone()[0]:
                            break
                        time.sleep(0.01)
                    else:
                        self.fail("PostgreSQL never observed the contender waiting")
                    self.assertFalse(
                        finished.wait(0.3), "contention must not decline compilation"
                    )
                finally:
                    holder.rollback()
                    contender.join(6)
            self.assertFalse(contender.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(finished.is_set())
        self.assertEqual(sum("event=acquired" in line for line in logged.output), 2)

    def test_lock_acquired_in_own_cursor(self):
        IrQweb = self.env["ir.qweb"]
        IrQweb._acquire_esbuild_lock("test.lock.alpha")

    def test_lock_rejects_other_cursor_while_held(self):
        IrQweb = self.env["ir.qweb"]
        IrQweb._acquire_esbuild_lock("test.lock.beta")
        with db_connect(self.env.cr.dbname).cursor() as cr2:
            cr2.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                ("esbuild:test.lock.beta",),
            )
            got = cr2.fetchone()[0]
        self.assertFalse(
            got,
            msg="sibling cursor must not acquire lock while self.env.cr holds it",
        )

    def test_lock_released_on_commit(self):
        dbname = self.env.cr.dbname
        key = "esbuild:test.lock.gamma"

        with db_connect(dbname).cursor() as cr_a:
            cr_a.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                (key,),
            )
            self.assertTrue(cr_a.fetchone()[0])
            cr_a.commit()

        with db_connect(dbname).cursor() as cr_b:
            cr_b.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                (key,),
            )
            got = cr_b.fetchone()[0]
            cr_b.commit()
        self.assertTrue(got, msg="lock must release at transaction commit")


@tagged("web_unit", "web_assets")
class TestContentAddressableUrl(TransactionCase):
    def test_identical_content_produces_identical_url(self):
        ir_qweb = self.env["ir.qweb"]
        content = "export const x = 1;"
        url1 = ir_qweb._save_esm_attachment("test.cas.same", content)
        url2 = ir_qweb._save_esm_attachment("test.cas.same", content)
        self.assertEqual(url1, url2)
        self.assertRegex(
            url1,
            r"^/web/assets/esm/[0-9a-f]{16}/test\.cas\.same\.esm\.js$",
            msg="URL must match content-addressable scheme",
        )

    def test_different_content_produces_different_url(self):
        ir_qweb = self.env["ir.qweb"]
        url_a = ir_qweb._save_esm_attachment(
            "test.cas.diff",
            "export const x = 1;",
        )
        url_b = ir_qweb._save_esm_attachment(
            "test.cas.diff",
            "export const x = 2;",
        )
        self.assertNotEqual(url_a, url_b)
        Attachment = self.env["ir.attachment"].sudo()
        attachments = Attachment.search(
            [
                ("url", "=like", "/web/assets/esm/%/test.cas.diff.esm.js"),
            ]
        )
        self.assertEqual(
            len(attachments),
            2,
            msg="superseded version must survive the rebuild (deferred GC)",
        )
        old_row = attachments.filtered(lambda a: a.url == url_a)
        self.env.cr.execute(
            "UPDATE ir_attachment SET write_date = write_date - interval '30 days'"
            " WHERE id = %s",
            [old_row.id],
        )
        old_row.invalidate_recordset()
        Attachment._gc_esm_assets()
        remaining = Attachment.search(
            [
                ("url", "=like", "/web/assets/esm/%/test.cas.diff.esm.js"),
            ]
        )
        self.assertEqual(remaining.mapped("url"), [url_b])


@tagged("web_unit", "web_assets")
class TestMetafileSidecar(TransactionCase):
    def test_metafile_saved_as_sibling_when_present(self):
        ir_qweb = self.env["ir.qweb"]
        url = ir_qweb._save_esm_attachment(
            "test.meta.present",
            "/* bundle */",
            metafile=json.dumps({"inputs": {}, "outputs": {}}),
        )
        meta_url = url[: -len(".esm.js")] + ".meta.json"
        meta = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("url", "=", meta_url),
                    ("public", "=", True),
                ],
                limit=1,
            )
        )
        self.assertTrue(meta, msg="sibling metafile attachment must exist")
        self.assertEqual(meta.mimetype, "application/json")
        parsed = json.loads(meta.raw)
        self.assertIn("inputs", parsed)
        self.assertIn("outputs", parsed)

    def test_metafile_absent_when_esbuild_did_not_run(self):
        ir_qweb = self.env["ir.qweb"]
        url = ir_qweb._save_esm_attachment(
            "test.meta.absent",
            "/* bundle */",
        )
        meta_url = url[: -len(".esm.js")] + ".meta.json"
        meta = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("url", "=", meta_url),
                ],
                limit=1,
            )
        )
        self.assertFalse(
            meta,
            msg="no metafile should be created when _last_metafile is None",
        )


@tagged("web_unit", "web_assets")
class TestGeneratedAssetsAreCollectable(TransactionCase):
    def _row_for(self, url, create):
        attachment = create(
            {
                "name": url.rsplit("/", 1)[-1],
                "mimetype": "text/javascript",
                "res_model": "ir.ui.view",
                "res_id": False,
                "type": "binary",
                "public": True,
                "raw": b"export default 1;",
                "url": url,
            }
        )
        Attachment = self.env["ir.attachment"]
        domain = Attachment._get_domain_generated_assets()
        return attachment, bool(
            Attachment.sudo().search(domain & Domain("id", "=", attachment.id))
        )

    def test_sudo_alone_leaves_an_uncollectable_row(self):
        env = self.env(user=self.env.ref("base.user_admin").id)
        attachment, collectable = self._row_for(
            "/web/assets/esm/bridges/probe_sudo.js",
            env["ir.attachment"].sudo().create,
        )
        self.assertNotEqual(attachment.create_uid.id, SUPERUSER_ID)
        self.assertFalse(collectable)

    def test_with_user_superuser_is_collectable(self):
        env = self.env(user=self.env.ref("base.user_admin").id)
        attachment, collectable = self._row_for(
            "/web/assets/esm/bridges/probe_superuser.js",
            env["ir.attachment"].with_user(SUPERUSER_ID).create,
        )
        self.assertEqual(attachment.create_uid.id, SUPERUSER_ID)
        self.assertTrue(collectable)

    def test_the_bridge_writer_uses_the_collectable_form(self):
        source = Path(esm_bridges.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"ir.attachment"].sudo().create', source)
        self.assertIn('"ir.attachment"].with_user(SUPERUSER_ID).create', source)


@tagged("web_unit", "web_assets")
class TestParentSelfBridge(TransactionCase):
    def test_parent_self_bridge_covers_native_modules(self):
        setup_ab = self.env["ir.qweb"]._get_asset_bundle(
            "web.assets_unit_tests_setup",
            js=True,
            css=False,
        )
        bridges = setup_ab._bridges._prepare_parent_self_bridge()
        native_specs = {a.module_path for a in setup_ab.native_modules}
        self.assertGreater(len(bridges), 0)
        for spec, url in list(bridges.items())[:20]:
            self.assertIn(spec, native_specs)
            self.assertTrue(
                url.startswith("/web/assets/esm/bridges/"),
                msg=f"bridge for {spec} is not an attachment URL: {url[:80]}",
            )
            self.assertRegex(url, r"^/web/assets/esm/bridges/[0-9a-f]{32}\.js$")

    def test_prod_import_map_bridges_parent_specifiers(self):
        self.env["ir.attachment"].sudo().search(
            [
                ("url", "=like", "/web/assets/esm/%/web.assets_unit_tests_setup%"),
            ]
        ).unlink()
        setup_ab = self.env["ir.qweb"]._get_asset_bundle(
            "web.assets_unit_tests_setup",
            js=True,
            css=False,
        )
        sample_spec = next(
            a.module_path
            for a in setup_ab.native_modules
            if a.module_path.startswith("@web/")
        )

        pre, _post = self.env["ir.qweb"]._get_native_module_nodes(
            "web.assets_unit_tests_setup",
            debug=False,
        )
        import_map = None
        for _tag, attrs in pre:
            if attrs.get("type") == "importmap":
                import_map = json.loads(attrs["text"])["imports"]
                break
        self.assertIsNotNone(import_map, "prod must emit an import map")
        self.assertIn(
            sample_spec,
            import_map,
            msg=(
                f"expected parent-self bridge for {sample_spec!r}; "
                f"map size={len(import_map)}, "
                f"@web/* count={sum(1 for s in import_map if s.startswith('@web/'))}"
            ),
        )


@tagged("web_unit", "web_assets")
class TestPipelineIntegration(TransactionCase):
    def test_admin_override_skips_esbuild(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.esbuild.force_fallback_bundles",
            "web.assets_web",
        )
        self.addCleanup(
            self.env["ir.config_parameter"].sudo().set_param,
            "web.esbuild.force_fallback_bundles",
            "",
        )

        called = []
        original = AssetsBundle.esbuild_native_bundle

        def _spy(self, *args, **kwargs):
            called.append(self.name)
            return original(self, *args, **kwargs)

        with patch.object(AssetsBundle, "esbuild_native_bundle", _spy):
            self.env["ir.qweb"]._get_asset_nodes(
                "web.assets_web",
                css=False,
                js=True,
            )
        self.assertNotIn(
            "web.assets_web",
            called,
            msg="admin override must bypass the esbuild subprocess",
        )

    def test_unavailable_lock_cursor_falls_through_to_debug_nodes(self):
        ir_qweb = self.env["ir.qweb"]
        with patch.object(
            type(ir_qweb),
            "_get_esbuild_lock_cursor",
            side_effect=lambda *_a: contextlib.nullcontext(None),
        ):
            self.env["ir.attachment"].sudo().search(
                [
                    ("url", "=like", "/web/assets/esm/%/web.assets_web%"),
                ]
            ).unlink()
            nodes = ir_qweb._get_asset_nodes(
                "web.assets_web",
                css=False,
                js=True,
            )
        self.assertTrue(nodes, msg="fallback must still produce nodes")
        tags = {tag for tag, _attrs in nodes}
        self.assertIn("script", tags)
        importmaps = [
            attrs
            for tag, attrs in nodes
            if tag == "script" and attrs.get("type") == "importmap"
        ]
        self.assertTrue(
            importmaps,
            msg="debug-mode fallback must emit an importmap",
        )

    def test_request_bound_debug_bundle_keeps_importmap(self):
        from odoo.addons.base.models import ir_qweb_assets

        ir_qweb = self.env["ir.qweb"]

        def importmaps(nodes):
            return [
                attrs
                for tag, attrs in nodes
                if tag == "script" and attrs.get("type") == "importmap"
            ]

        fake_request = SimpleNamespace()
        with patch.object(ir_qweb_assets, "request", fake_request):
            first = ir_qweb._get_asset_nodes(
                "web.assets_web", css=False, js=True, debug="assets", page=True
            )
            second = ir_qweb._get_asset_nodes(
                "web.assets_web", css=False, js=True, debug="assets", page=True
            )

        self.assertEqual(
            len(importmaps(first)),
            1,
            msg="first request-bound debug bundle must emit exactly one importmap",
        )
        self.assertEqual(
            len(importmaps(second)),
            0,
            msg="second bundle on the same request must be deduped (no importmap)",
        )


@tagged("web_unit", "web_assets")
class TestEsbuildIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        odoo_root = Path(odoo.__path__[0]).parent
        cls.esbuild = shutil.which("esbuild") or shutil.which(
            "esbuild",
            path=str(odoo_root / "node_modules" / ".bin"),
        )

    def setUp(self):
        super().setUp()
        if not self.esbuild:
            self.skipTest(
                "esbuild binary not found. Run 'npm install' in the Odoo root "
                "to enable this integration test.",
            )

    def test_emoji_bundle_compiles(self):
        IrQweb = self.env["ir.qweb"]
        assets_params = self.env["ir.asset"]._prepare_assets_params()
        bundle = IrQweb._get_asset_bundle(
            "web.assets_emoji",
            js=True,
            css=False,
            debug_assets=False,
            assets_params=assets_params,
        )
        self.assertTrue(
            bundle._is_esm_bundle,
            msg="web.assets_emoji must be classified as an ESM bundle",
        )
        self.assertGreater(
            len(bundle.native_modules),
            0,
            msg=(
                "bundle must have at least one native module "
                "(did ir.asset population run?)"
            ),
        )

        result = bundle.esbuild_native_bundle()

        self.assertIn(
            "odoo.loader.registerNativeModules",
            result.code,
            msg="bundle output must register modules via the loader API",
        )
        self.assertGreater(
            len(result.code),
            1000,
            msg=f"bundle output suspiciously small ({len(result.code)} bytes)",
        )
        self.assertIsNotNone(
            result.metafile,
            msg="metafile sidecar must be captured after successful build",
        )

    def test_timeout_parameter_threaded_through(self):
        IrQweb = self.env["ir.qweb"]
        assets_params = self.env["ir.asset"]._prepare_assets_params()
        bundle = IrQweb._get_asset_bundle(
            "web.assets_emoji",
            js=True,
            css=False,
            debug_assets=False,
            assets_params=assets_params,
        )
        result = bundle.esbuild_native_bundle(timeout_s=60, target="es2022")
        self.assertIn("odoo.loader.registerNativeModules", result.code)


@tagged("web_unit", "web_assets")
class TestEsbuildSettings(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()

    def _set(self, key, value):
        self.ICP.set_param(key, value)
        self.env.registry.clear_cache("stable")

    def test_unset_returns_default(self):
        self.ICP.search([("key", "=", "web.esbuild.cooldown_s")]).unlink()
        self.env.registry.clear_cache("stable")
        self.assertEqual(self.ICP.get_param_float("web.esbuild.cooldown_s", 60.0), 60.0)

    def test_valid_param_casts(self):
        self._set("web.esbuild.cooldown_s", "12.5")
        self.assertEqual(self.ICP.get_param_float("web.esbuild.cooldown_s", 60.0), 12.5)

    def test_unparseable_param_falls_back_to_default(self):
        self._set("web.esbuild.cooldown_s", "not-a-number")
        self.assertEqual(
            self.ICP.get_param_float("web.esbuild.cooldown_s", 60.0),
            60.0,
            msg="a bad cast must fall back to the default",
        )

    def test_fail_closed_agrees_with_every_other_boolean_parameter(self):
        IrQweb = self.env["ir.qweb"]
        for raw in ("0", "false", "no", "off", "none", ""):
            with self.subTest(raw=raw):
                self._set("web.esbuild.fail_closed", raw)
                self.assertFalse(
                    IrQweb._is_esbuild_fail_closed(),
                    msg=f"{raw!r} is falsy for ir.config_parameter",
                )
        for raw in ("1", "true", "yes"):
            with self.subTest(raw=raw):
                self._set("web.esbuild.fail_closed", raw)
                self.assertTrue(IrQweb._is_esbuild_fail_closed())

    def test_fail_closed_unset_follows_the_run_mode(self):
        self.ICP.search([("key", "=", "web.esbuild.fail_closed")]).unlink()
        self.env.registry.clear_cache("stable")
        self.assertTrue(
            self.env["ir.qweb"]._is_esbuild_fail_closed(),
            msg="under --test-enable the default is fail-closed",
        )


@tagged("web_unit", "web_assets")
class TestEsbuildSourceMaps(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        odoo_root = Path(odoo.__path__[0]).parent
        cls.esbuild = shutil.which("esbuild") or shutil.which(
            "esbuild",
            path=str(odoo_root / "node_modules" / ".bin"),
        )

    def setUp(self):
        super().setUp()
        if not self.esbuild:
            self.skipTest(
                "esbuild binary not found. Run 'npm install' in the Odoo root "
                "to enable this integration test.",
            )

    def _bundle(self, **kwargs):
        IrQweb = self.env["ir.qweb"]
        assets_params = self.env["ir.asset"]._prepare_assets_params()
        return IrQweb._get_asset_bundle(
            "web.assets_emoji",
            js=True,
            css=False,
            debug_assets=False,
            assets_params=assets_params,
        )

    def test_off_by_default(self):
        bundle = self._bundle()
        result = bundle.esbuild_native_bundle()
        self.assertIsNone(
            result.sourcemap,
            msg="default behavior must not capture a source map",
        )

    def test_linked_mode_populates_last_sourcemap_and_links_bundle(self):
        bundle = self._bundle()
        result = bundle.esbuild_native_bundle(source_maps="linked")
        self.assertIsNotNone(
            result.sourcemap,
            msg="linked mode must capture the sourcemap sibling",
        )
        parsed = json.loads(result.sourcemap)
        self.assertIn("version", parsed)
        self.assertIn("mappings", parsed)
        self.assertIn("//# sourceMappingURL=", result.code)

    def test_external_mode_emits_map_without_directive(self):
        bundle = self._bundle()
        result = bundle.esbuild_native_bundle(source_maps="external")
        self.assertIsNotNone(
            result.sourcemap,
            msg="external mode still writes the sidecar, just doesn't link it",
        )
        self.assertNotIn("//# sourceMappingURL=", result.code)

    def test_inline_mode_embeds_in_bundle(self):
        bundle = self._bundle()
        result = bundle.esbuild_native_bundle(source_maps="inline")
        self.assertIsNone(
            result.sourcemap,
            msg="inline mode embeds in bundle, no sidecar to capture",
        )
        self.assertIn(
            "//# sourceMappingURL=data:application/json;base64,",
            result.code,
        )

    def test_unknown_mode_silently_falls_back(self):
        bundle = self._bundle()
        with self.assertLogs(
            f"{ASSET_ROOT}.esbuild", level=logging.WARNING
        ) as captured:
            result = bundle.esbuild_native_bundle(source_maps="yes please")
        self.assertTrue(
            any(
                "event=source_maps_unknown_mode" in r.getMessage()
                and "mode=yes please" in r.getMessage()
                for r in captured.records
            ),
            msg="invalid source_maps mode must emit a structured warning",
        )
        self.assertIsNone(result.sourcemap)
        self.assertIn("odoo.loader.registerNativeModules", result.code)

    def test_external_mode_persists_sidecar_attachment(self):
        ir_qweb = self.env["ir.qweb"]
        url = ir_qweb._save_esm_attachment(
            "test.sm.sidecar",
            "/* bundle */",
            sourcemap='{"version":3,"sources":[],"mappings":""}',
        )
        sm_url = url + ".map"
        sm = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("url", "=", sm_url),
                    ("public", "=", True),
                ],
                limit=1,
            )
        )
        self.assertTrue(sm, msg="external-mode sidecar attachment must exist")
        self.assertEqual(sm.mimetype, "application/json")

    def test_no_sourcemap_no_sidecar(self):
        ir_qweb = self.env["ir.qweb"]
        url = ir_qweb._save_esm_attachment(
            "test.sm.absent",
            "/* bundle */",
        )
        sm_url = url + ".map"
        sm = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("url", "=", sm_url),
                ],
                limit=1,
            )
        )
        self.assertFalse(
            sm,
            msg="no source map must create no .map sidecar",
        )

    def test_setting_key_recognized(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.search([("key", "=", "web.esbuild.source_maps")]).unlink()
        self.env.registry.clear_cache("stable")
        self.assertEqual(ICP.get_param("web.esbuild.source_maps", ""), "")
        ICP.set_param("web.esbuild.source_maps", "external")
        self.env.registry.clear_cache("stable")
        self.assertEqual(ICP.get_param("web.esbuild.source_maps", ""), "external")


def _fake_native_module(url="", raw_content="", module_path="", filename=None):
    return SimpleNamespace(
        url=url,
        raw_content=raw_content,
        module_path=module_path,
        _filename=filename,
        parsed_header=_parse_odoo_module_header(raw_content),
    )


@tagged("web_unit", "web_assets")
class TestEsbuildHelpers(TransactionCase):
    def _compiler(self, name="web.assets_emoji", native_modules=(), provider=None):
        return EsbuildCompiler(
            name,
            list(native_modules),
            addon_flags_provider=provider,
        )

    def _odoo_root(self):
        return Path(odoo.__path__[0]).parent

    def test_resolve_opts_applies_defaults(self):
        c = self._compiler()
        timeout_s, target, source_maps = c._esbuild_resolve_opts(None, None, None)
        self.assertEqual(timeout_s, EsbuildCompiler._ESBUILD_TIMEOUT_S)
        self.assertEqual(target, EsbuildCompiler._ESBUILD_TARGET)
        self.assertEqual(source_maps, EsbuildCompiler._ESBUILD_SOURCE_MAPS)

    def test_resolve_opts_passes_through_valid(self):
        c = self._compiler()
        self.assertEqual(
            c._esbuild_resolve_opts(10, "es2022", "linked"),
            (10, "es2022", "linked"),
        )

    def test_resolve_opts_unknown_source_map_falls_back(self):
        c = self._compiler()
        with self.assertLogs(f"{ASSET_ROOT}.esbuild", level=logging.WARNING):
            _, _, source_maps = c._esbuild_resolve_opts(5, "es2023", "bogus")
        self.assertEqual(source_maps, "")

    def test_entry_lines_register_block(self):
        c = self._compiler(
            native_modules=[
                _fake_native_module(
                    url="/web/static/src/foo.js", module_path="@web/foo"
                ),
            ]
        )
        lines = c._esbuild_entry_lines(self._odoo_root())
        self.assertIn('import * as __owl from "@odoo/owl";', lines)
        self.assertIn('import * as __m0 from "./addons/web/static/src/foo.js";', lines)
        self.assertIn("odoo.loader.registerNativeModules({", lines)
        joined = "\n".join(lines)
        self.assertIn('"@odoo/owl": __owl', joined)
        self.assertIn('"@web/foo": __m0', joined)

    def test_flags_drops_own_test_externals(self):
        fake = (
            [],
            [
                "--external:@web/../tests/*",
                "--external:./web/static/tests/*",
                "--external:@other/../tests/*",
            ],
        )
        c = self._compiler(
            native_modules=[_fake_native_module(url="/web/static/tests/t.js")],
            provider=lambda root: fake,
        )
        _, external_flags = c._esbuild_flags(self._odoo_root(), None)
        self.assertNotIn("--external:@web/../tests/*", external_flags)
        self.assertNotIn("--external:./web/static/tests/*", external_flags)
        self.assertIn("--external:@other/../tests/*", external_flags)

    def test_flags_adds_dynamic_child_externals(self):
        c = self._compiler(provider=lambda root: ([], []))
        _, external_flags = c._esbuild_flags(
            self._odoo_root(), frozenset({"@lazy/child"})
        )
        self.assertIn("--external:@lazy/child", external_flags)

    def test_postprocess_rewrites_directive_and_captures_sidecars(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            out = tmp / "x.out.js"
            meta = tmp / "x.meta.json"
            smap = tmp / "x.out.js.map"
            out.write_text(
                "console.log(1);\n//# sourceMappingURL=tmpXYZ.js.out.js.map\n",
                encoding="utf-8",
            )
            meta.write_text('{"inputs":{}}', encoding="utf-8")
            smap.write_text('{"version":3,"mappings":""}', encoding="utf-8")
            result, metafile, sourcemap = esbuild_process.postprocess_output(
                "web.assets_emoji",
                0,
                out,
                meta,
                smap,
                "linked",
                entry_bytes=10,
                _t0=time.monotonic(),
            )
        self.assertIn("//# sourceMappingURL=web.assets_emoji.esm.js.map", result)
        self.assertNotIn("tmpXYZ", result)
        self.assertEqual(metafile, '{"inputs":{}}')
        self.assertEqual(sourcemap, '{"version":3,"mappings":""}')

    def test_postprocess_no_sourcemap_leaves_last_none(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            out = tmp / "x.out.js"
            meta = tmp / "x.meta.json"
            out.write_text("console.log(2);", encoding="utf-8")
            meta.write_text("{}", encoding="utf-8")
            result, _metafile, sourcemap = esbuild_process.postprocess_output(
                "web.assets_emoji", 0, out, meta, tmp / "x.map", "", 5, time.monotonic()
            )
        self.assertEqual(result, "console.log(2);")
        self.assertIsNone(sourcemap)

    def test_postprocess_missing_output_raises(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            with self.assertRaises(RuntimeError) as ctx:
                esbuild_process.postprocess_output(
                    "web.assets_emoji",
                    0,
                    tmp / "nope.js",
                    tmp / "nope.meta",
                    tmp / "nope.map",
                    "",
                    0,
                    time.monotonic(),
                )
        self.assertIn("output file missing", str(ctx.exception))


@tagged("web_unit", "web_assets")
class TestBridgeHelpers(TransactionCase):
    def test_resolver_resolves_external_lib(self):
        r = _BridgeExportResolver({"luxon": "/web/static/lib/luxon/luxon.js"}, "test")
        self.assertEqual(r.resolve_url("luxon"), "/web/static/lib/luxon/luxon.js")

    def test_resolver_resolves_addon_paths(self):
        r = _BridgeExportResolver({}, "test")
        self.assertEqual(
            r.resolve_url("@web/core/registry"),
            "/web/static/src/core/registry.js",
        )
        self.assertEqual(
            r.resolve_url("@web/../lib/foo/bar"), "/web/static/lib/foo/bar.js"
        )
        self.assertEqual(r.resolve_url("@web/../tests/baz"), "/web/static/tests/baz.js")

    def test_resolver_unmappable_specifiers(self):
        r = _BridgeExportResolver({}, "test")
        self.assertIsNone(r.resolve_url("luxon"))
        self.assertIsNone(r.resolve_url("@noslash"))

    def test_resolver_caches_and_get_protocol(self):
        r = _BridgeExportResolver({}, "test")
        self.assertIsNone(r.read_source("nope"))
        self.assertIn("nope", r._cache)
        self.assertIsNone(r._cache["nope"])
        self.assertIsNone(r.get("nope"))
        self.assertEqual(r.get("nope", "DEFAULT"), "DEFAULT")

    def test_discover_classifies_import_kinds(self):
        b = AssetsBundle("test.discover", [], env=self.env)
        b.native_modules = [
            _fake_native_module(
                raw_content=(
                    'import {a} from "@web/named";\n'
                    'import D from "@web/deflt";\n'
                    'import * as N from "@web/star";\n'
                )
            ),
        ]
        discovered, ext_seen = b._bridges._discover_bridge_specifiers(set(), set())
        self.assertEqual(discovered.get("@web/named"), set())
        self.assertEqual(discovered.get("@web/deflt"), {"__default__"})
        self.assertEqual(discovered.get("@web/star"), {"__star__"})
        self.assertEqual(ext_seen, set())

    def test_discover_excludes_ignored(self):
        b = AssetsBundle("test.discover2", [], env=self.env)
        b.native_modules = [
            _fake_native_module(
                raw_content=(
                    'import X from "@web/own";\n'
                    'import Y from "@odoo/owl";\n'
                    'import Z from "@web/extlib";\n'
                    'import W from "@web/keep";\n'
                )
            ),
        ]
        discovered, ext_seen = b._bridges._discover_bridge_specifiers(
            {"@web/own"}, {"@web/extlib"}
        )
        self.assertNotIn("@web/own", discovered)
        self.assertNotIn("@odoo/owl", discovered)
        self.assertNotIn("@web/extlib", discovered)
        self.assertIn("@web/keep", discovered)
        self.assertEqual(ext_seen, {"@web/extlib"})

    def test_shim_source_default_and_named(self):
        shim, star = _bridge_shim_source("@web/foo", set(), {"b", "a"}, True)
        self.assertFalse(star)
        self.assertIn('const _m = odoo.loader.modules.get("@web/foo");', shim)
        self.assertIn("_d = _m.default ?? _m;", shim)
        self.assertIn("_d as default", shim)
        self.assertIn("_e0 = _m.a;", shim)
        self.assertIn("_e1 = _m.b;", shim)
        self.assertIn("export { _d as default, _e0 as a, _e1 as b };", shim)

    def test_shim_source_star_fallback(self):
        shim, star = _bridge_shim_source("@web/bar", set(), set(), False)
        self.assertTrue(star)
        self.assertIn("_d = _m.default ?? _m;", shim)
        self.assertIn("_d as default", shim)
        self.assertEqual(shim.count("export {"), 1)
        self.assertNotIn("_e0", shim)

    def test_shim_source_waits_for_an_unregistered_provider(self):
        shim, _star = _bridge_shim_source("@web/late", set(), {"x"}, False, wait=True)
        self.assertIn("await new Promise(", shim)
        self.assertIn('addEventListener("registered", _w)', shim)
        self.assertIn("provider not registered after", shim)
        self.assertIn('addEventListener("registered", _s)', shim)
        eager, _star = _bridge_shim_source("@web/late", set(), {"x"}, False)
        self.assertNotIn("await", eager)

    def test_shim_source_named_only_still_exports_default(self):
        shim, star = _bridge_shim_source("@web/baz", set(), {"x"}, False)
        self.assertFalse(star)
        self.assertIn("_e0 = _m.x;", shim)
        self.assertIn("_e0 as x", shim)
        self.assertIn("_d as default", shim)

    def test_shim_source_star_kind_no_duplicate_default(self):
        shim, star = _bridge_shim_source("@web/qux", {"__star__"}, set(), False)
        self.assertTrue(star)
        self.assertEqual(shim.count("export {"), 1)
        self.assertEqual(shim.count(" as default"), 1)
        self.assertNotIn("export default", shim)

    def test_shim_source_default_kind_triggers_export(self):
        shim, star = _bridge_shim_source("@web/q", {"__default__"}, set(), False)
        self.assertFalse(star)
        self.assertIn("_d as default", shim)


@tagged("web_unit", "web_assets")
class TestTransitiveImportClosure(TransactionCase):
    @staticmethod
    def _read_static_url(url):
        if not url.startswith("/") or "/static/" not in url:
            return None
        try:
            return Path(file_path(url.lstrip("/"))).read_text(encoding="utf-8")
        except OSError, ValueError:
            return None

    def test_walk_finds_two_hop_specifier(self):
        res = discover_transitive_import_specifiers(
            [
                "@web/../lib/bootstrap/bootstrap.esm.js",
                "@web/core/utils/dom/scrolling",
            ],
            {"@web/libs/bootstrap"},
            external_libs(),
            "test.report.closure",
        )
        self.assertIn("@web/core/browser/browser", res)
        self.assertNotIn("@popperjs/core", res)
        self.assertNotIn("@web/libs/bootstrap", res)

    def test_scan_covers_reexport_and_relative_shapes(self):
        specs = _get_import_specifiers(
            'import { a } from "@web/named";\n'
            'import "@web/side_effect";\n'
            'import "./relative";\n'
            'export { b } from "@web/list_from";\n'
            'export * from "@web/star_from";\n'
            'export * as ns from "@web/ns_from";\n'
            'const url = import("@web/dynamic_only");\n'
        )
        self.assertLessEqual(
            {
                "@web/named",
                "@web/side_effect",
                "./relative",
                "@web/list_from",
                "@web/star_from",
                "@web/ns_from",
            },
            specs,
        )
        self.assertNotIn("@web/dynamic_only", specs)

    def _debug_importmap(self, bundle):
        nodes, _post = self.env["ir.qweb"]._get_native_module_nodes(
            bundle,
            debug="assets",
        )
        importmaps = [
            attrs
            for tag, attrs in nodes
            if tag == "script" and attrs.get("type") == "importmap"
        ]
        self.assertEqual(len(importmaps), 1)
        return json.loads(importmaps[0]["text"])["imports"]

    def _reachable_urls(self, imports, seeds):
        queue = [(spec, imports.get(spec)) for spec in seeds]
        seen_urls = set()
        while queue:
            _spec, url = queue.pop()
            if url is None or url in seen_urls:
                continue
            seen_urls.add(url)
            source = self._read_static_url(url)
            if source is None:
                continue
            for imported in _get_import_specifiers(source):
                if imported.startswith("."):
                    queue.append(
                        (
                            imported,
                            posixpath.normpath(f"{posixpath.dirname(url)}/{imported}"),
                        ),
                    )
                elif imported.startswith("/"):
                    queue.append((imported, imported))
                else:
                    queue.append((imported, imports.get(imported)))
        return seen_urls

    def test_tour_bundle_does_not_load_the_hoot_runner(self):
        imports = self._debug_importmap("web.assets_tests")
        seeds = [
            "@web/../tests/utils",
            "@web/../tests/helpers/utils",
            "@web/../tests/helpers/cleanup",
        ]
        for spec in seeds:
            self.assertIn(spec, imports, msg=f"{spec} missing from import map")
        reached = self._reachable_urls(imports, seeds)
        runner_urls = sorted(
            url
            for url in reached
            if url.endswith(("/lib/hoot/hoot.js", "/lib/hoot/core/runner.js"))
        )
        self.assertFalse(
            runner_urls,
            "The tour helpers reach the HOOT runner, which hooks window.onerror and "
            "unhandledrejection at import and turns every handled RPC error in a "
            "tour page into a console.error the browser harness fails on:"
            "\n- " + "\n- ".join(runner_urls),
        )

    def test_report_bundle_debug_importmap_is_transitively_complete(self):
        nodes, _post = self.env["ir.qweb"]._get_native_module_nodes(
            "web.report_assets_common",
            debug="assets",
        )
        importmaps = [
            attrs
            for tag, attrs in nodes
            if tag == "script" and attrs.get("type") == "importmap"
        ]
        self.assertEqual(len(importmaps), 1)
        imports = json.loads(importmaps[0]["text"])["imports"]
        for spec in ("@web/libs/bootstrap", "@popperjs/core"):
            self.assertIn(spec, imports, msg=f"{spec} missing from import map")

        seed = "@web/libs/bootstrap"
        queue = [(seed, imports.get(seed))]
        seen_urls = set()
        unmapped = []
        while queue:
            spec, url = queue.pop()
            if url is None:
                unmapped.append(spec)
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            source = self._read_static_url(url)
            if source is None:
                continue
            for imported in _get_import_specifiers(source):
                if imported.startswith("."):
                    queue.append(
                        (
                            imported,
                            posixpath.normpath(f"{posixpath.dirname(url)}/{imported}"),
                        ),
                    )
                elif imported.startswith("/"):
                    queue.append((imported, imported))
                else:
                    queue.append((imported, imports.get(imported)))
        self.assertFalse(
            unmapped,
            "Specifiers reachable from the report bundle but absent from its "
            "debug import map (the browser cannot resolve them):"
            "\n- " + "\n- ".join(sorted(unmapped)),
        )


@tagged("web_unit", "web_assets")
class TestEsmLexer(TransactionCase):
    SRC = (
        'import { q } from "@web/other";\n'
        "export const alpha = 1;\n"
        "export function beta() {}\n"
        "export default class Gamma {}\n"
        'export * as ns from "@web/ns_target";\n'
        "/* export const block_commented = 2; */\n"
        "const tpl = `export const in_template = 3;`;\n"
    )

    def test_worker_available(self):
        from odoo.tools.assets.esm_lexer import lex_module

        result = lex_module("export const x = 1;")
        self.assertIsNotNone(
            result,
            msg="es-module-lexer worker unavailable — run `npm install` "
            "in the Odoo root (same prerequisite as esbuild)",
        )
        self.assertEqual(result["names"], ["x"])
        self.assertFalse(result["hasDefault"])

    def test_lexer_and_regex_paths_agree(self):
        from odoo.tools.assets import esm_graph

        expected = ({"alpha", "beta", "ns"}, True)
        self.assertEqual(esm_graph._extract_esm_exports(self.SRC), expected)
        with patch.object(esm_graph, "lex_module", return_value=None):
            self.assertEqual(esm_graph._extract_esm_exports(self.SRC), expected)

    def test_lexer_line_comment_immunity(self):
        from odoo.tools.assets import esm_graph

        names, has_default = esm_graph._extract_esm_exports(
            "// export const ghost = 1;\nexport const real = 2;\n"
        )
        self.assertEqual(names, {"real"})
        self.assertFalse(has_default)

    def test_star_expansion_shared_by_both_paths(self):
        from odoo.tools.assets import esm_graph

        source_map = {
            "@web/barrel": 'export * from "@web/leaf";\nexport const own = 1;',
            "@web/leaf": "export const leaf_a = 1;\nexport const leaf_b = 2;",
        }
        expected = ({"own", "leaf_a", "leaf_b"}, False)
        result = esm_graph._extract_esm_exports(
            source_map["@web/barrel"],
            source_map=source_map,
            importing_specifier="@web/barrel",
        )
        self.assertEqual(result, expected)
        with patch.object(esm_graph, "lex_module", return_value=None):
            result = esm_graph._extract_esm_exports(
                source_map["@web/barrel"],
                source_map=source_map,
                importing_specifier="@web/barrel",
            )
        self.assertEqual(result, expected)

    def test_unlexable_source_falls_back_to_regex(self):
        from odoo.tools.assets import esm_graph

        broken = "export const good = 1;\nfunction ( { invalid syntax\n"
        names, _ = esm_graph._extract_esm_exports(broken)
        self.assertIn("good", names)

    def test_discovery_catches_mixed_default_named_import(self):
        from odoo.tools.assets.esm_bridges import BridgeShimManager

        asset = SimpleNamespace(
            module_path="@web/consumer",
            raw_content='import Def, { named } from "@other/mixed";\n',
        )
        manager = BridgeShimManager(self.env, "test.bundle", [asset])
        discovered, _ext = manager._discover_bridge_specifiers(set(), set())
        self.assertIn("@other/mixed", discovered)
        self.assertIn("__default__", discovered["@other/mixed"])


@tagged("web_unit", "web_assets")
class TestQwebAssetHelpers(TransactionCase):
    @property
    def _qweb(self):
        return self.env["ir.qweb"]

    def test_specifier_convention_resolves(self):
        cases = {
            "@web/core/registry": "/web/static/src/core/registry.js",
            "@web/../lib/hoot/hoot": "/web/static/lib/hoot/hoot.js",
            "@web/../tests/foo": "/web/static/tests/foo.js",
            "@account/models/move": "/account/static/src/models/move.js",
        }
        for spec, url in cases.items():
            self.assertEqual(self._qweb._specifier_to_static_url(spec), url, spec)

    def test_specifier_odoo_namespace_is_reserved(self):
        externals = self._qweb._external_libs()
        for spec in [k for k in externals if k.startswith("@odoo/")]:
            self.assertIsNone(
                self._qweb._specifier_to_static_url(spec),
                f"{spec} must not resolve via the addon convention",
            )
            self.assertTrue(externals[spec])
        self.assertIsNone(self._qweb._specifier_to_static_url("@odoo/nope"))

    def test_specifier_non_convention_returns_none(self):
        for spec in ["luxon", "@web", "@/foo", ""]:
            self.assertIsNone(self._qweb._specifier_to_static_url(spec), spec)

    def test_is_debug_assets_string_semantics(self):
        q = self._qweb
        self.assertTrue(q._is_debug_assets("assets"))
        self.assertTrue(q._is_debug_assets("1,assets"))
        self.assertFalse(q._is_debug_assets("1"))
        self.assertFalse(q._is_debug_assets(""))

    def test_is_debug_assets_never_raises_on_non_str(self):
        q = self._qweb
        for value in (True, False, None, 0, 1):
            self.assertFalse(q._is_debug_assets(value), repr(value))

    def test_get_asset_links_survives_bool_debug(self):
        self.assertEqual(
            self._qweb._get_asset_links(
                "web.assets_web", css=False, js=False, debug=True
            ),
            [],
        )

    def test_link_to_node_stylesheet_is_text_css(self):
        for path in ["/x/a.css", "/x/a.scss", "/x/a.sass"]:
            tag, attrs = self._qweb._link_to_node(path)
            self.assertEqual(tag, "link", path)
            self.assertEqual(attrs["type"], "text/css", path)
            self.assertEqual(attrs["rel"], "stylesheet", path)

    def test_link_to_node_script_and_xml(self):
        tag, attrs = self._qweb._link_to_node("/x/a.js")
        self.assertEqual(
            (tag, attrs["type"], attrs.get("src")),
            ("script", "text/javascript", "/x/a.js"),
        )
        tag, attrs = self._qweb._link_to_node("/x/a.xml")
        self.assertEqual(
            (tag, attrs["type"], attrs.get("data-src")),
            ("script", "text/xml", "/x/a.xml"),
        )

    def test_import_map_url_breakdown(self):
        im = {
            "a": "/web/static/src/a.js",
            "b": "/web/assets/esm/bridges/deadbeef.js",
            "c": "data:text/javascript,1",
            "d": "/account/static/src/d.js",
        }
        self.assertEqual(self._qweb._get_import_map_url_counts(im), (2, 1, 1))
        self.assertEqual(self._qweb._get_import_map_url_counts({}), (0, 0, 0))

    def test_combine_no_templates_is_identity(self):
        self.assertEqual(
            self._qweb._combine_bundle_with_templates("CODE;", ""), "CODE;"
        )

    def test_combine_appends_templates(self):
        out = self._qweb._combine_bundle_with_templates("CODE;", "TPL;")
        self.assertIn("CODE;", out)
        self.assertIn("TPL;", out)
        self.assertNotIn("sourceMappingURL", out)

    def test_combine_keeps_sourcemap_directive_last(self):
        src = "CODE;\n//# sourceMappingURL=b.esm.js.map"
        out = self._qweb._combine_bundle_with_templates(src, "TPL;")
        last = out.rstrip("\n").splitlines()[-1]
        self.assertEqual(last, "//# sourceMappingURL=b.esm.js.map")
        self.assertEqual(out.count("sourceMappingURL"), 1)
        self.assertIn("TPL;", out)


@tagged("web_unit", "web_assets")
class TestNativeNodesDispatch(TransactionCase):
    BUNDLE = "web.assets_web"
    PRE = [("script", {"type": "importmap", "data-bundle": "t", "text": "{}"})]
    POST = [("script", {"type": "module", "text": "t"})]

    @property
    def _qweb(self):
        return self.env["ir.qweb"]

    def _run(self, *, debug="", readonly=False, cached=None, impl=None):
        ir_qweb = self._qweb
        patches = [
            patch.object(
                type(ir_qweb),
                "_get_native_module_nodes_cached",
                **(cached or {"return_value": (self.PRE, self.POST)}),
            ),
            patch.object(
                type(ir_qweb),
                "_get_native_module_nodes_uncached",
                **(impl or {"return_value": (self.PRE, self.POST)}),
            ),
        ]
        if readonly:
            patches.append(patch.object(self.env.cr, "_readonly", True))
        with patches[0] as cached_mock, patches[1] as impl_mock:
            if readonly:
                with patches[2]:
                    result = ir_qweb._get_native_module_nodes(self.BUNDLE, debug=debug)
            else:
                result = ir_qweb._get_native_module_nodes(self.BUNDLE, debug=debug)
        return result, cached_mock, impl_mock

    def test_readwrite_prod_uses_cache(self):
        result, cached_mock, impl_mock = self._run()
        self.assertEqual(result, (self.PRE, self.POST))
        cached_mock.assert_called_once()
        impl_mock.assert_not_called()

    def test_readonly_prod_uses_cache(self):
        result, cached_mock, impl_mock = self._run(readonly=True)
        self.assertEqual(result, (self.PRE, self.POST))
        cached_mock.assert_called_once()
        impl_mock.assert_not_called()

    def test_debug_assets_bypasses_cache(self):
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                result, cached_mock, impl_mock = self._run(
                    debug="assets", readonly=readonly
                )
                self.assertEqual(result, (self.PRE, self.POST))
                cached_mock.assert_not_called()
                impl_mock.assert_called_once()

    def test_forced_fallback_is_cached_under_its_own_key(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.esbuild.force_fallback_bundles", self.BUNDLE
        )
        self.addCleanup(
            self.env["ir.config_parameter"].sudo().set_param,
            "web.esbuild.force_fallback_bundles",
            "",
        )
        self.env.registry.clear_cache("stable")
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                result, cached_mock, impl_mock = self._run(readonly=readonly)
                self.assertEqual(result, (self.PRE, self.POST))
                cached_mock.assert_called_once()
                self.assertFalse(
                    cached_mock.call_args.kwargs["esbuild_ok"],
                    msg="the fallback must be cached under esbuild_ok=False",
                )
                impl_mock.assert_not_called()

    def test_decline_falls_back_uncached(self):
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                result, cached_mock, impl_mock = self._run(
                    readonly=readonly,
                    cached={"side_effect": _EsmFallbackError},
                )
                self.assertEqual(result, (self.PRE, self.POST))
                cached_mock.assert_called_once()
                impl_mock.assert_called_once()


@tagged("web_unit", "web_assets")
class TestEsbuildLockCursor(TransactionCase):
    @property
    def _qweb(self):
        return self.env["ir.qweb"]

    def test_readwrite_yields_a_dedicated_cursor(self):
        self.assertFalse(self.env.cr.readonly)
        with self._qweb._get_esbuild_lock_cursor("b.x") as lock_cr:
            self.assertIsNotNone(lock_cr)
            self.assertIsNot(
                lock_cr,
                self.env.cr,
                msg="the lock must not be taken on the request transaction",
            )
            lock_cr.execute("SELECT pg_backend_pid()")
            self.assertNotEqual(
                lock_cr.fetchone()[0],
                self._backend_pid(),
                msg="a dedicated cursor means a separate backend",
            )

    def _backend_pid(self):
        self.env.cr.execute("SELECT pg_backend_pid()")
        return self.env.cr.fetchone()[0]

    def test_the_lock_is_released_when_the_block_exits(self):
        free = "SELECT pg_try_advisory_xact_lock(hashtext(%s))"
        with self._qweb._get_esbuild_lock_cursor("b.x") as lock_cr:
            self._qweb._acquire_esbuild_lock("b.x", cr=lock_cr)
            self.env.cr.execute(free, ("esbuild:b.x",))
            self.assertFalse(
                self.env.cr.fetchone()[0],
                msg="the compile must hold the lock against another backend",
            )
        self.env.cr.execute(free, ("esbuild:b.x",))
        self.assertTrue(
            self.env.cr.fetchone()[0],
            msg="the advisory lock must not outlive the compile",
        )

    def test_readonly_test_cursor_locks_on_the_request_cursor(self):
        with patch.object(self.env.cr, "_readonly", True):
            with self._qweb._get_esbuild_lock_cursor("b.x") as lock_cr:
                self.assertIs(
                    lock_cr,
                    self.env.cr,
                    msg="a test cannot open a read-write cursor from a readonly "
                    "one, and an advisory lock is legal on a read-only "
                    "transaction outside recovery",
                )
                self._qweb._acquire_esbuild_lock("b.x", cr=lock_cr)

    def test_acquire_lock_runs_on_the_given_cursor(self):
        executed = []

        fake_cr = SimpleNamespace(
            execute=lambda sql, params=None: executed.append(sql),
            fetchone=lambda: (True,),
        )
        self._qweb._acquire_esbuild_lock("b.x", cr=fake_cr)
        self.assertEqual(len(executed), 1)
        self.assertIn("pg_advisory_xact_lock", executed[0])

    def test_readonly_test_cursor_builds_under_the_lock(self):
        ir_qweb = self._qweb
        locked_on = []
        with (
            patch.object(self.env.cr, "_readonly", True),
            patch.object(
                type(ir_qweb),
                "_acquire_esbuild_lock",
                lambda _self, bundle, cr=None: locked_on.append(cr) or True,
            ),
            patch.object(
                type(ir_qweb),
                "_get_dynamic_child_bundles",
                lambda *_a, **_k: [],
            ),
            patch.object(
                type(ir_qweb),
                "_get_esbuild_child_externals",
                lambda *_a, **_k: (None, {}),
            ),
            patch.object(
                AssetsBundle,
                "esbuild_native_bundle",
                lambda *_a, **_k: EsbuildResult("built", None, None),
            ),
        ):
            result, child_bundles = ir_qweb._compile_with_esbuild_locked(
                "web.assets_web", AssetsBundle("web.assets_web", [], env=self.env), None
            )
        self.assertEqual(result.code, "built")
        self.assertEqual(child_bundles, [])
        self.assertEqual(locked_on, [self.env.cr])


@tagged("web_unit", "web_assets")
class TestRuntimeGroupUrls(TransactionCase):
    def test_a_child_with_no_file_of_its_own_gets_no_url(self):
        urls = self.env["ir.qweb"]._save_esm_group(
            "runtime:g5.parent",
            {"g5.child.esm.js": b"export const x = 1;"},
            ["g5.child", "g5.carried"],
        )
        self.assertEqual(set(urls), {"g5.child"})
        self.assertTrue(urls["g5.child"].endswith("/g5.child.esm.js"))


@tagged("web_unit", "web_assets")
class TestEsmRowsOutliveTheTest(TransactionCase):
    URL = "/web/assets/esm/test-outlives/web.assets_test_outlives.esm.js"

    def _rows_elsewhere(self):
        from odoo.db import db_connect

        with db_connect(self.env.cr.dbname).cursor() as other:
            other.execute(
                "SELECT id, write_date FROM ir_attachment WHERE url = %s", (self.URL,)
            )
            return other.fetchall()

    def _forget_elsewhere(self):
        from odoo.db import db_connect

        with db_connect(self.env.cr.dbname).cursor() as other:
            other.execute("DELETE FROM ir_attachment WHERE url = %s", (self.URL,))
            other.commit()

    def test_a_bundle_saved_under_a_test_is_there_for_the_next_one(self):
        self.addCleanup(self._forget_elsewhere)
        vals = {
            "name": "web.assets_test_outlives.esm.js",
            "url": self.URL,
            "mimetype": "text/javascript",
            "raw": b"export const outlives = true;",
            "public": True,
            "res_model": "ir.ui.view",
        }
        self.env["ir.qweb"]._save_esm_attachment_rows([vals], bundle="outlives")
        rows = self._rows_elsewhere()
        self.assertEqual(len(rows), 1, "the row is visible from another connection")
        self.env["ir.qweb"]._save_esm_attachment_rows([vals], bundle="outlives")
        self.assertEqual(len(self._rows_elsewhere()), 1, "saved once, by url")

    def test_a_table_the_test_altered_does_not_hang_the_save(self):
        self.addCleanup(self._forget_elsewhere)
        self.env.cr.execute("LOCK TABLE res_company IN ACCESS EXCLUSIVE MODE")
        vals = {
            "name": "web.assets_test_outlives.esm.js",
            "url": self.URL,
            "mimetype": "text/javascript",
            "raw": b"export const outlives = true;",
            "public": True,
            "res_model": "ir.ui.view",
        }
        self.env["ir.qweb"]._save_esm_attachment_rows([vals], bundle="outlives")
        self.assertEqual(self._rows_elsewhere(), [])
        self.assertEqual(
            self.env["ir.attachment"].search_count([("url", "=", self.URL)]), 1
        )

    def test_public_asset_persistence_does_not_wait_for_the_test_company(self):
        self.addCleanup(self._forget_elsewhere)
        self.env.cr.execute(
            "SELECT id FROM res_company WHERE id = %s FOR UPDATE",
            (self.env.company.id,),
        )
        IrQweb = type(self.env["ir.qweb"])
        drop_present = IrQweb._drop_rows_already_present

        def bounded_write(cr, vals):
            cr.execute("SET LOCAL lock_timeout = '200ms'")
            return drop_present(cr, vals)

        with patch.object(
            IrQweb, "_drop_rows_already_present", staticmethod(bounded_write)
        ):
            self.env["ir.qweb"]._save_esm_attachment_rows(
                [
                    {
                        "name": "company-independent.js",
                        "url": self.URL,
                        "raw": b"export const shared = true;",
                        "public": True,
                        "mimetype": "text/javascript",
                        "res_model": "ir.ui.view",
                    }
                ],
                bundle="company-independent",
            )
        self.assertEqual(len(self._rows_elsewhere()), 1)
        from odoo.db import db_connect

        with db_connect(self.env.cr.dbname).cursor() as other:
            other.execute(
                "SELECT company_id FROM ir_attachment WHERE url = %s", (self.URL,)
            )
            self.assertEqual(other.fetchone(), (None,))


@tagged("web_unit", "web_assets")
class TestEsmSourceKeyedReuse(TransactionCase):
    BUNDLE = "web.assets_web"

    def setUp(self):
        super().setUp()
        self.env.registry.clear_cache("assets")
        self.addCleanup(self.env.registry.clear_cache, "assets")
        self.compiles = 0
        IrQweb = type(self.env["ir.qweb"])
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(ir_qweb_assets, "request", None))
        stack.enter_context(
            patch.object(IrQweb, "_get_dynamic_child_bundles", lambda *_a, **_k: [])
        )
        stack.enter_context(
            patch.object(
                IrQweb, "_get_esbuild_child_externals", lambda *_a, **_k: (None, {})
            )
        )
        stack.enter_context(
            patch.object(AssetsBundle, "esbuild_native_bundle", self._compile)
        )
        self._forget()
        self.addCleanup(self._forget)

    def _compile(self, *_args, **_kwargs):
        self.compiles += 1
        return EsbuildResult("export const keyed = 1;", '{"outputs": {}}', None)

    def _forget(self):
        from odoo.db import db_connect

        with db_connect(self.env.cr.dbname).cursor() as other:
            other.execute(
                "DELETE FROM ir_attachment WHERE url LIKE %s",
                (f"/web/assets/esm/by-source/%/{self.BUNDLE}.json",),
            )
            other.commit()

    def test_the_next_process_serves_the_index_without_esbuild(self):
        # the test transaction is REPEATABLE READ and cannot see rows another
        # connection commits, so both renders run on connections of their own,
        # the way two worker processes would
        from odoo.db import db_connect

        params = self.env["ir.asset"]._prepare_assets_params()
        results = []
        for _process in range(2):
            with db_connect(self.env.cr.dbname).cursor() as own:
                fresh = odoo.api.Environment(own, SUPERUSER_ID, {})["ir.qweb"]
                self.env.registry.clear_cache("assets")
                results.append(
                    fresh._get_native_module_nodes(self.BUNDLE, assets_params=params)
                )
        self.assertEqual(
            self.compiles,
            1,
            "the second process finds the compiled bundle by its sources' digest",
        )
        self.assertEqual(results[1], results[0])


@tagged("web_unit", "web_assets")
class TestProdNodesDeclineNotCached(TransactionCase):
    BUNDLE = "g4.decline.bundle"

    @property
    def _qweb(self):
        return self.env["ir.qweb"]

    def _fake_bundle(self):
        return SimpleNamespace(
            name=self.BUNDLE,
            generate_esm_template_bundle=lambda use_import: "",
        )

    def test_decline_raises_instead_of_inlining(self):
        ir_qweb = self._qweb
        with patch.object(
            type(ir_qweb),
            "_save_esm_attachment",
            side_effect=ReadOnlySqlTransaction("no writable cursor"),
        ):
            with (
                self.assertLogs(
                    f"{ASSET_ROOT}.attach", level=logging.WARNING
                ) as caught,
                self.assertRaises(_EsmFallbackError),
            ):
                ir_qweb._get_esm_nodes_prod(
                    self.BUNDLE,
                    self._fake_bundle(),
                    EsbuildResult("CODE;", None, None),
                    None,
                    [],
                    raise_on_decline=True,
                )
        self.assertIn("declined=True", caught.output[0])

    def test_a_failed_save_statement_leaves_the_transaction_usable(self):
        # the touch of a row another connection updated is a serialization
        # failure inside the caller's transaction; served inline, the caller
        # must still be able to run the next statement
        ir_qweb = self._qweb

        def failing_touch(cr, touch_ids):
            cr.execute("SELECT 1 / 0")

        with (
            patch.object(
                type(ir_qweb),
                "_plan_esm_row",
                lambda self, rows, touch_ids, *a: touch_ids.append(1) or False,
            ),
            patch.object(
                type(ir_qweb), "_touch_esm_attachment_rows", staticmethod(failing_touch)
            ),
            self.assertLogs(f"{ASSET_ROOT}.attach", level=logging.WARNING) as caught,
        ):
            _pre, post = ir_qweb._get_esm_nodes_prod(
                self.BUNDLE,
                self._fake_bundle(),
                EsbuildResult("CODE;", None, None),
                None,
                [],
            )
        self.assertIn("err=DivisionByZero", caught.output[0])
        module_nodes = [
            attrs
            for tag, attrs in post
            if tag == "script" and attrs.get("type") == "module"
        ]
        self.assertEqual(module_nodes[0].get("text"), "CODE;")
        self.env.cr.execute("SELECT 1")
        self.assertEqual(self.env.cr.fetchone(), (1,))

    def test_uncached_rerun_still_inlines(self):
        ir_qweb = self._qweb
        with patch.object(
            type(ir_qweb),
            "_save_esm_attachment",
            side_effect=ReadOnlySqlTransaction("no writable cursor"),
        ):
            with self.assertLogs(
                f"{ASSET_ROOT}.attach", level=logging.WARNING
            ) as caught:
                _pre, post = ir_qweb._get_esm_nodes_prod(
                    self.BUNDLE,
                    self._fake_bundle(),
                    EsbuildResult("CODE;", None, None),
                    None,
                    [],
                )
        self.assertIn("declined=False", caught.output[0])
        module_nodes = [
            attrs
            for tag, attrs in post
            if tag == "script" and attrs.get("type") == "module"
        ]
        self.assertEqual(len(module_nodes), 1)
        self.assertEqual(module_nodes[0].get("text"), "CODE;")
        self.assertNotIn("src", module_nodes[0])


@tagged("web_unit", "web_assets")
class TestReadonlyDeclineIsRemembered(TransactionCase):
    BUNDLE = "web.assets_web"

    def setUp(self):
        super().setUp()
        self.env.registry.clear_cache("assets")
        self.addCleanup(self.env.registry.clear_cache, "assets")
        self.compiles = 0
        self.params = self.env["ir.asset"]._prepare_assets_params()
        IrQweb = type(self.env["ir.qweb"])
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(ir_qweb_assets, "request", None))
        stack.enter_context(
            patch.object(IrQweb, "_get_dynamic_child_bundles", lambda *_a, **_k: [])
        )
        stack.enter_context(
            patch.object(
                IrQweb, "_get_esbuild_child_externals", lambda *_a, **_k: (None, {})
            )
        )
        stack.enter_context(
            patch.object(
                IrQweb, "_get_esm_nodes_debug", lambda *_a, **_k: ([("debug", {})], [])
            )
        )
        stack.enter_context(
            patch.object(AssetsBundle, "esbuild_native_bundle", self._compile)
        )

    def _compile(self, *_args, **_kwargs):
        self.compiles += 1
        return EsbuildResult(f"built{self.compiles};", None, None)

    def _render(self, *, readonly=True):
        # the memo is the contract for a write that cannot happen: under a test
        # the rows normally go through their own connection, so that write is
        # made to fail here the way a read-only cursor used to
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.closing(self.env.cr.savepoint(flush=False)))
            if readonly:
                stack.enter_context(patch.object(self.env.cr, "_readonly", True))
                stack.enter_context(
                    patch.object(
                        type(self.env["ir.qweb"]),
                        "_save_esm_attachment_rows_autonomously",
                        side_effect=ReadOnlySqlTransaction("no writable cursor"),
                    )
                )
            return self.env["ir.qweb"]._get_native_module_nodes(
                self.BUNDLE, assets_params=self.params
            )

    def test_a_readonly_decline_is_the_fallback_signal(self):
        # under a test the rows go through their own connection; the decline
        # is what a failure of that write becomes on a read-only cursor
        with (
            patch.object(self.env.cr, "_readonly", True),
            patch.object(
                type(self.env["ir.qweb"]),
                "_save_esm_attachment_rows_autonomously",
                side_effect=ReadOnlySqlTransaction("no writable cursor"),
            ),
        ):
            with self.assertRaises(_EsmReadonlyDeclined):
                self.env["ir.qweb"]._prepare_esm_script_node(
                    "b.x", "export const x = 1;", {}, raise_on_decline=True
                )
        self.assertTrue(issubclass(_EsmReadonlyDeclined, _EsmFallbackError))

    def test_the_second_readonly_render_compiles_nothing(self):
        first = self._render()
        self.assertEqual(self.compiles, 1)
        self.assertEqual(first[0], [("debug", {})])
        with self.assertNoLogs(f"{ASSET_ROOT}.attach", level=logging.WARNING):
            again = self._render()
        self.assertEqual(
            self.compiles,
            1,
            msg="a readonly test cursor cannot persist what it compiles, so "
            "compiling it again on the next request only burns esbuild time",
        )
        self.assertEqual(again, first)

    def test_a_transient_decline_is_not_remembered(self):
        attempts = []
        with patch.object(
            type(self.env["ir.qweb"]),
            "_get_esbuild_lock_cursor",
            lambda _self, bundle: (
                attempts.append(bundle) or contextlib.nullcontext(None)
            ),
        ):
            self._render()
            self._render()
        self.assertEqual(
            len(attempts), 2, "an unavailable lock cursor is retried next time"
        )
        self.assertEqual(self.compiles, 0)

    def test_a_readwrite_cursor_ignores_the_memo(self):
        self._render()
        _pre, post = self._render(readonly=False)
        self.assertEqual(self.compiles, 2)
        self.assertTrue(post[0][1].get("src"), "the read-write render persists")
        self._render()
        self.assertEqual(self.compiles, 2, "the persisted variant is now cached")

    def test_a_persisted_artifact_lifts_the_memo(self):
        self._render()
        self.assertEqual(self.compiles, 1)
        self.env["ir.qweb"]._save_esm_attachment(self.BUNDLE, "export const y = 2;")
        self._render()
        self.assertEqual(
            self.compiles,
            2,
            msg="once something is persisted for the bundle, a readonly render "
            "must compile again to find its own artifact by url",
        )

    def test_clearing_the_assets_cache_forgets_the_decline(self):
        self._render()
        self.env.registry.clear_cache("assets")
        self._render()
        self.assertEqual(self.compiles, 2)


@tagged("web_unit", "web_assets")
class TestImportMapMergeHelpers(TransactionCase):
    @property
    def _qweb(self):
        return self.env["ir.qweb"]

    BUNDLE = "web.assets_unit_tests_setup"
    COLLIDING = "@odoo/hoot"
    DECOY = "/web/static/lib/hoot/decoy_that_is_not_served.js"

    def _rendered_import_map(self, debug):
        pre, _post = self._qweb._get_native_module_nodes(self.BUNDLE, debug=debug)
        for tag, attrs in pre:
            if tag == "script" and attrs.get("type") == "importmap":
                return json.loads(attrs["text"])["imports"]
        return {}

    def test_the_page_entry_outranks_the_external_table(self):
        own = self._qweb._get_native_module_data_cached(
            self.BUNDLE,
            assets_params=self.env["ir.asset"]._prepare_assets_params(),
        )["import_map"]
        self.assertIn(
            self.COLLIDING,
            own,
            f"{self.BUNDLE} no longer claims {self.COLLIDING}; pick another "
            "colliding specifier or drop this test",
        )
        externals = dict(self._qweb._external_libs())
        externals[self.COLLIDING] = self.DECOY
        with patch.object(
            type(self._qweb), "_external_libs", staticmethod(lambda: externals)
        ):
            self.env.registry.clear_cache("assets")
            rendered = self._rendered_import_map("assets")
        self.env.registry.clear_cache("assets")
        self.assertEqual(
            rendered.get(self.COLLIDING),
            own[self.COLLIDING],
            "the external table overrode where the page actually serves the module",
        )

    def test_the_external_table_is_the_floor(self):
        externals = dict(self._qweb._external_libs())
        self.assertIn("luxon", externals)
        rendered = self._rendered_import_map("assets")
        self.assertEqual(rendered.get("luxon"), externals["luxon"])

    @staticmethod
    def _fake_registry(**overrides):
        reg = SimpleNamespace(
            dynamic_children={},
            dynamic_bundle_names=set(),
            import_map_includes={},
            secondary_import_map_includes={},
            runtime_bundle_names=set(),
            exports=frozenset(),
            bundle_owners={},
        )
        for key, value in overrides.items():
            setattr(reg, key, value)
        reg.bundle_addon = lambda name: (
            reg.bundle_owners.get(name) or name.partition(".")[0]
        )
        children = {child for kids in reg.dynamic_children.values() for child in kids}
        reg.dynamic_bundle_names = set(reg.dynamic_bundle_names) | children
        reg.runtime_bundle_names = set(reg.runtime_bundle_names) | children
        return reg

    def test_the_fake_registry_carries_every_real_field(self):
        missing = set(EsmRegistry._fields) - set(vars(self._fake_registry()))
        self.assertEqual(
            sorted(
                missing
                - {
                    "bundles",
                    "standalone_bundles",
                    "external_libs",
                    "import_map_included_bundles",
                    "secondary_parents",
                    "secondary_bundle_names",
                }
            ),
            [],
            "the fake registry lacks a field the production code may read",
        )

    @staticmethod
    def _fake_ab(name, import_map, bridge_import_map=None, discovered=()):
        def get_native_module_data(with_bridges=True):
            data = {"import_map": dict(import_map)}
            if bridge_import_map is not None:
                data["bridge_import_map"] = dict(bridge_import_map)
            return data

        return SimpleNamespace(
            name=name,
            get_native_module_data=get_native_module_data,
            _bridges=SimpleNamespace(
                _discover_bridge_specifiers=lambda specs, ext, modules=None: (
                    list(discovered),
                    set(),
                ),
            ),
        )

    def _patch_registry(self, reg):
        stack = contextlib.ExitStack()
        for module in (
            "odoo.addons.base.models.ir_qweb_assets",
            "odoo.addons.base.models.ir_qweb_assets_import_map",
        ):
            stack.enter_context(patch(f"{module}.esm_registry", return_value=reg))
        return stack

    def test_dynamic_child_construction_policy(self):
        reg = self._fake_registry(
            dynamic_children={"parent": ("child.dyn", "child.plain")},
        )
        built = []

        def fake_get_asset_bundle(bundle, js, css, debug_assets, assets_params):
            built.append((bundle, debug_assets))
            return SimpleNamespace(name=bundle)

        ir_qweb = self._qweb
        with (
            self._patch_registry(reg),
            patch.object(
                type(ir_qweb),
                "_get_asset_bundle",
                side_effect=fake_get_asset_bundle,
            ),
        ):
            ir_qweb._get_dynamic_child_bundles("parent", None, debug_assets=False)
            self.assertEqual(built, [("child.dyn", True), ("child.plain", True)])
            built.clear()
            ir_qweb._get_dynamic_child_bundles("parent", None, debug_assets=True)
            self.assertEqual(built, [("child.dyn", True), ("child.plain", True)])

    def _child_pair(self):
        dyn = self._fake_ab("child.dyn", {"@a/x": "/a/static/src/x.js"})
        plain = self._fake_ab(
            "child.plain",
            {"@b/y": "/b/static/src/y.js", "@a/x": "/b/override.js"},
        )
        return dyn, plain

    def test_merge_child_import_maps(self):
        reg = self._fake_registry(dynamic_bundle_names={"child.dyn"})
        dyn, plain = self._child_pair()
        import_map = {}
        with self._patch_registry(reg):
            dynamic, specs = self._qweb._merge_child_import_maps(
                import_map, [dyn, plain]
            )
        self.assertEqual(dynamic, [dyn])
        self.assertEqual(
            import_map,
            {"@a/x": "/b/override.js", "@b/y": "/b/static/src/y.js"},
        )
        self.assertEqual(specs, {"@a/x", "@b/y"})

    def test_child_specifiers_are_collected_without_being_mapped(self):
        reg = self._fake_registry(dynamic_bundle_names={"child.dyn"})
        dyn, plain = self._child_pair()
        import_map = {"@keep/me": "/keep/static/src/me.js"}
        with self._patch_registry(reg):
            dynamic, specs = self._qweb._merge_child_import_maps(
                import_map, [dyn, plain], map_specifiers=False
            )
        self.assertEqual(dynamic, [dyn])
        self.assertEqual(specs, {"@a/x", "@b/y"})
        self.assertEqual(
            import_map,
            {"@keep/me": "/keep/static/src/me.js"},
            "a dynamic child's specifiers were mapped on the parent page",
        )

    def test_merge_includes_production_policy(self):
        reg = self._fake_registry(import_map_includes={"parent": ("inc.a",)})
        ir_qweb = self._qweb
        with (
            self._patch_registry(reg),
            patch.object(
                type(ir_qweb),
                "_get_native_module_data_cached",
                return_value={
                    "import_map": {"@inc/mod": "/inc/static/src/mod.js"},
                    "bridge_import_map": {
                        "@parent/kept": "/web/assets/esm/bridges/aa.js",
                        "@child/direct": "/web/assets/esm/bridges/bb.js",
                    },
                },
            ) as cached_mock,
        ):
            import_map = {"@child/direct": "/child/static/src/direct.js"}
            include_names = ir_qweb._merge_include_import_maps(
                "parent",
                import_map,
                None,
                debug_assets=False,
                resolve_bridges=False,
            )
        self.assertEqual(include_names, ("inc.a",))
        cached_mock.assert_called_once()
        self.assertEqual(import_map["@inc/mod"], "/inc/static/src/mod.js")
        self.assertEqual(import_map["@parent/kept"], "/web/assets/esm/bridges/aa.js")
        self.assertEqual(import_map["@child/direct"], "/child/static/src/direct.js")

    def test_merge_includes_debug_policy_resolves_bridges(self):
        reg = self._fake_registry(import_map_includes={"parent": ("inc.a",)})
        include_ab = self._fake_ab(
            "inc.a",
            {"@inc/mod": "/inc/static/src/mod.js"},
            discovered=["@web/core/registry", "unresolvable-bare"],
        )
        ir_qweb = self._qweb
        with (
            self._patch_registry(reg),
            patch.object(
                type(ir_qweb),
                "_get_asset_bundle",
                return_value=include_ab,
            ),
        ):
            import_map = {
                "unresolvable-bare": "data:text/javascript,shim",
            }
            ir_qweb._merge_include_import_maps(
                "parent",
                import_map,
                None,
                debug_assets=True,
                resolve_bridges=True,
            )
        self.assertEqual(import_map["@inc/mod"], "/inc/static/src/mod.js")
        self.assertEqual(
            import_map["@web/core/registry"], "/web/static/src/core/registry.js"
        )
        self.assertNotIn("unresolvable-bare", import_map)

    def test_merge_secondary_is_first_wins(self):
        reg = self._fake_registry(secondary_import_map_includes={"parent": ("sec.a",)})
        sec_ab = self._fake_ab(
            "sec.a",
            {
                "@parent/mod": "/web/assets/esm/bridges/shim.js",
                "@sec/new": "/sec/static/src/new.js",
            },
        )
        ir_qweb = self._qweb
        with (
            self._patch_registry(reg),
            patch.object(type(ir_qweb), "_get_asset_bundle", return_value=sec_ab),
        ):
            import_map = {"@parent/mod": "/parent/static/src/mod.js"}
            ir_qweb._merge_secondary_import_maps(
                "parent", import_map, None, debug_assets=False
            )
        self.assertEqual(
            import_map,
            {
                "@parent/mod": "/parent/static/src/mod.js",
                "@sec/new": "/sec/static/src/new.js",
            },
        )

    def test_resolve_bridge_specifiers_matrix(self):
        qweb = self._qweb
        base_map = {
            "@a/direct": "/a/static/src/direct.js",
            "@b/shimmed": "/web/assets/esm/bridges/cc.js",
            "@c/data": "data:text/javascript,x",
            "bare-unresolvable": "/web/assets/esm/bridges/dd.js",
        }

        import_map = dict(base_map)
        with self.assertLogs(f"{ASSET_ROOT}.bridge", level=logging.WARNING) as captured:
            resolved = qweb._add_import_map_bridge_urls(
                import_map,
                ["@a/direct", "@b/shimmed", "@c/data", "bare-unresolvable", "@d/new"],
                drop_unresolved=True,
            )
        self.assertEqual(len(captured.output), 3)
        self.assertEqual(import_map["@a/direct"], "/a/static/src/direct.js")
        self.assertNotIn("@a/direct", resolved)
        self.assertEqual(import_map["@b/shimmed"], "/b/static/src/shimmed.js")
        self.assertEqual(import_map["@c/data"], "/c/static/src/data.js")
        self.assertEqual(import_map["@d/new"], "/d/static/src/new.js")
        self.assertNotIn("bare-unresolvable", import_map)

        import_map = dict(base_map)
        qweb._add_import_map_bridge_urls(
            import_map,
            ["bare-unresolvable"],
            drop_unresolved=False,
        )
        self.assertEqual(
            import_map["bare-unresolvable"], "/web/assets/esm/bridges/dd.js"
        )


@tagged("web_unit", "web_assets")
class TestGeneratedAssetDomains(TransactionCase):
    def _make(self, name, url):
        return (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": name,
                    "url": url,
                    "type": "binary",
                    "res_model": "ir.ui.view",
                    "res_id": 0,
                    "public": True,
                    "raw": b"g4-domain-test",
                }
            )
        )

    def test_reuse_only_accepts_a_row_the_controller_would_serve(self):
        IrQweb = self.env["ir.qweb"]
        Attachment = self.env["ir.attachment"].sudo()
        content = "export const reuse_probe = 1;\n"
        url = f"/web/assets/esm/{cache_hash(content.encode())[:16]}/g4.reuse.esm.js"
        Attachment.search([("url", "=", url)]).unlink()

        admin = self.env.ref("base.user_admin")
        self.env["ir.attachment"].with_user(admin).create(
            {
                "name": "g4.reuse.esm.js",
                "url": url,
                "type": "binary",
                "res_model": "ir.ui.view",
                "res_id": 0,
                "public": True,
                "raw": content.encode(),
                "mimetype": "text/javascript",
            }
        )
        self.env.flush_all()

        self.assertEqual(IrQweb._save_esm_attachment("g4.reuse", content), url)
        servable = Attachment.search(Attachment._get_domain_generated_assets(url))
        self.assertTrue(
            servable,
            "reuse returned a URL the serving controller would answer 404 for",
        )

    def test_the_single_row_form_is_the_serving_predicate(self):
        row = self._make("g4.one.esm.js", "/web/assets/esm/feedface/g4.one.esm.js")
        Attachment = self.env["ir.attachment"].sudo()
        self.assertEqual(
            Attachment.search(Attachment._get_domain_generated_assets(row.url)),
            row,
        )
        row.create_uid = self.env.ref("base.user_admin").id
        self.env.flush_all()
        self.assertFalse(
            Attachment.search(Attachment._get_domain_generated_assets(row.url)),
            "a row this framework did not author is not a generated asset",
        )

    def test_esm_domain_narrows_generated_domain(self):
        Attachment = self.env["ir.attachment"]
        esm = self._make(
            "g4.bundle.esm.js", "/web/assets/esm/deadbeef/g4.bundle.esm.js"
        )
        sourcemap = self._make(
            "g4.bundle.esm.js.map", "/web/assets/esm/deadbeef/g4.bundle.esm.js.map"
        )
        meta = self._make(
            "g4.bundle.meta.json", "/web/assets/esm/deadbeef/g4.bundle.meta.json"
        )
        bridge = self._make("g4-shim.js", "/web/assets/esm/bridges/cafebabe.js")
        classic = self._make(
            "web.assets_g4.min.js", "/web/assets/1/web.assets_g4.min.js"
        )
        everything = esm | sourcemap | meta | bridge | classic

        generated = Attachment.sudo().search(Attachment._get_domain_generated_assets())
        self.assertEqual(
            everything & generated,
            everything,
            "the broad domain must match every generated row, classic included",
        )

        esm_only = Attachment.sudo().search(
            Attachment._get_domain_esm_generated_assets()
        )
        self.assertEqual(everything & esm_only, esm | sourcemap | meta | bridge)
        self.assertNotIn(
            classic,
            esm_only,
            "classic .min.js bundles have their own rotation and must never "
            "match the ESM-narrowed domain",
        )


@tagged("web_unit", "web_assets")
class TestSecondaryBundleSingletons(TransactionCase):
    def test_explicit_members_already_owned_by_the_page_are_shared(self):
        qweb = self.env["ir.qweb"]
        spec = "@example/shared"
        asset = SimpleNamespace(module_path=spec, url="/example/static/src/shared.js")
        bundle = SimpleNamespace(
            native_modules=[asset],
            get_native_module_data=lambda **kw: {"import_map": {spec: asset.url}},
            _bridges=SimpleNamespace(
                _discover_reachable_specifiers=lambda *a, **kw: ({}, set())
            ),
        )
        with patch.object(
            type(qweb), "_get_secondary_provider_specs", return_value={spec}
        ):
            shared, inlined = qweb._get_secondary_reach(
                "web.assets_tests", {}, ("web.assets_web",), sec_ab=bundle
            )
        self.assertEqual(shared, {spec})
        self.assertEqual(inlined, set())

    # A declared parent may be a page carrying five modules (room's booking
    # tablet) or one half of a split page (web.assets_frontend_minimal), so the
    # scope-less safe set, the intersection over every declared parent, is
    # allowed to be empty. The singletons are shared on a page that has them.
    FULL_PAGE = ("web.assets_web",)

    def _shared(self, page_scope=()):
        return self.env["ir.qweb"]._get_secondary_shared_specs(
            "web.assets_tests", None, page_scope
        )

    def test_safe_set_contains_core_singletons(self):
        shared = self._shared(self.FULL_PAGE)
        for spec in ("@web/core/browser/browser", "@web/env"):
            self.assertIn(
                spec,
                shared,
                msg=f"{spec} must be shared with the parent app bundle, not inlined",
            )

    def test_safe_set_subset_of_every_installed_parent(self):
        from odoo.tools.assets.esm_registry import esm_registry

        IrQweb = self.env["ir.qweb"]
        shared = self._shared()
        parents = esm_registry().secondary_parents.get("web.assets_tests", ())
        checked = 0
        for parent in parents:
            ab = IrQweb._get_asset_bundle(
                parent, js=True, css=False, debug_assets=False, assets_params=None
            )
            specs = set(ab.get_native_module_data(with_bridges=False)["import_map"])
            if not specs:
                continue
            checked += 1
            self.assertLessEqual(
                shared,
                specs,
                msg=(
                    f"shared specs not all registered by {parent!r}: "
                    f"{sorted(shared - specs)} — that page would get an "
                    "unresolvable alias"
                ),
            )
        self.assertGreater(checked, 0, "no installed parent bundle to check against")

    def test_non_secondary_bundle_has_no_shared_specs(self):
        self.assertEqual(
            self.env["ir.qweb"]._get_secondary_shared_specs("web.assets_web", None),
            frozenset(),
        )

    def test_stub_sources_read_the_loader(self):
        stubs = self.env["ir.qweb"]._get_secondary_parent_stubs(
            "web.assets_tests", None, self.FULL_PAGE
        )
        self.assertIn("@web/core/browser/browser", stubs)
        browser_stub = stubs["@web/core/browser/browser"]
        self.assertIn(
            'odoo.loader.modules.get("@web/core/browser/browser")',
            browser_stub,
        )
        self.assertIn("_m === undefined", browser_stub)
        self.assertIn("= _m.browser;", browser_stub)
        self.assertIn(" as browser", browser_stub)


@tagged("web_unit", "web_assets")
class TestSecondaryBundleSingletonsBuild(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        odoo_root = Path(odoo.__path__[0]).parent
        cls.esbuild = shutil.which("esbuild") or shutil.which(
            "esbuild", path=str(odoo_root / "node_modules" / ".bin")
        )

    def setUp(self):
        super().setUp()
        if not self.esbuild:
            self.skipTest("esbuild binary not found (run 'npm install').")

    def test_browser_is_aliased_not_inlined(self):
        IrQweb = self.env["ir.qweb"]
        ab = IrQweb._get_asset_bundle(
            "web.assets_tests",
            js=True,
            css=False,
            debug_assets=False,
            assets_params=None,
        )
        stubs = IrQweb._get_secondary_parent_stubs(
            "web.assets_tests", None, ("web.assets_web",)
        )
        self.assertTrue(stubs, "web.assets_tests should have shared-specifier stubs")

        inlined = ab.esbuild_native_bundle().code
        aliased = ab.esbuild_native_bundle(secondary_parent_stubs=stubs).code

        sig = "window.fetch.bind(window)"
        self.assertIn(sig, inlined, "control: the unaliased build inlines browser.js")
        self.assertNotIn(
            sig,
            aliased,
            "aliased build must NOT inline a second copy of browser.js",
        )
        self.assertIn(
            'odoo.loader.modules.get("@web/core/browser/browser")',
            aliased,
            "aliased build must reach browser via the loader singleton",
        )


@tagged("web_unit", "web_assets")
class TestSecondaryBundlePageScopeKey(TransactionCase):
    BUNDLE = "web.assets_tests"
    # rendered beside the parents, never declared as one
    SIBLING = "web.assets_backend"

    def _scope(self, rendered):
        req = SimpleNamespace(_esm_page_bundles=rendered)
        with patch.object(ir_qweb_assets, "request", req):
            return self.env["ir.qweb"]._get_esm_page_scope(self.BUNDLE)

    def test_only_declared_parents_key_the_variant(self):
        parents = esm_registry().secondary_parents[self.BUNDLE]
        self.assertIn("web.assets_frontend_lazy", parents)
        self.assertNotIn(self.SIBLING, parents)
        self.assertEqual(
            self._scope(("web.assets_frontend_lazy", self.SIBLING)),
            ("web.assets_frontend_lazy",),
            msg="a sibling bundle on the page is not a provider the secondary "
            "bundle was declared against; keying on it splits one variant "
            "into one per render order",
        )

    def test_the_key_follows_the_declaration_order(self):
        # Other addons can declare a parent before web's manifest is read.
        # The registry owns the order; rendering in reverse must not change it.
        parents = esm_registry().secondary_parents[self.BUNDLE]
        self.assertGreaterEqual(len(parents), 2)
        self.assertEqual(self._scope(tuple(reversed(parents))), parents)
        self.assertEqual(self._scope(parents), parents)

    def test_no_declared_parent_on_the_page_is_the_scope_less_variant(self):
        self.assertEqual(self._scope((self.SIBLING,)), ())


@tagged("web_unit", "web_assets")
class TestSecondaryBundleServesEveryPage(TransactionCase):
    BUNDLE = "web.assets_tests"
    BACKEND = "web.assets_web"
    FRONTEND = "web.assets_frontend_lazy"
    BRIDGE_RE = re.compile(r"\[asset\.loader\] bridge (\S+?): provider not registered")
    STRICT_RE = re.compile(
        r'"(\S+?)(?:" \+ ")? is not registered: the bundle importing'
    )

    def _pipeline_stubs(self, code):
        return set(self.BRIDGE_RE.findall(code)) | set(self.STRICT_RE.findall(code))

    def _pregenerate(self):
        IrQweb = self.env["ir.qweb"]
        IrQweb._get_native_module_nodes_cached(
            self.BUNDLE,
            assets_params=self.params,
            with_test_satellites=self.satellites,
            page_scope=(),
        )
        IrQweb._pregenerate_secondary_page_scopes(self.BUNDLE)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        odoo_root = Path(odoo.__path__[0]).parent
        cls.esbuild = shutil.which("esbuild") or shutil.which(
            "esbuild", path=str(odoo_root / "node_modules" / ".bin")
        )

    def setUp(self):
        super().setUp()
        if not self.esbuild:
            self.skipTest("esbuild binary not found (run 'npm install').")
        self.params = self.env["ir.asset"]._prepare_assets_params()
        self.satellites = self.env["ir.qweb"]._has_esm_test_satellites("")
        self.env.registry.clear_cache("assets")

    def _specs(self, bundle):
        return set(
            self.env["ir.qweb"]
            ._get_asset_bundle(
                bundle,
                js=True,
                css=False,
                debug_assets=False,
                assets_params=self.params,
            )
            .get_native_module_data(with_bridges=False)["import_map"]
        )

    def _artifact(self, post_nodes):
        scripts = [attrs for tag, attrs in post_nodes if attrs.get("data-bridge")]
        self.assertEqual(len(scripts), 1, post_nodes)
        url = scripts[0].get("src")
        self.assertTrue(
            url,
            msg="the page must get a compiled artifact by url, not the debug "
            "per-module fallback whose bare imports the page cannot resolve",
        )
        attachment = self.env["ir.attachment"].sudo().search([("url", "=", url)])
        self.assertEqual(len(attachment), 1, url)
        return url, attachment.raw.decode("utf-8")

    def _render_on_page(self, page_bundle, *, readonly):
        IrQweb = self.env["ir.qweb"]
        req = SimpleNamespace(_esm_page_bundles=(page_bundle,))
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(ir_qweb_assets, "request", req))
            if readonly:
                stack.enter_context(
                    contextlib.closing(self.env.cr.savepoint(flush=False))
                )
                stack.enter_context(patch.object(self.env.cr, "_readonly", True))
            _pre, post = IrQweb._get_native_module_nodes(self.BUNDLE)
        return self._artifact(post)

    def test_each_page_gets_an_artifact_its_import_map_can_serve(self):
        if not self._specs(self.FRONTEND) or not self._specs(self.BACKEND):
            self.skipTest("parent bundles resolved empty (web assets unavailable)")
        IrQweb = self.env["ir.qweb"]
        self._pregenerate()

        backend_url, backend_code = self._render_on_page(self.BACKEND, readonly=False)
        frontend_url, frontend_code = self._render_on_page(self.FRONTEND, readonly=True)

        self.assertNotEqual(backend_url, frontend_url)
        for page, code in (
            (self.BACKEND, backend_code),
            (self.FRONTEND, frontend_code),
        ):
            stubs = self._pipeline_stubs(code)
            self.assertTrue(stubs, f"no loader stubs in the {page} artifact")
            self.assertLessEqual(
                stubs,
                self._specs(page),
                msg=f"the {page} artifact aliases a module that page does not carry",
            )
        inlined = {
            page: set(
                IrQweb._get_secondary_inlined_reach(
                    self.BUNDLE, self.params, page_scope=(page,)
                )
            )
            for page in (self.BACKEND, self.FRONTEND)
        }
        self.assertLess(
            len(inlined[self.BACKEND]),
            len(inlined[self.FRONTEND]),
            "the backend page provides more of what the bundle reaches, so its "
            "artifact carries fewer modules of its own",
        )

    def test_the_backend_variant_does_not_evict_the_frontend_one(self):
        if not self._specs(self.FRONTEND) or not self._specs(self.BACKEND):
            self.skipTest("parent bundles resolved empty (web assets unavailable)")
        self._pregenerate()
        with self.assertNoLogs(f"{ASSET_ROOT}.fallback", level=logging.INFO):
            first_url, _ = self._render_on_page(self.FRONTEND, readonly=True)
            self._render_on_page(self.BACKEND, readonly=False)
            again_url, _ = self._render_on_page(self.FRONTEND, readonly=True)
        self.assertEqual(first_url, again_url)


@tagged("web_unit", "web_assets")
class TestPregenerationWarmsSecondaryPageScopes(TransactionCase):
    BUNDLE = "web.assets_tests"

    def test_every_installed_declared_parent_scope_is_built(self):
        IrQweb = self.env["ir.qweb"]
        seen = []

        def _cached(_self, bundle, assets_params=None, **kwargs):
            seen.append((bundle, kwargs.get("page_scope", ())))
            return [], []

        with (
            patch.object(type(IrQweb), "_get_native_module_nodes_cached", _cached),
            patch.object(
                type(IrQweb),
                "_get_bundles_to_pregenerate",
                lambda _self: ({self.BUNDLE}, set()),
            ),
        ):
            IrQweb._pregenerate_assets_bundles()

        installed = self.env["ir.asset"]._get_addons_installed()
        expected = {
            (self.BUNDLE, (parent,))
            for parent in esm_registry().secondary_parents[self.BUNDLE]
            if parent.partition(".")[0] in installed
        }
        self.assertTrue(expected)
        self.assertLessEqual(expected, set(seen))
        self.assertIn((self.BUNDLE, ()), seen)


@tagged("web_unit", "web_assets")
class TestLazyBundleRelativeImports(TransactionCase):
    @staticmethod
    def _module(module_path, raw_content, url=""):
        return SimpleNamespace(
            module_path=module_path,
            raw_content=raw_content,
            url=url or module_path.replace("@", "/", 1) + ".js",
        )

    def test_in_bundle_relative_import_passes(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/dir/a",
                'import { b } from "./b.js";\nimport { c } from "../c";\n',
            ),
            self._module("@mod/dir/b", "export const b = 1;\n"),
            self._module("@mod/c", "export const c = 1;\n"),
        ]
        self.assertEqual(get_escaping_relative_imports(modules), [])

    def test_escaping_relative_import_is_reported(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/dir/a",
                'import { svc } from "../../service.js";\n',
            ),
        ]
        self.assertEqual(
            get_escaping_relative_imports(modules),
            [("@mod/dir/a", "../../service.js", "@mod/service")],
        )

    def test_index_long_form_is_a_member(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/a",
                'import { x } from "./widget/index.js";\n',
            ),
            self._module(
                "@mod/widget",
                "export const x = 1;\n",
                url="/mod/static/src/widget/index.js",
            ),
        ]
        self.assertEqual(get_escaping_relative_imports(modules), [])

    def test_bare_specifiers_are_ignored(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/a",
                'import { registry } from "@web/core/registry";\n',
            ),
        ]
        self.assertEqual(get_escaping_relative_imports(modules), [])

    def test_relative_import_from_an_index_module_is_a_member(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/chart",
                'import "./plugins/core.js";\nexport * from "./menu/link.js";\n',
                url="/mod/static/src/chart/index.js",
            ),
            self._module(
                "@mod/chart/plugins/core",
                "export const core = 1;\n",
                url="/mod/static/src/chart/plugins/core.js",
            ),
            self._module(
                "@mod/chart/menu/link",
                "export const link = 1;\n",
                url="/mod/static/src/chart/menu/link.js",
            ),
        ]
        self.assertEqual(get_escaping_relative_imports(modules), [])

    def test_relative_import_into_static_lib_is_a_member(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/passkey_lib",
                'import { start } from "../lib/vendored.js";\n'
                "export const lib = { start };\n",
                url="/mod/static/src/passkey_lib.js",
            ),
            self._module(
                "@mod/../lib/vendored",
                "export function start() {}\n",
                url="/mod/static/lib/vendored.js",
            ),
        ]
        self.assertEqual(get_escaping_relative_imports(modules), [])

    def test_index_module_escaping_its_directory_is_still_reported(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        modules = [
            self._module(
                "@mod/chart",
                'import { svc } from "../service.js";\n',
                url="/mod/static/src/chart/index.js",
            ),
        ]
        self.assertEqual(
            get_escaping_relative_imports(modules),
            [("@mod/chart", "../service.js", "@mod/service")],
        )

    def test_payload_guard_raises_with_details(self):
        from odoo.addons.base.models.ir_qweb_assets_esbuild import EsbuildBundleError

        fake_bundle = SimpleNamespace(
            name="mod.lazy_bundle",
            native_modules=[
                self._module(
                    "@mod/dir/a",
                    'import { svc } from "../../service.js";\n',
                ),
            ],
        )
        with self.assertRaises(EsbuildBundleError) as caught:
            self.env["ir.qweb"]._check_lazy_bundle_relative_imports(fake_bundle)
        message = str(caught.exception)
        self.assertIn("mod.lazy_bundle", message)
        self.assertIn("@mod/dir/a", message)
        self.assertIn("../../service.js", message)
        self.assertIn("@mod/service", message)


@tagged("post_install", "-at_install", "web_assets")
class TestDynamicBundleIntegrity(TransactionCase):
    def _dynamic_bundle_names(self):
        from odoo.tools.assets.esm_registry import esm_registry

        registry = esm_registry()
        names = sorted(registry.runtime_bundle_names)
        self.assertTrue(
            names,
            "the ESM registry declares no runtime bundle at all — the "
            "sweep would pass having checked nothing",
        )
        self.assertEqual(
            sorted(registry.dynamic_bundle_names - registry.runtime_bundle_names),
            [],
            "a dynamic child outside the runtime set: the route would decline "
            "to serve it as ESM while this sweep verified it",
        )
        return names

    def _assert_sweep_saw_assets(self, populated, names):
        self.assertGreater(
            populated,
            1,
            f"only {populated} of {len(names)} dynamic bundles resolved to "
            "any file. Either no module owning one is installed, or this "
            "ran before their assets were queryable — - either way the "
            "sweep proves nothing. Widen INSTALL in asset_lint.yml, or "
            "check that this class still runs post_install.",
        )

    FRONTEND_REACH_EXEMPT = set()

    def test_a_frontend_loadable_bundle_reaches_nothing_backend_only(self):
        registry = esm_registry()
        IrQweb = self.env["ir.qweb"]
        parent_name = "web.assets_frontend"
        parent = IrQweb._get_asset_bundle(
            parent_name, js=True, css=False, debug_assets=True, assets_params=None
        )
        available = {a.module_path for a in parent.native_modules} | set(
            external_libs()
        )
        self.assertTrue(available, f"{parent_name} resolved to nothing")

        children = [
            child
            for parent_bundle, kids in registry.dynamic_children.items()
            for child in kids
            if parent_bundle == parent_name
        ]
        self.assertTrue(children, f"no dynamic child declared on {parent_name}")

        unreachable = []
        for child_name in sorted(children):
            child = IrQweb._get_asset_bundle(
                child_name, js=True, css=False, debug_assets=True, assets_params=None
            )
            if not child.native_modules:
                continue
            own = {a.module_path for a in child.native_modules}
            discovered, _ext = child._bridges._discover_bridge_specifiers(
                own, set(external_libs())
            )
            unreachable.extend(
                f"{child_name} -> {spec}"
                for spec in sorted(set(discovered) - available)
                if (child_name, spec) not in self.FRONTEND_REACH_EXEMPT
            )
        self.assertFalse(
            unreachable,
            f"lazy children of {parent_name} needing modules that page never "
            f"registers; their bridges resolve to undefined:\n  "
            + "\n  ".join(unreachable),
        )

    def test_every_installed_dynamic_bundle_is_self_contained(self):
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        IrQweb = self.env["ir.qweb"]
        names = self._dynamic_bundle_names()
        escapes = []
        populated = 0
        for bundle_name in names:
            asset_bundle = IrQweb._get_asset_bundle(
                bundle_name,
                js=True,
                css=False,
                debug_assets=True,
                assets_params=None,
            )
            populated += bool(asset_bundle.native_modules)
            escapes.extend(
                (bundle_name, *escape)
                for escape in get_escaping_relative_imports(asset_bundle.native_modules)
            )
        self._assert_sweep_saw_assets(populated, names)
        self.assertFalse(
            escapes,
            "Per-file-served bundles with relative imports escaping the "
            f"bundle (use the bare '@addon/...' specifier instead): {escapes}",
        )

    def _compiled_runtime_bundles(self):
        IrQweb = self.env["ir.qweb"]
        installed = self.env["ir.asset"]._get_addons_installed()
        names = [
            name
            for name in self._dynamic_bundle_names()
            if name.partition(".")[0] in installed
            and IrQweb._is_runtime_child_compiled(name)
            and IrQweb._get_asset_bundle(
                name, js=True, css=False, debug_assets=True, assets_params=None
            ).native_modules
        ]
        self.assertTrue(names, "no installed runtime bundle carries a module")
        # under a test the page carries web_tour.automatic (web.assets_tests):
        # such a child compiles to nothing and is served as bare specifiers
        names = [
            name
            for name in names
            if not IrQweb._get_esm_bundle_payload(name, debug_assets=False).get(
                "carried"
            )
        ]
        self.assertTrue(names, "every runtime bundle is carried by the test page")
        return names

    def test_a_child_the_test_page_carries_is_served_as_bare_specifiers(self):
        IrQweb = self.env["ir.qweb"]
        payload = IrQweb._get_esm_bundle_payload(
            "web_tour.automatic", debug_assets=False, page="web.assets_web"
        )
        self.assertTrue(payload.get("carried"))
        self.assertNotIn("esm_url", payload)
        self.assertIn(
            "@web_tour/js/tour_automatic/tour_automatic", payload["specifiers"]
        )
        self.assertFalse(
            [spec for spec in payload["import_map"] if spec.startswith("@web_tour/")],
            "a carried child maps none of its modules: the page's map serves them",
        )

    def _metafile_inputs(self, url):
        meta_url = url.removesuffix(".esm.js") + ".meta.json"
        row = (
            self.env["ir.attachment"]
            .sudo()
            .search([("url", "=", meta_url), ("public", "=", True)], limit=1)
        )
        self.assertTrue(row, f"no metafile beside {url}")
        return set(json.loads(row.raw.decode())["inputs"])

    def test_a_runtime_bundle_is_served_as_one_compiled_url(self):
        IrQweb = self.env["ir.qweb"]
        for name in self._compiled_runtime_bundles():
            payload = IrQweb._get_esm_bundle_payload(name, debug_assets=False)
            url = payload.get("esm_url")
            self.assertTrue(url, f"{name}: no compiled artifact in the payload")
            self.assertTrue(url.startswith("/web/assets/esm/"), (name, url))
            self.assertIsNone(
                payload["template_url"],
                f"{name}: templates ride inside the compiled bundle",
            )
            raw = {
                value
                for value in payload["import_map"].values()
                if "/static/src/" in value
            }
            self.assertFalse(
                raw,
                f"{name}: a compiled child must not map any module to a raw "
                f"source file: {sorted(raw)[:3]}",
            )
            self.assertTrue(
                self.env["ir.attachment"]
                .sudo()
                .search_count([("url", "=", url), ("public", "=", True)]),
                f"{name}: {url} is not persisted",
            )

    def test_a_runtime_bundle_resolves_every_parent_module_through_a_stub(self):
        from odoo.tools.assets.esbuild import module_specifiers
        from odoo.tools.assets.esm_graph import get_escaping_relative_imports

        IrQweb = self.env["ir.qweb"]
        registry = esm_registry()
        installed = self.env["ir.asset"]._get_addons_installed()
        problems = []
        checked = 0
        for name in self._compiled_runtime_bundles():
            parents = [
                parent
                for parent, children in registry.dynamic_children.items()
                if name in children and parent.partition(".")[0] in installed
            ]
            # the set the group build itself stubs against: on a test page the
            # secondary satellites (web.assets_tests) register what they
            # inline for that page, so a child neither carries nor bridges it
            parent_specs = set(
                IrQweb._get_runtime_parent_specs(
                    tuple(parents), None, IrQweb._has_esm_test_satellites("")
                )
            )
            child = IrQweb._get_asset_bundle(
                name, js=True, css=False, debug_assets=True
            )
            own = [a for a in child.native_modules if a.module_path not in parent_specs]
            own_specs = {n for a in own for n in module_specifiers(a)}
            discovered, _ext = child._bridges._discover_bridge_specifiers(
                own_specs, set(external_libs()), modules=own
            )
            reachable = (
                set(discovered)
                | {
                    resolved
                    for _m, _s, resolved in get_escaping_relative_imports(
                        own, own_specs
                    )
                }
            ) & parent_specs
            url = IrQweb._get_esm_bundle_payload(name, debug_assets=False)["esm_url"]
            code = "\n".join(
                att.raw.decode()
                for att in self.env["ir.attachment"]
                .sudo()
                .search([("url", "=like", url.rpartition("/")[0] + "/%.js")])
            )
            for spec in sorted(reachable):
                checked += 1
                if f'odoo.loader.modules.get("{spec}")' not in code:
                    problems.append(f"{name}: {spec} is not read from the loader")
            problems.extend(
                f"{name}: registers {asset.module_path}, which its parent owns"
                for asset in child.native_modules
                if asset.module_path in parent_specs
                and f'"{asset.module_path}":' in code
            )
        self.assertGreater(checked, 0, "no child reached a parent module at all")
        self.assertFalse(
            problems,
            "a module the page bundle already evaluated would be evaluated "
            "again by the child (singleton split):\n  " + "\n  ".join(problems),
        )

    def test_the_debug_payload_still_serves_per_file(self):
        IrQweb = self.env["ir.qweb"]
        name = self._compiled_runtime_bundles()[0]
        payload = IrQweb._get_esm_bundle_payload(name, debug_assets=True)
        self.assertNotIn("esm_url", payload)
        self.assertTrue(payload["specifiers"])

    def test_a_page_never_inlines_what_a_dynamic_child_owns(self):
        IrQweb = self.env["ir.qweb"]
        registry = esm_registry()
        installed = self.env["ir.asset"]._get_addons_installed()
        params = self.env["ir.asset"]._prepare_assets_params()
        root = Path(odoo.__path__[0]).parent
        owned = {}
        for child_name in registry.dynamic_bundle_names:
            if child_name.partition(".")[0] not in installed:
                continue
            child = IrQweb._get_asset_bundle(
                child_name, js=True, css=False, debug_assets=True
            )
            for asset in child.native_modules:
                if asset._filename:
                    owned[posixpath.relpath(asset._filename, root)] = child_name
        inlined = []
        checked = 0
        for page in sorted(registry.dynamic_children):
            if page.partition(".")[0] not in installed:
                continue
            if page in registry.import_map_includes:
                continue
            bundle = IrQweb._get_asset_bundle(
                page, js=True, css=False, assets_params=params
            )
            if not bundle.native_modules:
                continue
            own = {
                posixpath.relpath(a._filename, root)
                for a in bundle.native_modules
                if a._filename
            }
            children = IrQweb._get_dynamic_child_bundles(
                page, params, debug_assets=False
            )
            dyn, stubs = IrQweb._get_esbuild_child_externals(
                page, bundle, params, children
            )
            result = bundle.esbuild_native_bundle(
                dynamic_child_specs=dyn, secondary_parent_stubs=stubs or None
            )
            checked += 1
            inlined.extend(
                f"{page} inlines {path}, owned by {owned[path]}"
                for path in json.loads(result.metafile)["inputs"]
                if path in owned and path not in own
            )
        self.assertGreater(checked, 0)
        self.assertFalse(
            inlined,
            "declare the child under every page family whose code reaches it:\n  "
            + "\n  ".join(inlined),
        )

    def test_every_installed_dynamic_bundle_serves_a_payload(self):
        IrQweb = self.env["ir.qweb"]
        names = self._dynamic_bundle_names()
        failures = []
        populated = 0
        for bundle_name in names:
            try:
                payload = IrQweb._get_esm_bundle_payload(
                    bundle_name, debug_assets=False
                )
            except Exception as exc:
                failures.append(f"{bundle_name}: {type(exc).__name__}: {exc}")
                continue
            populated += bool(payload["specifiers"])
        self.assertFalse(
            failures,
            "Dynamic child bundles whose /web/bundle payload does not "
            f"build; each is an HTTP 500 on the route: {failures}",
        )
        self._assert_sweep_saw_assets(populated, names)


@tagged("web_unit", "web_assets")
class TestTestSatelliteGating(TransactionCase):
    BUNDLE = "web.assets_frontend"

    @property
    def _qweb(self):
        return self.env["ir.qweb"]

    def _rendered_import_map(self, debug=""):
        self.env.registry.clear_cache("assets")
        pre, _post = self._qweb._get_native_module_nodes(self.BUNDLE, debug=debug)
        self.env.registry.clear_cache("assets")
        for tag, attrs in pre:
            if tag == "script" and attrs.get("type") == "importmap":
                return json.loads(attrs["text"])["imports"]
        return {}

    @staticmethod
    def _test_specifiers(import_map):
        return sorted(s for s in import_map if "/../tests/" in s)

    def test_condition_matches_the_template(self):
        rendered = self._qweb._has_esm_test_satellites
        with odoo.tools.config.patch(test_enable=False):
            for debug in ("", None, False, "1", "assets", "assets,qweb"):
                self.assertFalse(rendered(debug), f"debug={debug!r}")
            for debug in ("tests", "assets,tests", "1,tests"):
                self.assertTrue(rendered(debug), f"debug={debug!r}")
        with odoo.tools.config.patch(test_enable=True):
            self.assertTrue(rendered(""))

    def test_prod_page_carries_no_test_specifiers(self):
        secondaries = esm_registry().secondary_import_map_includes
        self.assertIn(
            self.BUNDLE,
            secondaries,
            f"{self.BUNDLE} no longer declares secondary_import_map_includes; "
            "pick another parent or drop this test",
        )
        with odoo.tools.config.patch(test_enable=False):
            import_map = self._rendered_import_map(debug="")
        self.assertTrue(import_map, "the bundle rendered no import map at all")
        self.assertEqual(
            self._test_specifiers(import_map),
            [],
            "test-bundle specifiers reached a production page's import map",
        )

    def test_test_mode_still_carries_them(self):
        with odoo.tools.config.patch(test_enable=False):
            without = self._rendered_import_map(debug="")
        with odoo.tools.config.patch(test_enable=True):
            with_them = self._rendered_import_map(debug="")
        self.assertTrue(
            self._test_specifiers(with_them),
            "test mode no longer merges the satellites; the guard over-fired",
        )
        self.assertLess(
            len(without),
            len(with_them),
            "gating the merge changed nothing — the guard is not wired",
        )


@tagged("web_unit", "web_assets")
class TestEsmPersistenceDegradation(TransactionCase):
    def _node(self, exc, raise_on_decline=False):
        IrQweb = self.env["ir.qweb"]
        with patch.object(type(IrQweb), "_save_esm_attachment", side_effect=exc):
            return IrQweb._prepare_esm_script_node(
                "b.x", "export const x = 1;", {}, raise_on_decline=raise_on_decline
            )

    def test_a_readonly_cursor_inlines_the_code(self):
        tag, attrs = self._node(ReadOnlySqlTransaction("readonly"))
        self.assertEqual(tag, "script")
        self.assertEqual(attrs["text"], "export const x = 1;")
        self.assertNotIn("src", attrs)

    def test_any_other_persistence_failure_also_inlines(self):
        for exc in (ValueError("filestore write failed"), OSError("ENOSPC")):
            with self.subTest(exc=type(exc).__name__):
                tag, attrs = self._node(exc)
                self.assertEqual(tag, "script")
                self.assertEqual(attrs["text"], "export const x = 1;")

    def test_a_declining_caller_still_gets_the_fallback_signal(self):
        for exc in (ReadOnlySqlTransaction("ro"), ValueError("boom")):
            with self.subTest(exc=type(exc).__name__):
                with self.assertRaises(_EsmFallbackError):
                    self._node(exc, raise_on_decline=True)

    def test_both_decline_signals_share_one_contract(self):
        self.assertTrue(issubclass(_EsmFallbackError, _BuildDeclined))
        self.assertTrue(issubclass(_StandaloneBundleDeclined, _BuildDeclined))


@tagged("-at_install", "post_install", "web_assets")
class TestEsmConcurrentPublication(TransactionCase):
    def test_the_lock_sets_the_isolation_level_and_the_timeout_on_a_fresh_cursor(self):
        with db_connect(self.env.cr.dbname).cursor() as cr:
            self.env["ir.qweb"]._lock_esm_publication(cr, "1500ms")
            cr.execute("SHOW transaction_isolation")
            self.assertEqual(cr.fetchone()[0], "read committed")
            cr.execute("SHOW lock_timeout")
            self.assertEqual(cr.fetchone()[0], "1500ms")
            cr.rollback()

    def test_concurrent_publishers_recheck_after_the_preceding_commit(self):
        qweb = self.env["ir.qweb"]
        db = db_connect(self.env.cr.dbname)
        url = "/web/assets/esm/concurrent-test/publication.esm.js"
        errors = []
        vals = [
            {
                "url": url,
                "name": "publication.esm.js",
                "raw": b"export {};",
                "company_id": False,
            }
        ]

        def publish():
            try:
                qweb._save_esm_attachment_rows_autonomously(vals)
            except Exception as exc:
                errors.append(exc)

        def remove_rows():
            with db.cursor() as cr:
                cr.execute("DELETE FROM ir_attachment WHERE url = %s", (url,))
                cr.commit()

        remove_rows()
        self.addCleanup(remove_rows)
        with self.assertLogs(f"{ASSET_ROOT}.attach", level=logging.DEBUG) as logged:
            with db.cursor() as holder:
                holder.execute(
                    "SELECT pg_advisory_xact_lock(hashtext('esm:publication'))"
                )
                writers = [threading.Thread(target=publish) for _ in range(2)]
                for writer in writers:
                    writer.start()
                try:
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline:
                        holder.execute(
                            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' "
                            "AND objid = hashtext('esm:publication')::oid "
                            "AND database = (SELECT oid FROM pg_database "
                            "WHERE datname = current_database()) AND NOT granted"
                        )
                        if holder.fetchone()[0] == 2:
                            break
                        time.sleep(0.01)
                    else:
                        self.fail(
                            "both publishers must wait before checking stored URLs"
                        )
                finally:
                    holder.rollback()
                    for writer in writers:
                        writer.join(6)
            self.assertFalse(any(writer.is_alive() for writer in writers))
            self.assertEqual(errors, [])
        self.assertEqual(
            sum("event=publication_acquired" in line for line in logged.output), 2
        )
        with db.cursor() as cr:
            cr.execute("SELECT count(*) FROM ir_attachment WHERE url = %s", (url,))
            self.assertEqual(
                cr.fetchone()[0], 1, "the second writer must reuse the row"
            )


@tagged("web_unit", "web_assets")
class TestEsmAttachmentRowsAreNotDuplicated(TransactionCase):
    def test_the_writing_cursor_re_checks_the_urls(self):
        IrQweb = self.env["ir.qweb"]
        url = "/web/assets/esm/dup0/g4.dup.esm.js"
        self.env["ir.attachment"].sudo().search([("url", "=", url)]).unlink()
        vals = [{"url": url, "name": "g4.dup.esm.js"}, {"url": "/other", "name": "o"}]

        self.assertEqual(
            IrQweb._drop_rows_already_present(self.env.cr, vals),
            vals,
            "nothing is present yet, so nothing is dropped",
        )

        self.env["ir.attachment"].sudo().create(
            {
                "name": "g4.dup.esm.js",
                "url": url,
                "type": "binary",
                "res_model": "ir.ui.view",
                "res_id": 0,
                "public": True,
                "raw": b"x",
            }
        )
        self.env.flush_all()
        self.assertEqual(
            IrQweb._drop_rows_already_present(self.env.cr, vals),
            [vals[1]],
            "a URL already on the writing cursor must not be inserted again",
        )


@tagged("web_unit", "web_assets")
class TestPageScopedScriptsAreRenderedOnce(TransactionCase):
    def _pre(self, bundle, specs):
        IrQweb = self.env["ir.qweb"]
        return [
            (
                "script",
                {
                    "type": "importmap",
                    "data-bundle": bundle,
                    "text": json.dumps({"imports": {s: f"/{s}" for s in specs}}),
                },
            ),
            IrQweb._prepare_loader_shim_node(bundle),
            ("script", {"type": "module", "src": "/x.js"}),
        ]

    def _kinds(self, nodes):
        IrQweb = self.env["ir.qweb"]
        return [
            "importmap"
            if IrQweb._is_import_map_node(n)
            else "shim"
            if IrQweb._is_loader_shim_node(n)
            else "other"
            for n in nodes
        ]

    def test_the_second_bundle_keeps_neither_the_map_nor_the_shim(self):
        IrQweb = self.env["ir.qweb"]
        req = SimpleNamespace()
        with patch.object(ir_qweb_assets, "request", req):
            first = IrQweb._dedup_request_page_scripts("a", self._pre("a", ["@a/one"]))
            second = IrQweb._dedup_request_page_scripts("b", self._pre("b", ["@a/one"]))
            self.assertTrue(getattr(req, "_esm_import_map_rendered", False))
        self.assertEqual(self._kinds(first), ["importmap", "shim", "other"])
        self.assertEqual(self._kinds(second), ["other"])

    def test_a_specifier_the_first_bundle_lacks_is_mapped_by_the_second(self):
        IrQweb = self.env["ir.qweb"]
        logger = get_asset_logger("esm")
        with patch.object(ir_qweb_assets, "request", SimpleNamespace()):
            IrQweb._dedup_request_page_scripts("a", self._pre("a", ["@a/one"]))
            with self.assertNoLogs(logger.name, level="WARNING"):
                second = IrQweb._dedup_request_page_scripts(
                    "b", self._pre("b", ["@a/one", "@b/only"])
                )
        self.assertEqual(self._kinds(second), ["importmap", "other"])
        self.assertEqual(
            IrQweb._get_import_map_specs(second),
            frozenset({"@b/only"}),
            "a page carrying two ESM bundles must be able to resolve every "
            "specifier either declares: @a/one is already mapped so the later "
            "map omits it, and @b/only would be unresolvable if the map were "
            "dropped wholesale as it once was",
        )

    def test_a_superset_page_logs_no_warning(self):
        IrQweb = self.env["ir.qweb"]
        logger = get_asset_logger("esm")
        with patch.object(ir_qweb_assets, "request", SimpleNamespace()):
            IrQweb._dedup_request_page_scripts("a", self._pre("a", ["@a/one", "@b/x"]))
            with self.assertNoLogs(logger.name, level="WARNING"):
                IrQweb._dedup_request_page_scripts("b", self._pre("b", ["@a/one"]))


@tagged("web_unit", "web_assets")
class TestAssetLinkCacheKey(TransactionCase):
    def _observe(self, **kwargs):
        IrQweb = self.env["ir.qweb"]
        seen = {}
        real = type(IrQweb)._get_asset_links_cached

        def spy(self_, bundle, **kw):
            seen.update(kw)
            return real(self_, bundle, **kw)

        with patch.object(type(IrQweb), "_get_asset_links_cached", spy):
            IrQweb._get_asset_links("web.assets_web", **kwargs)
        return seen

    def test_a_js_only_lookup_pins_both_css_knobs_off(self):
        seen = self._observe(css=False, js=True, autoprefix=True)
        self.assertFalse(seen["rtl"])
        self.assertFalse(seen["autoprefix"])

    def test_a_css_lookup_still_carries_them(self):
        seen = self._observe(css=True, js=False, autoprefix=True)
        self.assertTrue(seen["autoprefix"])
        self.assertEqual(seen["rtl"], self.env["ir.qweb"]._is_rtl_language())

    def test_a_js_only_lookup_does_not_consult_the_language(self):
        IrQweb = self.env["ir.qweb"]
        with patch.object(
            type(IrQweb),
            "_is_rtl_language",
            side_effect=AssertionError("no language lookup for a JS-only call"),
        ):
            IrQweb._get_asset_links("web.assets_web", css=False, js=True)


@tagged("post_install", "-at_install", "web_assets")
class TestBundleDescriptorFormat(HttpCase):
    def _descriptor(self, bundle_name):
        response = self.url_open(f"/web/bundle/{bundle_name}")
        self.assertEqual(response.status_code, 200, bundle_name)
        return response.json()

    def test_cold_runtime_descriptor_persists_its_asset(self):
        attachments = self.env["ir.attachment"]
        attachments.search(
            attachments._get_domain_generated_assets(url_pattern="/web/assets/esm/%")
        ).unlink()
        self.env.registry.clear_cache("assets")
        response = self.url_open(
            "/web/bundle/web_tour.interactive?debug=tests&page=web.assets_frontend"
        )
        self.assertEqual(response.status_code, 200)
        asset_url = response.json()["esm_url"]
        self.assertTrue(asset_url)
        asset = self.url_open(asset_url)
        self.assertEqual(asset.status_code, 200, asset_url)
        self.assertTrue(asset.content)

    def test_an_esm_bundle_is_served_in_the_esm_envelope(self):
        registry = esm_registry()
        for name in ("web.assets_frontend", "web.assets_frontend_lazy"):
            self.assertIn(
                name,
                registry.bundles,
                "fixture assumption: this bundle has an ESM build",
            )
            self.assertNotIn(
                name,
                registry.runtime_bundle_names,
                "fixture assumption: and nobody declared it a runtime bundle — "
                "which is exactly the case the old predicate got wrong",
            )
            payload = self._descriptor(name)
            self.assertIsInstance(
                payload, dict, f"{name} was served in the classic (list) envelope"
            )
            self.assertTrue(payload.get("is_esm"), name)
            self.assertTrue(payload.get("specifiers"), name)

    def test_a_runtime_bundle_envelope_names_its_compiled_url(self):
        IrQweb = self.env["ir.qweb"]
        installed = set(
            self.env["ir.module.module"]
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        checked = 0
        for name in sorted(esm_registry().runtime_bundle_names):
            if name.split(".", 1)[0] not in installed:
                continue
            if not IrQweb._is_runtime_child_compiled(name):
                continue
            payload = self._descriptor(name)
            if (
                isinstance(payload, list)
                or not payload.get("specifiers")
                or payload.get("carried")
            ):
                continue
            members = IrQweb._get_asset_bundle(
                name, js=True, css=False, debug_assets=True
            ).native_modules
            if all(asset.url in set(external_libs().values()) for asset in members):
                continue
            checked += 1
            self.assertTrue(payload.get("esm_url"), name)
            asset = self.url_open(payload["esm_url"])
            self.assertEqual(asset.status_code, 200, payload["esm_url"])
            self.assertTrue(asset.content, name)
            self.assertFalse(
                [f for f in payload["files"] if f.get("src") is None],
                f"{name}: the route lists a file with no URL",
            )
        self.assertGreater(checked, 0)

    def test_a_library_only_bundle_is_served_classic(self):
        IrQweb = self.env["ir.qweb"]
        installed = self.env["ir.asset"]._get_addons_installed()
        checked = 0
        for name in sorted(esm_registry().runtime_bundle_names):
            if name.partition(".")[0] not in installed:
                continue
            bundle = IrQweb._get_asset_bundle(
                name, js=True, css=False, debug_assets=True
            )
            if bundle.native_modules or bundle.templates or not bundle.javascripts:
                continue
            checked += 1
            payload = self._descriptor(name)
            self.assertIsInstance(
                payload,
                list,
                f"{name} carries only classic scripts and was served an ESM "
                "envelope with nothing in it",
            )
            self.assertTrue([e for e in payload if e.get("type") == "script"], name)
        self.assertGreater(checked, 0, "fixture: a library-only runtime bundle")

    def test_no_bundle_is_served_classic_while_naming_an_esm_chunk(self):
        installed = set(
            self.env["ir.module.module"]
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        offenders = []
        for name in sorted(esm_registry().bundles):
            if name.split(".", 1)[0] not in installed:
                continue
            payload = self._descriptor(name)
            if isinstance(payload, dict):
                continue
            scripts = [e for e in payload if e.get("type") == "script"]
            loadable = [e for e in scripts if e.get("src") and ".esm." not in e["src"]]
            if scripts and not loadable:
                offenders.append(name)
        self.assertFalse(
            offenders,
            f"served in the classic envelope with no loadable script: {offenders}",
        )


@tagged("-at_install", "post_install", "web_assets")
class TestPerFileSecondaryOnAPage(TransactionCase):
    # a page-scoped secondary whose compiled file could not be saved (a
    # read-only test cursor) is served per file next to the page's compiled
    # bundles; what those bundles carry must reach it through bridges, or the
    # page evaluates a second copy (`Duplicate add for key "tools" in
    # "debug_section"` on /?debug=tests, from debug_menu -> debug_menu_basic)
    BUNDLE = "web.assets_tests"
    PAGE = ("web.assets_frontend_minimal", "web.assets_frontend_lazy")

    def _debug_map(self, page_scope):
        IrQweb = self.env["ir.qweb"]
        params = self.env["ir.asset"]._prepare_assets_params()
        bundle = IrQweb._get_asset_bundle(
            self.BUNDLE, js=True, css=False, debug_assets=False, assets_params=params
        )
        native_data = IrQweb._get_native_module_data_cached(
            self.BUNDLE, assets_params=params
        )
        import_map, _bridges = IrQweb._get_esm_import_map_debug(
            self.BUNDLE,
            bundle,
            native_data,
            params,
            debug_assets=False,
            with_test_satellites=False,
            page_scope=page_scope,
        )
        provided = IrQweb._get_secondary_provider_specs(
            self.BUNDLE, params, self.PAGE
        ) - set(native_data["import_map"])
        return import_map, provided

    _BRIDGE = ("/web/assets/esm/bridges/", "data:")

    def test_what_the_page_carries_is_bridged_not_served_again(self):
        # what the tests bundle reaches AND the page carries -- derived from
        # the install, not a fixed module name, since which page modules the
        # bundle's test tours reach depends on what is installed
        import_map, provided = self._debug_map(self.PAGE)
        reached = sorted(provided & set(import_map))
        self.assertTrue(
            reached, "fixture: the tests bundle reaches modules the page carries"
        )
        served_again = [
            s for s in reached if not import_map[s].startswith(self._BRIDGE)
        ]
        self.assertEqual(
            served_again,
            [],
            "a page-carried module served per file is a second copy of it",
        )

    def test_a_page_scope_is_what_bridges_the_page_carried_modules(self):
        # without the page scope the per-file branch does not bridge to the
        # page's copies; at least one module the scoped map bridges is served
        # per file (its own src url) unscoped -- the duplication the scope fixes
        scoped, provided = self._debug_map(self.PAGE)
        unscoped, _ = self._debug_map(())
        bridged_by_scope = {
            s for s in provided & set(scoped) if scoped[s].startswith(self._BRIDGE)
        }
        self.assertTrue(
            bridged_by_scope, "fixture: the page scope bridges page-carried modules"
        )
        served_raw_unscoped = {
            s
            for s in bridged_by_scope
            if s in unscoped and not unscoped[s].startswith(self._BRIDGE)
        }
        self.assertTrue(
            served_raw_unscoped,
            "the page scope must change the outcome: a module it bridges is "
            "served per file without it",
        )


@tagged("-at_install", "post_install", "web_assets")
class TestPageBundleExportSurface(TransactionCase):
    BUNDLE = "web.assets_web"

    def _exported(self):
        IrQweb = self.env["ir.qweb"]
        params = self.env["ir.asset"]._prepare_assets_params()
        bundle = IrQweb._get_asset_bundle(self.BUNDLE, css=False, js=True)
        children = IrQweb._get_dynamic_child_bundles(
            self.BUNDLE, params, debug_assets=False
        )
        return bundle, IrQweb._get_exported_specs(self.BUNDLE, bundle, params, children)

    def test_the_surface_is_a_strict_subset_of_the_members(self):
        bundle, exported = self._exported()
        members = {a.module_path for a in bundle.native_modules}
        self.assertTrue(exported <= members | {"@odoo/owl"})
        self.assertLess(
            len(exported),
            len(members) // 2,
            "registering most members again means the consumer scan is "
            "reading static imports as loader reads",
        )

    def test_a_source_is_scanned_for_literals_once_per_descriptor(self):
        from types import SimpleNamespace

        from odoo.addons.base.models import ir_qweb_assets_esbuild as esbuild_module

        IrQweb = self.env["ir.qweb"]
        source = SimpleNamespace(
            raw_content='import { a } from "@web/x"; odoo.loader.modules.get("@web/y");'
        )
        descriptor = f"/probe/{self.id()},1.0"
        esbuild_module._SPECIFIER_LITERALS_CACHE.pop(descriptor, None)
        first = IrQweb._get_specifier_literals(descriptor, source)
        self.assertEqual(
            first, frozenset({"@web/y"}), "an import target is not a literal"
        )
        source.raw_content = 'odoo.loader.modules.get("@web/z");'
        self.assertEqual(
            IrQweb._get_specifier_literals(descriptor, source),
            first,
            "the same url and mtime is served from the memo",
        )
        self.assertEqual(
            IrQweb._get_specifier_literals(f"/probe/{self.id()},2.0", source),
            frozenset({"@web/z"}),
            "a new mtime is a new scan",
        )

    def test_what_a_child_imports_and_what_a_literal_names_stay_registered(self):
        bundle, exported = self._exported()
        self.assertIn("@web/core/templates", exported)
        migrations = [
            a.module_path
            for a in bundle.native_modules
            if "/html_migrations/migration-" in (a.url or "")
        ]
        self.assertTrue(migrations, "fixture: html_editor migrations are members")
        self.assertTrue(
            set(migrations) <= exported,
            "html_upgrade_manager reads these from the loader by the name "
            "the migration registry carries",
        )
        IrQweb = self.env["ir.qweb"]
        for child_name in esm_registry().dynamic_children.get(self.BUNDLE, ()):
            if (
                esm_registry().bundle_addon(child_name)
                not in self.env["ir.asset"]._get_addons_installed()
            ):
                continue
            child = IrQweb._get_asset_bundle(
                child_name, css=False, js=True, debug_assets=True
            )
            own = {a.module_path for a in child.native_modules}
            discovered, _ext = child._bridges._discover_bridge_specifiers(
                own, set(external_libs())
            )
            members = {a.module_path for a in bundle.native_modules}
            self.assertFalse(
                (set(discovered) & members) - exported,
                f"{child_name} imports a parent module the parent does not register",
            )

    def test_every_bridge_in_a_page_import_map_has_a_registered_provider(self):
        # a bridge shim reads its provider from the loader; the per-file
        # fallback of a secondary resolves a bare specifier through the page's
        # map, so a bridged member nobody registers is "X is not a constructor"
        # on the first request after the tests bundle changed
        IrQweb = self.env["ir.qweb"]
        params = self.env["ir.asset"]._prepare_assets_params()
        pages = {
            "backend": ("web.assets_web",),
            "frontend": ("web.assets_frontend_minimal", "web.assets_frontend_lazy"),
        }
        for page, names in pages.items():
            with self.subTest(page=page):
                registered: set[str] = set()
                bridged: set[str] = set()
                for name in names:
                    bundle = IrQweb._get_asset_bundle(name, css=False, js=True)
                    children = IrQweb._get_dynamic_child_bundles(
                        name, params, debug_assets=False
                    )
                    registered |= IrQweb._get_exported_specs(
                        name, bundle, params, children
                    )
                    import_map, _dyn, _inc = IrQweb._get_esm_import_map_prod(
                        name, bundle, params, children, with_test_satellites=True
                    )
                    bridged |= {
                        spec
                        for spec, url in import_map.items()
                        if url.startswith("/web/assets/esm/bridges/")
                    }
                self.assertTrue(bridged, "fixture: the page bridges something")
                self.assertFalse(sorted(bridged - registered))

    def test_a_declared_export_is_registered_without_a_source_naming_it(self):
        # test_click_everywhere asks the loader for the clickbot loader by
        # name from Python; no JavaScript source spells that literal, so the
        # scan cannot find it and the manifest declares it.
        _bundle, exported = self._exported()
        self.assertIn("@web/webclient/clickbot/clickbot_loader", esm_registry().exports)
        self.assertIn("@web/webclient/clickbot/clickbot_loader", exported)

    def test_the_compiled_bundle_registers_exactly_the_surface(self):
        bundle, exported = self._exported()
        code = bundle.esbuild_native_bundle(exported_specs=exported).code
        for spec in sorted(exported):
            self.assertIn(f'"{spec}":', code, spec)
        silent = next(
            a.module_path
            for a in bundle.native_modules
            if a.module_path not in exported
        )
        self.assertNotIn(f'"{silent}":', code)


@tagged("-at_install", "post_install", "web_assets")
class TestLogicalParentExportSurface(TransactionCase):
    """`web.assets_frontend` is a logical parent: pages load its members as
    `web.assets_frontend_minimal` plus `web.assets_frontend_lazy`, while
    consumers (survey's secondary bundles, web.assets_tests) are declared under
    the logical name. What a consumer imports from the physical bundle must be
    registered by that physical bundle."""

    PARENT = "web.assets_frontend"
    PHYSICAL = ("web.assets_frontend_minimal", "web.assets_frontend_lazy")

    def test_a_consumer_of_the_logical_parent_is_served_by_its_physical_bundles(self):
        IrQweb = self.env["ir.qweb"]
        params = self.env["ir.asset"]._prepare_assets_params()
        installed = self.env["ir.asset"]._get_addons_installed()
        consumers = [
            name
            for name in esm_registry().secondary_import_map_includes.get(
                self.PARENT, ()
            )
            if name.partition(".")[0] in installed
        ]
        self.assertTrue(consumers, "fixture: web.assets_tests is declared under it")
        for physical in self.PHYSICAL:
            bundle = IrQweb._get_asset_bundle(physical, css=False, js=True)
            members = {a.module_path for a in bundle.native_modules}
            children = IrQweb._get_dynamic_child_bundles(
                physical, params, debug_assets=False
            )
            exported = IrQweb._get_exported_specs(physical, bundle, params, children)
            for name in consumers:
                consumer = IrQweb._get_asset_bundle(
                    name, css=False, js=True, debug_assets=True
                )
                own = {a.module_path for a in consumer.native_modules}
                discovered, _ext = consumer._bridges._discover_bridge_specifiers(
                    own, set(external_libs())
                )
                self.assertFalse(
                    (set(discovered) & members) - exported,
                    f"{name} imports from {physical} a module it does not register",
                )


@tagged("-at_install", "post_install", "web_assets")
class TestRuntimeBundleExportSurface(TransactionCase):
    PAGES = ("web.assets_web", "web.assets_unit_tests_setup")

    def test_a_parentless_runtime_bundle_finds_its_imports_registered(self):
        IrQweb = self.env["ir.qweb"]
        params = self.env["ir.asset"]._prepare_assets_params()
        installed = self.env["ir.asset"]._get_addons_installed()
        registry = esm_registry()
        declared_children = {
            name for children in registry.dynamic_children.values() for name in children
        }
        runtime_bundles = [
            name
            for name in sorted(registry.runtime_bundle_names - declared_children)
            if registry.bundle_addon(name) in installed
        ]
        if not runtime_bundles:
            self.skipTest("no parentless runtime bundle is installed")
        for page in self.PAGES:
            bundle = IrQweb._get_asset_bundle(page, css=False, js=True)
            members = {a.module_path for a in bundle.native_modules}
            children = IrQweb._get_dynamic_child_bundles(
                page, params, debug_assets=False
            )
            exported = IrQweb._get_exported_specs(page, bundle, params, children)
            for name in runtime_bundles:
                consumer = IrQweb._get_asset_bundle(
                    name, css=False, js=True, debug_assets=True
                )
                own = {a.module_path for a in consumer.native_modules}
                discovered, _ext = consumer._bridges._discover_bridge_specifiers(
                    own, set(external_libs())
                )
                self.assertFalse(
                    (set(discovered) & members) - exported,
                    f"{name} imports from {page} a module it does not register",
                )


@tagged("-at_install", "post_install", "web_assets")
class TestLibraryFacades(TransactionCase):
    PAGE_FAMILIES = ("web.assets_web", "web.assets_frontend")

    FACADE_DIRS = ("static/src/core/lib", "static/src/lib")

    def _facade_sources(self):
        for addon in sorted(self.env["ir.asset"]._get_addons_installed()):
            for sub in self.FACADE_DIRS:
                try:
                    directory = Path(file_path(f"{addon}/{sub}"))
                except FileNotFoundError:
                    continue
                for path in sorted(directory.glob("*.js")):
                    yield f"{addon}/{sub}/{path.name}", path.read_text(encoding="utf-8")

    def _facaded_libraries(self):
        from odoo.tools.assets.esm_graph import _TRANSITIVE_IMPORT_RE

        libraries = set(external_libs())
        facaded = {}
        for name, source in self._facade_sources():
            for spec in re.findall(r'import\(\s*["\']([^"\']+)["\']', source):
                if spec in libraries:
                    facaded[spec] = name
            self.assertFalse(
                [
                    m.group("spec")
                    for m in _TRANSITIVE_IMPORT_RE.finditer(source)
                    if m.group("spec") in libraries
                ],
                f"{name} is a facade and must not import its library statically",
            )
        self.assertIn("chart.js", facaded, "fixture: chartjs.js is a facade")
        return facaded

    def test_a_page_family_reaches_a_facaded_library_only_through_its_facade(self):
        facaded = self._facaded_libraries()
        IrQweb = self.env["ir.qweb"]
        offenders = []
        for family in self.PAGE_FAMILIES:
            bundle = IrQweb._get_asset_bundle(
                family, js=True, css=False, debug_assets=True
            )
            for asset in bundle.native_modules:
                if any(f"/{sub}/" in (asset.url or "") for sub in self.FACADE_DIRS):
                    continue
                lexed = lex_module(asset.raw_content)
                imports = (
                    {imp["n"] for imp in lexed["imports"]}
                    if lexed is not None
                    else _get_import_specifiers(asset.raw_content)
                )
                offenders.extend(
                    f"{family}: {asset.url} imports {spec} statically; use {facaded[spec]}"
                    for spec in sorted(imports & set(facaded))
                )
        self.assertFalse(offenders, "\n  ".join(["", *offenders]))


@tagged("web_unit", "web_assets")
class TestServedLibraries(TransactionCase):
    def test_a_closure_follows_relative_imports_inside_static(self):
        files = lib_closure("/web/static/lib/hoot/hoot.js")
        self.assertIn("/web/static/lib/hoot/hoot.js", files)
        self.assertIn("/web/static/lib/hoot/core/runner.js", files)
        self.assertTrue(all(url.startswith("/web/static/") for url in files))
        self.assertEqual(
            lib_closure("/web/static/lib/luxon/luxon.js"),
            {
                "/web/static/lib/luxon/luxon.js": lib_closure(
                    "/web/static/lib/luxon/luxon.js"
                )["/web/static/lib/luxon/luxon.js"]
            },
        )
        self.assertEqual(lib_closure("/web/static/lib/nope/nope.js"), {})

    def test_the_unique_changes_with_any_file_of_the_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp, "a.js")
            b = Path(tmp, "b.js")
            a.write_text("import './b.js';", encoding="utf-8")
            b.write_text("export const x = 1;", encoding="utf-8")
            files = {"/x/static/lib/a.js": a, "/x/static/lib/b.js": b}
            first = lib_unique(files)
            self.assertEqual(first, lib_unique(files))
            b.write_text("export const x = 2;", encoding="utf-8")
            self.assertNotEqual(first, lib_unique(files))

    def test_every_declared_library_is_served_content_addressed(self):
        served = served_external_libs()
        self.assertEqual(set(served), set(external_libs()))
        for spec, url in served.items():
            self.assertRegex(
                url,
                rf"^{LIB_URL_PREFIX}[0-9a-f]{{16}}{re.escape(external_libs()[spec])}$",
                f"{spec} is not content-addressed",
            )
        by_url = served_lib_files()
        for url in served.values():
            self.assertIn(url, by_url)
        declared_files = [declared for _lib, declared in by_url.values()]
        self.assertEqual(len(declared_files), len(set(declared_files)))
        for served_url, (lib, declared) in by_url.items():
            source = lib.files[declared].read_text(encoding="utf-8")
            for spec in _get_import_specifiers(source):
                if not spec.startswith(("./", "../")):
                    continue
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(served_url), spec)
                )
                self.assertIn(target, by_url, f"{declared} imports {spec}")
        prefix = lambda spec: served[spec].split("/web/static/", 1)[0]  # noqa: E731  closes over served for the three assertions below
        self.assertEqual(
            prefix("@odoo/hoot-dom-helpers-dom"),
            prefix("@odoo/hoot-dom-helpers-events"),
        )
        self.assertNotEqual(prefix("@odoo/hoot-dom"), prefix("luxon"))

    def test_a_page_imports_the_served_copy_and_a_debug_page_the_source(self):
        IrQweb = self.env["ir.qweb"]
        for debug, prefix in (("", LIB_URL_PREFIX), ("assets", "/web/static/lib/")):
            nodes = IrQweb._get_asset_nodes(
                "web.assets_web", css=False, js=True, debug=debug
            )
            maps = [
                json.loads(n[1]["text"]) for n in nodes if IrQweb._is_import_map_node(n)
            ]
            self.assertTrue(maps, f"no import map with debug={debug!r}")
            self.assertTrue(
                maps[0]["imports"]["@odoo/owl"].startswith(prefix),
                f"debug={debug!r}: {maps[0]['imports']['@odoo/owl']}",
            )
        rows = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                self.env["ir.attachment"]._get_domain_generated_assets(
                    url_pattern=f"{LIB_URL_PREFIX}%"
                )
            )
        )
        self.assertTrue(set(served_lib_files()) <= set(rows.mapped("url")))
        owl = rows.filtered(lambda r: r.name == "web/static/lib/owl/owl.es.js")
        self.assertEqual(len(owl), 1)
        source = Path(file_path("web/static/lib/owl/owl.es.js")).read_bytes()
        self.assertLess(len(owl.raw), len(source) // 2, "the served copy is minified")
        self.assertIn(b"export", owl.raw)

    def test_a_page_preloads_the_libraries_its_bundle_imports_statically(self):
        IrQweb = self.env["ir.qweb"]
        nodes = IrQweb._get_asset_nodes("web.assets_web", css=False, js=True)
        preloads = {
            attrs["href"]
            for tag, attrs in nodes
            if tag == "link" and attrs.get("rel") == "modulepreload"
        }
        served = served_external_libs()
        self.assertIn(served["@odoo/owl"], preloads)
        self.assertIn(served["luxon"], preloads)
        self.assertNotIn(served["chart.js"], preloads, "reached by import() only")
        self.assertTrue(all(href.startswith(LIB_URL_PREFIX) for href in preloads))
        self.assertEqual(
            IrQweb._get_static_external_imports(
                json.dumps(
                    {
                        "outputs": {
                            "a.js": {
                                "imports": [
                                    {
                                        "path": "luxon",
                                        "kind": "import-statement",
                                        "external": True,
                                    },
                                    {
                                        "path": "chart.js",
                                        "kind": "dynamic-import",
                                        "external": True,
                                    },
                                    {"path": "b.js", "kind": "import-statement"},
                                ]
                            }
                        }
                    }
                )
            ),
            ["luxon"],
        )

    def test_a_superseded_copy_is_collected_and_the_current_one_kept(self):
        IrQweb = self.env["ir.qweb"]
        IrQweb._get_external_libs_served(debug_assets=False)
        Attachment = self.env["ir.attachment"].sudo()
        name = "web/static/lib/luxon/luxon.js"
        current = Attachment.search(
            Attachment._get_domain_generated_assets(url_pattern=f"{LIB_URL_PREFIX}%")
            & Domain("name", "=", name)
        )
        self.assertEqual(len(current), 1)
        stale = Attachment.with_user(SUPERUSER_ID).create(
            {
                "name": name,
                "mimetype": "text/javascript",
                "res_model": "ir.ui.view",
                "res_id": False,
                "type": "binary",
                "public": True,
                "raw": b"export default 1;",
                "url": f"{LIB_URL_PREFIX}0000000000000000/{name}",
            }
        )
        self.env.cr.execute(
            "UPDATE ir_attachment SET write_date = write_date - interval '30 days'"
            " WHERE id = %s",
            [stale.id],
        )
        stale.invalidate_recordset()
        Attachment._gc_esm_assets()
        self.assertFalse(stale.exists())
        self.assertTrue(current.exists())


@tagged("-at_install", "post_install", "web_assets")
class TestServedLibrariesOverHttp(HttpCase):
    def test_the_served_copy_is_immutable_and_a_stale_unique_is_not_found(self):
        self.env["ir.qweb"]._get_external_libs_served(debug_assets=False)
        url = served_external_libs()["@odoo/owl"]
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("immutable", response.headers.get("Cache-Control", ""))
        self.assertIn("javascript", response.headers.get("Content-Type", ""))
        self.assertIn("export", response.text)
        unique = url[len(LIB_URL_PREFIX) :].split("/", 1)[0]
        stale = url.replace(unique, "0" * 16, 1)
        self.assertEqual(self.url_open(stale).status_code, 404)
        self.assertEqual(
            self.url_open(
                f"{LIB_URL_PREFIX}{unique}/web/static/lib/nope.js"
            ).status_code,
            404,
        )


@tagged("-at_install", "post_install", "web_assets")
class TestRuntimeBundlesInTheBrowser(HttpCase):
    PAGE_BUNDLE = "web.assets_web"

    def test_loading_every_lazy_child_rebinds_nothing(self):
        IrQweb = self.env["ir.qweb"]
        installed = self.env["ir.asset"]._get_addons_installed()
        children = [
            name
            for name in sorted(
                esm_registry().dynamic_children.get(self.PAGE_BUNDLE, ())
            )
            if name.partition(".")[0] in installed
            and IrQweb._is_runtime_child_compiled(name)
            and IrQweb._get_asset_bundle(
                name, js=True, css=False, debug_assets=True
            ).native_modules
        ]
        self.assertTrue(children, "no compiled lazy child of the web client here")
        self.browser_js(
            "/odoo",
            """
            (async () => {
                const rebinds = [];
                odoo.loader.bus.addEventListener("rebind", (ev) =>
                    rebinds.push(...ev.detail.specifiers)
                );
                const { loadBundle } = odoo.loader.modules.get("@web/core/assets");
                const before = odoo.loader.modules.size;
                for (const name of %s) {
                    try {
                        await loadBundle(name);
                    } catch (error) {
                        console.error(
                            `loading ${name} failed: ${error} ${error?.cause || ""} ${error?.stack || ""}`
                        );
                        return;
                    }
                }
                if (rebinds.length) {
                    console.error("singleton split: " + rebinds.join(", "));
                } else if (odoo.loader.modules.size === before) {
                    console.error("no lazy child registered a module");
                } else {
                    console.log("test successful");
                }
            })();
            """
            % json.dumps(children),
            "odoo.isReady === true",
            login="admin",
        )


@tagged("web_unit", "web_assets")
class TestImportDiscovery(TransactionCase):
    def test_bridge_discovers_side_effect_imports(self):
        m = _IMPORT_ANY_RE.search('import "@mail/chatter/web/chatter_patch";')
        self.assertIsNotNone(m, "side-effect import must be discovered")
        self.assertEqual(m.group("side"), "@mail/chatter/web/chatter_patch")
        self.assertIsNone(m.group("spec"), "side-effect import has no binding spec")
        for binding in (
            'import { _t } from "@web/core/translation";',
            'import * as ns from "@web/core/utils";',
            'import def from "@web/core/registry";',
        ):
            m = _IMPORT_ANY_RE.search(binding)
            self.assertIsNotNone(m, f"binding import must match: {binding}")
            self.assertIsNone(m.group("side"), binding)
            self.assertTrue(m.group("spec"), binding)
