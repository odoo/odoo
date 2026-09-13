import base64
import io
import logging
import socket
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pymupdf
import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from weasyprint.urls import URLFetcher

from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.libs.json import loads as json_loads
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tests.transaction_case import _super_send
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

from odoo.addons.base.models.ir_actions_report import (
    PDF_OPTIONS_DATA_KEY,
    OdooURLFetcher,
    _weasy_state,
)

_weasy_logger = logging.getLogger("weasyprint")


@tagged("post_install", "-at_install")
class TestReportUrlFetcher(TransactionCase):
    def setUp(self):
        super().setUp()
        self.report = self.env["ir.actions.report"]
        self.fetcher = self.report._prepare_url_fetcher()
        self.addCleanup(self.fetcher.cleanup)

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_static_file_rejects_path_traversal(self):
        url = "http://localhost/base/static/../../../../../../etc/passwd"
        path = "/base/static/../../../../../../etc/passwd"
        self.assertIsNone(self.fetcher._resolve_static_file(url, path))

    def test_static_file_ignores_non_static_path(self):
        self.assertIsNone(
            self.fetcher._resolve_static_file(
                "http://localhost/base/models/foo.py", "/base/models/foo.py"
            )
        )
        self.assertIsNone(
            self.fetcher._resolve_static_file("http://localhost/base", "/base")
        )

    def test_parse_image_url_variants(self):
        cases = [
            (
                "/web/image/res.partner/42/image_1920",
                "",
                ("res.partner", 42, "image_1920", 0, 0),
            ),
            (
                "/web/image/res.partner/42/image_128/64x96",
                "",
                ("res.partner", 42, "image_128", 64, 96),
            ),
            (
                "/web/image/7",
                "",
                ("ir.attachment", 7, "raw", 0, 0),
            ),
            (
                "/web/image/7-deadbeef/20x30",
                "",
                ("ir.attachment", 7, "raw", 20, 30),
            ),
            (
                "/web/image",
                "model=res.users&id=3&field=avatar_128&width=10&height=15",
                ("res.users", 3, "avatar_128", 10, 15),
            ),
            (
                "/web/image",
                "id=9",
                ("ir.attachment", 9, "raw", 0, 0),
            ),
        ]
        for path, query, expected in cases:
            with self.subTest(path=path, query=query):
                self.assertEqual(self.fetcher._parse_image_url(path, query), expected)

    def test_parse_image_url_missing_id_raises(self):
        with self.assertRaises(ValueError):
            self.fetcher._parse_image_url("/web/image", "model=res.partner")

    def _resolving(self, *addresses, error=None):
        def getaddrinfo(host, port, *args, **kwargs):
            if error:
                raise error
            return [
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
                for a in addresses
            ]

        return patch("socket.getaddrinfo", side_effect=getaddrinfo)

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_fetch_refuses_every_non_public_literal(self):
        for host in (
            "169.254.169.254",
            "127.0.0.2",
            "10.1.2.3",
            "192.168.0.5",
            "172.16.9.9",
            "100.64.0.1",
            "100.127.255.254",
            "[::1]",
            "[fe80::1]",
            "[64:ff9b::7f00:1]",
        ):
            with self.subTest(host=host), self.assertRaises(ValueError):
                self.fetcher.fetch(f"http://{host}/font.woff")

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_fetch_refuses_loopback_names_whatever_they_resolve_to(self):
        for host in ("localhost", "LOCALHOST", "db.localhost", "db.localhost."):
            with (
                self.subTest(host=host),
                self._resolving("93.184.216.34"),
                self.assertRaises(ValueError),
            ):
                self.fetcher.fetch(f"http://{host}:1/font.woff")

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_fetch_refuses_a_name_resolving_to_a_private_address(self):
        with self._resolving("127.0.0.1"), self.assertRaises(ValueError):
            self.fetcher.fetch("http://localtest.me/font.woff")

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_fetch_refuses_a_name_that_does_not_resolve(self):
        error = socket.gaierror(socket.EAI_NONAME, "no such host")
        with self._resolving(error=error), self.assertRaises(ValueError):
            self.fetcher.fetch("http://internal.corp.example.com/font.woff")

    def test_fetch_connects_to_the_checked_address_under_the_hostname(self):
        sent = []

        def send(adapter, request, **kwargs):
            sent.append((request.netguard_address, request.headers.get("Host")))
            response = requests.Response()
            response.status_code = 200
            response.request = request
            response.url = request.url
            response.headers["Content-Type"] = "text/css"
            response.headers["Content-Encoding"] = "gzip"
            response._content = b"body{}"
            return response

        with (
            self._resolving("93.184.216.34"),
            patch.object(requests.Session, "send", _super_send),
            patch.object(HTTPAdapter, "send", autospec=True, side_effect=send),
        ):
            resource = self.fetcher.fetch("https://cdn.example.com/site.css")
        self.assertEqual(sent, [("93.184.216.34", "cdn.example.com")])
        self.assertEqual(resource.read(), b"body{}")
        self.assertEqual(resource.headers["Content-Type"], "text/css")
        self.assertNotIn("Content-Encoding", resource.headers)

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_fetch_refuses_private_ip(self):
        with self.assertRaises(ValueError):
            self.fetcher.fetch("http://169.254.169.254/latest/meta-data/")

    def test_fetch_rejects_file_scheme(self):
        with self.assertRaises(ValueError):
            self.fetcher.fetch("file:///etc/passwd")


@tagged("post_install", "-at_install")
class TestReportAuditFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reports = cls.env["ir.actions.report"].create(
            [
                {
                    "name": "Audit Report 1",
                    "model": "res.partner",
                    "report_name": "base.audit_report_1",
                },
                {
                    "name": "Audit Report 2",
                    "model": "res.partner",
                    "report_name": "base.audit_report_2",
                },
                {
                    "name": "Audit Report 3",
                    "model": "res.users",
                    "report_name": "base.audit_report_3",
                },
            ]
        )

    def test_create_action_binds_per_model(self):
        self.reports.create_action()
        partner_model = self.env["ir.model"]._get("res.partner")
        users_model = self.env["ir.model"]._get("res.users")
        self.assertEqual(self.reports[0].binding_model_id, partner_model)
        self.assertEqual(self.reports[1].binding_model_id, partner_model)
        self.assertEqual(self.reports[2].binding_model_id, users_model)
        self.assertEqual(set(self.reports.mapped("binding_type")), {"report"})

    def test_create_action_checks_write_access(self):
        user = self.env["res.users"].create(
            {
                "name": "Report Audit User",
                "login": "report_audit_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.reports.with_user(user).create_action()

    def test_search_model_id_unhandled_combo_returns_notimplemented(self):
        Report = self.env["ir.actions.report"]
        self.assertIs(Report._search_model_id("=", None), NotImplemented)
        partner_model = self.env["ir.model"]._get("res.partner")
        found = Report.search([("model_id", "=", partner_model.id)])
        self.assertIn(self.reports[0], found)

    def test_render_unknown_report_type_raises(self):
        report = self.reports[0]
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_act_report_xml SET report_type = %s WHERE id = %s",
            ["qweb-bogus", report.id],
        )
        report.invalidate_recordset(["report_type"])
        with self.assertRaises(UserError) as capture:
            self.env["ir.actions.report"]._render(report, [])
        self.assertIn("qweb-bogus", str(capture.exception))

    def test_render_resolves_string_reference_once(self):
        self.env["ir.actions.report"].create(
            {
                "name": "Audit Render Report",
                "model": "res.partner",
                "report_type": "qweb-html",
                "report_name": "base.audit_report_render",
            }
        )
        self.env["ir.ui.view"].create(
            {
                "type": "qweb",
                "name": "base.audit_report_render",
                "key": "base.audit_report_render",
                "arch": '<main><div class="article"><span>audit</span></div></main>',
            }
        )
        Report = self.env["ir.actions.report"]
        report_cls = type(Report)
        original_get_report = report_cls._get_report
        seen_refs = []

        def _tracking_get_report(model_self, report_ref):
            seen_refs.append(report_ref)
            return original_get_report(model_self, report_ref)

        self.patch(report_cls, "_get_report", _tracking_get_report)
        content, report_type = Report._render(
            "base.audit_report_render", [self.env.user.partner_id.id]
        )
        self.assertEqual(report_type, "html")
        self.assertIn(b"audit", content)
        string_refs = [ref for ref in seen_refs if isinstance(ref, str)]
        self.assertEqual(
            len(string_refs),
            1,
            "the string report reference must be resolved exactly once per render",
        )

    def test_barcode_fallback_to_code128_logs_warning(self):
        with self.assertLogs(
            "odoo.addons.base.models.ir_actions_report", level="WARNING"
        ) as capture:
            png = self.env["ir.actions.report"].prepare_barcode("I2of5", "not-numeric")
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertTrue(
            any("falling back to Code128" in line for line in capture.output)
        )

    def test_report_name_is_indexed(self):
        self.assertTrue(self.env["ir.actions.report"]._fields["report_name"].index)


@tagged("post_install", "-at_install")
class TestReportAttachmentNameCache(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Audit Attach"})
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "audit attach report",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "base.audit_attach_report_dummy",
                "attachment": "'fallback-%s.pdf' % object.id",
            }
        )

    def _stream_entry(self, **extra):
        return {"stream": io.BytesIO(b"%PDF-audit"), "attachment": None, **extra}

    def test_cached_attachment_name_skips_safe_eval(self):
        self.report.attachment = "1/0"
        streams = {self.partner.id: self._stream_entry(attachment_name="cached.pdf")}
        vals_list = self.env[
            "ir.actions.report"
        ]._prepare_pdf_report_attachment_vals_list(self.report, streams)
        self.assertEqual(len(vals_list), 1)
        self.assertEqual(vals_list[0]["name"], "cached.pdf")
        self.assertEqual(vals_list[0]["res_id"], self.partner.id)

    def test_evaluated_empty_cache_skips_attachment(self):
        self.report.attachment = "1/0"
        streams = {self.partner.id: self._stream_entry(attachment_name="")}
        vals_list = self.env[
            "ir.actions.report"
        ]._prepare_pdf_report_attachment_vals_list(self.report, streams)
        self.assertEqual(vals_list, [])

    def test_entry_without_a_name_is_skipped(self):
        for entry in (self._stream_entry(), self._stream_entry(attachment_name=None)):
            with self.subTest(entry=entry):
                vals_list = self.env[
                    "ir.actions.report"
                ]._prepare_pdf_report_attachment_vals_list(
                    self.report, {self.partner.id: entry}
                )
                self.assertEqual(vals_list, [])


@tagged("post_install", "-at_install")
class TestPdfOptionsChannel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Audit PdfOpts"})
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "audit pdfopts report",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "base.audit_pdfopts_report_dummy",
            }
        )

    def _prepare_streams(self, data):
        captured = {}
        registry_cls = type(self.env["ir.actions.report"])
        partner_id = self.partner.id

        def fake_render_qweb_html(model, report_ref, docids, data=None):
            captured["qweb_data"] = data
            return (b"<html/>", "html")

        def fake_prepare_weasyprint_html(model, html, report_model=False):
            return (["<html/>"], [partner_id], {})

        def fake_render_html_to_pdf(
            model,
            bodies,
            report_ref=False,
            landscape=False,
            specific_paperformat_args=None,
            _split=False,
            **kwargs,
        ):
            captured["pdf_kwargs"] = kwargs
            return [b"%PDF-audit"] * len(bodies) if _split else b"%PDF-audit"

        with (
            patch.object(registry_cls, "_render_qweb_html", fake_render_qweb_html),
            patch.object(
                registry_cls,
                "_prepare_weasyprint_html",
                fake_prepare_weasyprint_html,
            ),
            patch.object(registry_cls, "_render_html_to_pdf", fake_render_html_to_pdf),
        ):
            self.env["ir.actions.report"]._render_qweb_pdf_prepare_streams(
                self.report, data, res_ids=[self.partner.id]
            )
        return captured

    def test_namespaced_key_feeds_options_and_is_popped(self):
        captured = self._prepare_streams(
            {PDF_OPTIONS_DATA_KEY: {"pdf_variant": "pdf/a-3b"}}
        )
        self.assertEqual(captured["pdf_kwargs"], {"pdf_variant": "pdf/a-3b"})
        self.assertNotIn(
            PDF_OPTIONS_DATA_KEY,
            captured["qweb_data"],
            "the reserved key must never reach the QWeb rendering context",
        )

    def test_top_level_keys_are_not_options(self):
        captured = self._prepare_streams({"pdf_variant": "pdf/a-3b"})
        self.assertEqual(
            captured["pdf_kwargs"],
            {},
            "legacy top-level data keys must not be interpreted as PDF options",
        )


@tagged("post_install", "-at_install")
class TestReportRenderEntryPoints(TransactionCase):
    def test_render_qweb_html_accepts_int_docids(self):
        module = self.env["ir.module.module"].search([("name", "=", "base")])
        content, report_type = self.env["ir.actions.report"]._render_qweb_html(
            "base.report_irmodulereference", module.id
        )
        self.assertEqual(report_type, "html")
        self.assertTrue(content)

    def test_render_qweb_html_does_not_mutate_caller_data(self):
        module = self.env["ir.module.module"].search([("name", "=", "base")])
        data = {}
        self.env["ir.actions.report"]._render_qweb_html(
            "base.report_irmodulereference", [module.id], data=data
        )
        self.assertEqual(data, {}, "the caller's data dict must not be mutated")

    def test_report_action_accepts_any_id_iterable(self):
        report = self.env.ref("base.ir_module_reference_print")
        action = report.report_action((7, 9), config=False)
        self.assertEqual(action["context"]["active_ids"], [7, 9])

    def test_report_action_rejects_non_iterable_docids(self):
        report = self.env.ref("base.ir_module_reference_print")
        with self.assertRaises(TypeError):
            report.report_action(3.5, config=False)


@tagged("post_install", "-at_install")
class TestValidActionReportsDomainGuard(TransactionCase):
    def test_malformed_domain_is_logged_and_treated_valid(self):
        Report = self.env["ir.actions.report"]
        common = {
            "model": "res.partner",
            "report_type": "qweb-pdf",
        }
        good = Report.create(
            {
                "name": "audit good domain",
                "report_name": "base.audit_good_domain_dummy",
                "domain": "[('name', '=', 'Audit Domain Guard')]",
                **common,
            }
        )
        bad = Report.create(
            {
                "name": "audit bad domain",
                "report_name": "base.audit_bad_domain_dummy",
                "domain": "[('name' =",
                **common,
            }
        )
        partner = self.env["res.partner"].create({"name": "Audit Domain Guard"})
        with self.assertLogs(
            "odoo.addons.base.models.ir_actions_report", level="WARNING"
        ) as capture:
            valid_ids = (good + bad).get_valid_action_reports(
                "res.partner", [partner.id]
            )
        self.assertIn(good.id, valid_ids)
        self.assertIn(bad.id, valid_ids, "a malformed domain degrades to always-valid")
        self.assertTrue(any("malformed domain" in line for line in capture.output))


@tagged("post_install", "-at_install")
class TestWeasyPrintFailureObservability(TransactionCase):
    def test_layout_failure_logs_traceback(self):
        engine = self.env["ir.actions.report"]._prepare_weasyprint_engine()
        with (
            patch(
                "odoo.addons.base.models.ir_actions_report.weasyprint.HTML",
                side_effect=ValueError("audit-layout-boom"),
            ),
            self.assertLogs(
                "odoo.addons.base.models.ir_actions_report", level="ERROR"
            ) as capture,
            self.assertRaises(UserError),
        ):
            engine._render_body_document("<html/>", fetcher=None, body_css=[])
        self.assertTrue(
            any(record.exc_info for record in capture.records),
            "the log record must carry the traceback (exc_info=True)",
        )


@tagged("post_install", "-at_install")
class TestHtmlToImageTestMode(TransactionCase):
    def test_short_circuits_in_test_mode(self):
        registry_cls = type(self.env["ir.actions.report"])
        with patch.object(
            registry_cls,
            "_prepare_url_fetcher",
            side_effect=AssertionError("must not render in test mode"),
        ) as fetcher_mock:
            result = self.env["ir.actions.report"]._render_html_to_image(
                ["<div>audit</div>"], 10, 10
            )
        self.assertEqual(result, [None])
        self.assertFalse(fetcher_mock.called)

    def test_force_report_rendering_bypasses_short_circuit(self):
        registry_cls = type(self.env["ir.actions.report"])
        fetcher_cm = MagicMock()
        fetcher_cm.__enter__ = MagicMock(return_value=MagicMock())
        fetcher_cm.__exit__ = MagicMock(return_value=False)
        with (
            patch.object(
                registry_cls, "_prepare_url_fetcher", return_value=fetcher_cm
            ) as fetcher_mock,
            patch(
                "odoo.addons.base.models.ir_actions_report.weasyprint.HTML",
                side_effect=ValueError("audit-image-boom"),
            ),
            self.assertLogs(
                "odoo.addons.base.models.ir_actions_report", level="WARNING"
            ),
        ):
            result = (
                self.env["ir.actions.report"]
                .with_context(force_report_rendering=True)
                ._render_html_to_image(["<div>audit</div>"], 10, 10)
            )
        self.assertEqual(result, [None])
        self.assertTrue(fetcher_mock.called)


@tagged("post_install", "-at_install")
class TestAssociatedViewMissingActionRef(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Audit Associated View Report",
                "model": "res.partner",
                "report_name": "base.audit_associated_view_dummy",
            }
        )

    def test_returns_action_data_when_action_ref_exists(self) -> None:
        data = self.report.action_view_qweb_views()
        self.assertIsInstance(data, dict)
        matching_view, other_view = self.env["ir.ui.view"].create(
            [
                {"name": "audit_associated_view_dummy", "type": "qweb", "arch": "<t/>"},
                {"name": "audit_unrelated_view", "type": "qweb", "arch": "<t/>"},
            ]
        )
        found = self.env["ir.ui.view"].search(data["domain"])
        self.assertIn(matching_view, found)
        self.assertNotIn(other_view, found)

    def test_returns_false_when_action_ref_missing(self) -> None:
        imd = self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "action_ui_view")]
        )
        imd.unlink()
        self.assertFalse(self.report.action_view_qweb_views())

    def test_returns_false_when_report_name_has_no_module_part(self) -> None:
        self.report.report_name = "audit_no_module_part"
        self.assertFalse(self.report.action_view_qweb_views())


@tagged("post_install", "-at_install")
class TestXmlidLookupCacheOrderingAfterWrite(TransactionCase):
    def test_db_row_reflects_write_before_cache_clear(self) -> None:
        group_a = self.env["res.groups"].create({"name": "Audit Group A"})
        group_b = self.env["res.groups"].create({"name": "Audit Group B"})
        imd = self.env["ir.model.data"].create(
            {
                "module": "__test_imd_audit",
                "name": "test_group_order",
                "model": "res.groups",
                "res_id": group_a.id,
            }
        )
        self.env.flush_all()

        observed_res_id = []

        def _probe_db_on_clear_cache(*args: object, **kwargs: object) -> None:
            self.env.cr.execute(
                "SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s",
                ["__test_imd_audit", "test_group_order"],
            )
            observed_res_id.append(self.env.cr.fetchone()[0])

        self.patch(self.env.registry, "clear_cache", _probe_db_on_clear_cache)
        imd.write({"res_id": group_b.id})

        self.assertTrue(observed_res_id)
        self.assertEqual(
            observed_res_id,
            [group_b.id] * len(observed_res_id),
            "the DB row must already reflect the write by the time "
            "clear_cache() runs, else a concurrent raw-SQL lookup could "
            "re-cache the pre-write row",
        )


@tagged("post_install", "-at_install")
class TestFetcherHttpFallback(TransactionCase):
    def setUp(self):
        super().setUp()
        self.fetcher = self.env["ir.actions.report"]._prepare_url_fetcher()
        self.addCleanup(self.fetcher.cleanup)

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_http_fallback_retries_with_full_url(self):
        seen = {}

        def failing_get(url, cookies):
            raise requests.exceptions.ConnectionError("audit: primary down")

        def fake_super_fetch(fetcher_self, url, headers=None):
            seen["url"] = url
            raise ValueError("audit: stop here")

        with (
            patch.object(
                OdooURLFetcher, "_get_http_response", staticmethod(failing_get)
            ),
            patch.object(URLFetcher, "fetch", fake_super_fetch),
            self.assertRaises(ValueError),
        ):
            self.fetcher._get_via_http("/web/image/1", "/web/image/1")
        parsed = urlparse(seen["url"])
        self.assertTrue(
            parsed.scheme and parsed.netloc,
            f"fallback must receive an absolute URL, got {seen['url']!r}",
        )
        self.assertTrue(seen["url"].endswith("/web/image/1"))

    def test_resolve_barcode_forwards_barborder(self):
        captured = {}
        registry_cls = type(self.env["ir.actions.report"])

        def fake_barcode(model, barcode_type, value, **kwargs):
            captured["type"] = barcode_type
            captured.update(kwargs)
            return b"\x89PNG-audit"

        with patch.object(registry_cls, "prepare_barcode", fake_barcode):
            response = self.fetcher._resolve_barcode(
                "/report/barcode/QR/audit?barBorder=0",
                "/report/barcode/QR/audit",
                "barBorder=0&quiet=1",
            )
        self.assertIsNotNone(response)
        self.assertEqual(captured["type"], "QR")
        self.assertEqual(captured.get("barBorder"), "0")
        self.assertEqual(captured.get("quiet"), "1")


@tagged("post_install", "-at_install")
class TestReportFetcherOrigin(TransactionCase):
    def _fetcher(self, base_url):
        fetcher = OdooURLFetcher(self.env, base_url=base_url)
        fetcher._session_cookie = "SESSIONSECRET"
        return fetcher

    def _route(self, fetcher, url):
        seen = {}

        def fake_http_response(target, cookies, verify=True):
            seen["local"] = verify
            response = MagicMock()
            response.headers = {"Content-Type": "image/png"}
            response.content = b"x"
            return response

        fetcher._get_http_response = fake_http_response
        with patch.object(
            OdooURLFetcher,
            "_fetch_external",
            lambda self, u, hostname, headers=None: MagicMock(),
        ):
            fetcher.fetch(url)
        return ("local", seen["local"]) if "local" in seen else ("external", None)

    def test_cookie_only_reaches_the_exact_origin(self):
        fetcher = self._fetcher("https://erp.example.com")
        self.assertEqual(self._route(fetcher, "/web/content/1"), ("local", True))
        self.assertEqual(
            self._route(fetcher, "https://erp.example.com/web/content/1"),
            ("local", True),
        )
        for foreign in (
            "https://erp.example.com:9999/web/content/1",
            "http://erp.example.com/web/content/1",
            "https://evil.example.net/pixel.png",
        ):
            self.assertEqual(
                self._route(fetcher, foreign),
                ("external", None),
                f"{foreign} was treated as this database's own origin",
            )
        fetcher.cleanup()

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_loopback_name_is_refused_from_a_public_origin(self):
        fetcher = self._fetcher("https://erp.example.com")
        for target in (
            "http://localhost:8069/web/content/1",
            "http://ip6-localhost:8069/web/content/1",
            "http://db.localhost/web/content/1",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                fetcher.fetch(target)
        fetcher.cleanup()

    def test_tls_verification_is_waived_only_for_loopback(self):
        loopback = self._fetcher("http://localhost:8069")
        self.assertEqual(
            self._route(loopback, "http://localhost:8069/web/content/1"),
            ("local", False),
        )
        loopback.cleanup()

    def test_private_address_literals_stay_refused(self):
        fetcher = self._fetcher("https://erp.example.com")
        with (
            self.assertRaises(ValueError),
            mute_logger("odoo.addons.base.models.ir_actions_report"),
        ):
            fetcher.fetch("http://169.254.169.254/latest/meta-data/")
        fetcher.cleanup()


@tagged("post_install", "-at_install")
class TestMergePdfsErrorPolicy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.report = self.env["ir.actions.report"]
        self.valid = self.report._render_html_to_pdf(
            ["<html><body><p>valid</p></body></html>"]
        )

    def test_default_policy_aborts_and_names_the_corrupt_stream_as_cause(self):
        with self.assertRaises(UserError) as caught:
            self.report._merge_pdfs([io.BytesIO(self.valid), io.BytesIO(b"not a pdf")])
        self.assertIsNotNone(
            caught.exception.__cause__,
            "the reader failure is the cause of the UserError and must be chained; "
            "raising inside a helper left it as an implicit __context__ instead",
        )

    def test_a_policy_that_returns_none_carries_on(self):
        collected = []

        def collect(error, error_stream):
            collected.append(error_stream)

        merged = self.report._merge_pdfs(
            [io.BytesIO(self.valid), io.BytesIO(b"not a pdf")], collect
        )
        self.assertEqual(len(collected), 1, "the corrupt stream must reach the policy")
        self.assertTrue(
            merged.getvalue().startswith(b"%PDF"),
            "a policy that declines to abort must still get the surviving pages",
        )

    def test_the_builder_returns_the_error_rather_than_raising_it(self):
        error = self.report._prepare_merge_pdfs_error()
        self.assertIsInstance(
            error,
            UserError,
            "_prepare_*_error builds the exception; the caller writes the raise",
        )


@tagged("post_install", "-at_install")
class TestLayoutConfiguratorAction(TransactionCase):
    def setUp(self):
        super().setUp()
        self.report = self.env["ir.actions.report"].search([], limit=1)
        self.env.company.external_report_layout_id = False

    def test_a_company_without_a_layout_gets_the_configurator_first(self):
        action = self.report.report_action([])
        self.assertEqual(action["type"], "ir.actions.act_window")
        context = action.get("context")
        if isinstance(context, str):
            context = json_loads(context)
        inner = context.get("report_action")
        self.assertIsNotNone(
            inner,
            "the configurator carries the report action under the literal key "
            "'report_action', which web/models/base_document_layout.py reads back",
        )
        self.assertEqual(inner["type"], "ir.actions.report")
        self.assertTrue(inner["close_on_report_download"])

    def test_discard_logo_check_returns_the_report_action_itself(self):
        action = self.report.with_context(discard_logo_check=True).report_action([])
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], self.report.report_name)


BROKEN_IMAGE = "data:image/png;base64,QUFBQUFB"


def _png_data_uri(color):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _first_pixel(pdf):
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        for xref, *_rest in document.get_page_images(0):
            raw = document.extract_image(xref)["image"]
            with Image.open(io.BytesIO(raw)) as image:
                return image.convert("RGB").getpixel((4, 4))
    return None


@tagged("post_install", "-at_install")
class TestImageCacheLifetime(TransactionCase):
    def _render(self, *sources):
        body = (
            "<html><head></head><body><main>"
            + "".join(f'<img src="{src}">' for src in sources)
            + "</main></body></html>"
        )
        return (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_html_to_pdf([body])
        )

    def test_a_url_is_not_reused_across_renders(self):
        red, green = _png_data_uri((255, 0, 0)), _png_data_uri((0, 255, 0))
        self.assertNotEqual(
            _first_pixel(self._render(red)),
            _first_pixel(self._render(green)),
            "a process-wide cache keyed on the URL alone served one render's "
            "image to the next, across users and databases",
        )

    @mute_logger("weasyprint")
    def test_an_unloadable_image_does_not_poison_later_renders(self):
        sources = [_png_data_uri((i, 40, 80)) for i in range(60)]
        self._render(BROKEN_IMAGE, *sources)
        for source in sources[:4]:
            with self.subTest(source=source[:40]):
                self.assertTrue(
                    self._render(source).startswith(b"%PDF"),
                    "an image that failed to load inserts one unpaired cache "
                    "entry; evicting across that boundary used to orphan a "
                    "payload and fail every later render of the survivor",
                )

    def test_database_state_is_scoped_and_evicted_as_one_unit(self):
        self.addCleanup(_weasy_state.clear_for_tests)
        _weasy_state.setup_process()
        first = _weasy_state.for_database("audit_db_a")
        second = _weasy_state.for_database("audit_db_b")
        self.assertIsNot(first, second)
        self.assertIsNot(first.font_config, second.font_config)
        self.assertIs(first, _weasy_state.for_database("audit_db_a"))

        first.css_cache[("/a.css", "sum")] = object()
        for index in range(16):
            _weasy_state.for_database(f"audit_db_filler_{index}")
        revived = _weasy_state.for_database("audit_db_a")
        self.assertNotIn(
            ("/a.css", "sum"),
            revived.css_cache,
            "a stylesheet outliving the font configuration it was parsed "
            "against would render with its @font-face rules missing",
        )


@tagged("post_install", "-at_install")
class TestArticleHeaderFooterPairing(TransactionCase):
    ARCH = """<t t-name="base.audit_pairing"><html><head></head><body><main>
        <div class="header">ALPHA</div>
        <div class="article" data-oe-model="res.partner" data-oe-id="1">
            <div class="header">STRAY</div><span>ONE</span>
        </div>
        <div class="header">BETA</div>
        <div class="article" data-oe-model="res.partner" data-oe-id="2">
            <span>TWO</span>
        </div>
        <div class="footer">OMEGA</div>
    </main></body></html></t>"""

    def _bodies(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "audit pairing",
                "type": "qweb",
                "key": "base.audit_pairing",
                "arch_db": self.ARCH,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "audit_pairing",
                "model": "ir.ui.view",
                "res_id": view.id,
            }
        )
        report = self.env["ir.actions.report"].create(
            {
                "name": "Audit pairing",
                "model": "res.partner",
                "report_name": "base.audit_pairing",
                "report_type": "qweb-pdf",
            }
        )
        self.env.flush_all()
        html = self.env["ir.actions.report"]._render_qweb_html(report, [1, 2])[0]
        bodies, res_ids, _args = report._prepare_weasyprint_html(
            html, report_model="res.partner"
        )
        return [str(body) for body in bodies], res_ids

    def test_a_header_inside_an_article_does_not_shift_the_next_record(self):
        bodies, res_ids = self._bodies()
        self.assertEqual(res_ids, [1, 2])
        self.assertIn("ALPHA", bodies[0])
        self.assertIn(
            "BETA",
            bodies[1],
            "pairing headers to articles by document-order index let a header "
            "nested inside one record's content consume the next record's",
        )
        self.assertNotIn(
            "STRAY",
            bodies[1],
            "one record's content must never reach another record's page",
        )
        self.assertIn("OMEGA", bodies[1])
        self.assertNotIn("OMEGA", bodies[0])


@tagged("post_install", "-at_install")
class TestAttachmentNamesEvaluatedOnce(TransactionCase):
    def test_precomputed_names_are_not_recomputed(self):
        report = self.env["ir.actions.report"].create(
            {
                "name": "Audit attachment",
                "model": "res.partner",
                "report_name": "base.audit_attachment",
                "report_type": "qweb-pdf",
                "attachment": "'audit-%s.pdf' % object.id",
            }
        )
        records = self.env["res.partner"].search([], limit=3)
        module = "odoo.addons.base.models.ir_actions_report"
        with patch(f"{module}.safe_eval", wraps=safe_eval) as evaluated:
            filenames = report._get_attachment_filenames(records)
            baseline = evaluated.call_count
            report._get_attachments(records, filenames)
            self.assertEqual(
                evaluated.call_count,
                baseline,
                "_get_attachments recomputed the names its caller had just "
                "evaluated, doubling safe_eval over the whole batch",
            )
        self.assertEqual(len(filenames), len(records))


@tagged("post_install", "-at_install")
class TestMergeErrorRecordIds(TransactionCase):
    def setUp(self):
        super().setUp()
        self.report = self.env["ir.actions.report"].create(
            {
                "name": "Audit merge",
                "model": "res.partner",
                "report_name": "base.audit_merge",
                "report_type": "qweb-pdf",
            }
        )
        self.valid_pdf = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_html_to_pdf(["<html><body><main><p>ok</p></main></body></html>"])
        )

    def _render_with_streams(self, streams):
        with (
            patch.object(
                type(self.env["ir.actions.report"]),
                "_render_qweb_pdf_prepare_streams",
                return_value=streams,
            ),
            mute_logger("odoo.addons.base.models.ir_actions_report"),
        ):
            return (
                self.env["ir.actions.report"]
                .with_context(force_report_rendering=True)
                ._render_qweb_pdf(self.report, [1])
            )

    def test_only_the_sentinel_corrupt_raises_the_plain_error(self):
        streams = {
            False: {"stream": io.BytesIO(b"not a pdf"), "attachment": None},
            1: {"stream": io.BytesIO(self.valid_pdf), "attachment": None},
        }
        with self.assertRaises(UserError) as caught:
            self._render_with_streams(streams)
        self.assertNotIsInstance(
            caught.exception,
            RedirectWarning,
            "the merged-body sentinel is not a record, so there is nothing for "
            "the user to open",
        )

    def test_the_sentinel_is_not_counted_among_problematic_records(self):
        streams = {
            False: {"stream": io.BytesIO(b"not a pdf"), "attachment": None},
            1: {"stream": io.BytesIO(b"also not a pdf"), "attachment": None},
        }
        with self.assertRaises(RedirectWarning) as caught:
            self._render_with_streams(streams)
        action = caught.exception.args[1]
        self.assertEqual(action["res_id"], 1)
        self.assertNotIn(
            "2",
            caught.exception.args[0],
            "False reached the count and the domain, so the message named one "
            "more corrupt file than the action could show",
        )


@tagged("post_install", "-at_install")
class TestHtmlToImageDiagnostics(TransactionCase):
    def test_a_failed_render_reports_what_the_renderer_said(self):
        def fail_after_complaining(**kwargs):
            _weasy_logger.error("Failed to load image at 'audit-probe.png'")
            raise ValueError("audit-image-boom")

        module = "odoo.addons.base.models.ir_actions_report"
        with (
            patch(f"{module}.weasyprint.HTML", side_effect=fail_after_complaining),
            self.assertLogs(module, level="WARNING") as captured,
        ):
            result = (
                self.env["ir.actions.report"]
                .with_context(force_report_rendering=True)
                ._render_html_to_image(["<div>audit</div>"], 10, 10)
            )
        self.assertEqual(result, [None])
        self.assertIn(
            "audit-probe.png",
            captured.output[0],
            "the renderer's own diagnosis is the useful half, and routing "
            "weasyprint's records to a per-render sink had swallowed it",
        )


@tagged("post_install", "-at_install")
class TestReportPaperformatFallback(TransactionCase):
    def test_a_report_with_no_paperformat_falls_back_to_a_real_one(self):
        report = self.env["ir.actions.report"].create(
            {
                "name": "No Paperformat Report",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "base.no_paperformat_probe",
            }
        )
        self.env.company.paperformat_id = False
        self.assertFalse(report.paperformat_id)

        paperformat = report.get_paperformat()
        self.assertEqual(
            paperformat,
            self.env.ref("base.paperformat_euro"),
            "an unconfigured report must fall back to the shipped default format",
        )

        css = self.env["ir.actions.report"]._prepare_paperformat_css(paperformat)
        self.assertIn(
            "margin: 30.0mm", css, "the fallback must carry real, non-zero margins"
        )
        empty_css = self.env["ir.actions.report"]._prepare_paperformat_css(
            self.env["report.paperformat"]
        )
        self.assertIn(
            "margin: 0.0mm 0.0mm 0.0mm 0.0mm",
            empty_css,
            "an empty paperformat is exactly the 0mm case the fallback avoids",
        )


ARTICLE_ARCH = """<t t-name="base.audit_multi_article"><html><head></head><body><main>
    <t t-foreach="docs" t-as="doc">
        <div class="article" data-oe-model="res.partner" t-att-data-oe-id="doc.id">
            <span t-field="doc.display_name" />
        </div>
    </t>
</main></body></html></t>"""


class MultiArticleReportCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.ui.view"].create(
            {
                "name": "audit multi article",
                "type": "qweb",
                "key": "base.audit_multi_article",
                "arch_db": ARTICLE_ARCH,
            }
        )
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Audit multi article",
                "model": "res.partner",
                "report_name": "base.audit_multi_article",
                "report_type": "qweb-pdf",
            }
        )
        cls.partners = cls.env["res.partner"].create(
            [{"name": "Audit Alpha"}, {"name": "Audit Beta"}]
        )

    def _render_pdf(self, pdf_options):
        Report = self.env["ir.actions.report"].with_context(force_report_rendering=True)
        pdf, _content_type = Report._render_qweb_pdf(
            self.report, self.partners.ids, data={PDF_OPTIONS_DATA_KEY: pdf_options}
        )
        return pdf


@tagged("post_install", "-at_install")
class TestReportGroupAccess(MultiArticleReportCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report.group_ids = cls.env.ref("base.group_system")
        cls.plain_user = cls.env["res.users"].create(
            {
                "name": "Audit Plain",
                "login": "audit_plain_report",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def _report_as_plain_user(self):
        return self.env["ir.actions.report"].with_user(self.plain_user)

    def _hide_partners_from_plain_user(self):
        self.env["ir.rule"].create(
            {
                "name": "audit: hide the article partners",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": [("id", "not in", self.partners.ids)],
                "groups": [(4, self.env.ref("base.group_user").id)],
            }
        )

    def test_a_user_outside_the_groups_renders_records_it_can_read(self):
        Report = self._report_as_plain_user()
        for report_ref in (self.report.id, self.report.report_name, self.report):
            with self.subTest(report_ref=report_ref):
                content, _type = Report._render_qweb_html(report_ref, self.partners.ids)
                self.assertIn(b"Audit Alpha", content)
        content, _type = Report.with_context(
            force_report_rendering=True
        )._render_qweb_pdf(self.report.id, self.partners.ids)
        self.assertTrue(content)

    def test_a_user_who_cannot_read_the_records_cannot_render_them(self):
        self._hide_partners_from_plain_user()
        Report = self._report_as_plain_user()
        with self.assertRaises(AccessError):
            Report._render_qweb_html(self.report.id, self.partners.ids)
        with self.assertRaises(AccessError):
            Report.with_context(force_report_rendering=True)._render_qweb_pdf(
                self.report.id, self.partners.ids
            )
        content, _type = Report.sudo()._render_qweb_html(
            self.report.id, self.partners.ids
        )
        self.assertIn(b"Audit Alpha", content)

    def test_a_stored_attachment_is_not_served_to_a_user_who_cannot_read(self):
        self.report.write({"attachment": "'audit.pdf'", "attachment_use": True})
        Report = self.env["ir.actions.report"].with_context(force_report_rendering=True)
        Report._render_qweb_pdf(self.report.id, self.partners.ids)
        self.assertTrue(
            self.env["ir.attachment"].search_count(
                [("res_model", "=", "res.partner"), ("res_id", "in", self.partners.ids)]
            )
        )
        self._hide_partners_from_plain_user()
        with self.assertRaises(AccessError):
            Report.with_user(self.plain_user)._render_qweb_pdf(
                self.report.id, self.partners.ids
            )

    def test_the_toolbar_keeps_filtering_by_group(self):
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.plain_user)
            .get_bindings("res.partner")
        )
        self.assertNotIn(
            self.report.id, [action["id"] for action in bindings.get("report", [])]
        )


@tagged("post_install", "-at_install")
class TestGetReportFromName(TransactionCase):
    def test_keeps_the_caller_context_and_returns_the_sudo_report(self):
        report = (
            self.env["ir.actions.report"]
            .with_context(audit_marker=1)
            ._get_report_from_name("base.report_irmodulereference")
        )
        self.assertEqual(report, self.env.ref("base.ir_module_reference_print"))
        self.assertTrue(report.env.su)
        self.assertEqual(report.env.context.get("audit_marker"), 1)

    def test_a_missing_or_empty_name_is_an_empty_recordset(self):
        Report = self.env["ir.actions.report"]
        self.assertFalse(Report._get_report_from_name("base.__no_such_report__"))
        self.assertFalse(Report._get_report_from_name("no_dot_no_report"))
        self.assertFalse(Report._get_report_from_name(None))


@tagged("post_install", "-at_install")
class TestMultiRecordDocumentOptions(MultiArticleReportCase):
    def test_pdfa_survives_a_two_record_render(self):
        pdf = self._render_pdf({"pdf_variant": "pdf/a-3b"})
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            self.assertEqual(doc.page_count, 2)
            kind, _value = doc.xref_get_key(doc.pdf_catalog(), "OutputIntents")
            self.assertEqual(
                kind,
                "array",
                "merging per-record PDFs with pypdf drops the PDF/A output intent",
            )
            self.assertIn("pdfaid", doc.get_xml_metadata())

    def test_pdfa_survives_the_tolerant_font_retry(self):
        from odoo.addons.base.models import ir_actions_report as mod

        render_document = mod._render_html_document
        failures = {"left": 1}

        class _FailingOnceDocument:
            def __init__(self, document):
                self._document = document

            def __getattr__(self, name):
                return getattr(self._document, name)

            def copy(self, *args, **kwargs):
                return _FailingOnceDocument(self._document.copy(*args, **kwargs))

            def write_pdf(self, *args, **kwargs):
                if failures["left"]:
                    failures["left"] -= 1
                    raise ValueError("expected 0 <= int <= 122, got 200")
                return self._document.write_pdf(*args, **kwargs)

        def render_failing_once(*args, **kwargs):
            return _FailingOnceDocument(render_document(*args, **kwargs))

        with (
            patch.object(mod, "_render_html_document", render_failing_once),
            mute_logger("odoo.addons.base.models.ir_actions_report"),
        ):
            pdf = self._render_pdf({"pdf_variant": "pdf/a-3b"})
        self.assertEqual(failures["left"], 0, "the tolerant-font retry did not run")
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            self.assertEqual(doc.page_count, 2)
            kind, _value = doc.xref_get_key(doc.pdf_catalog(), "OutputIntents")
            self.assertEqual(
                kind,
                "array",
                "the tolerant-font retry merged per-record PDFs with pypdf and "
                "dropped the PDF/A output intent",
            )
            self.assertIn("pdfaid", doc.get_xml_metadata())

    def test_attachments_survive_a_two_record_render(self):
        pdf = self._render_pdf(
            {"attachments": [{"content": b"audit-payload", "name": "audit.txt"}]}
        )
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            self.assertEqual(doc.page_count, 2)
            self.assertEqual(doc.embfile_names(), ["audit.txt"])

    def test_engine_split_render_keeps_only_per_body_options(self):
        import weasyprint

        engine = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._prepare_weasyprint_engine()
        )
        body = "<html><body><main>audit</main></body></html>"
        pdfs = engine.render(
            [body, body],
            "",
            split=True,
            pdf_options={
                "attachments": [weasyprint.Attachment(string=b"x", name="x.txt")],
                "dpi": 72,
            },
        )
        self.assertEqual(len(pdfs), 2)
        for pdf in pdfs:
            self.assertTrue(pdf.startswith(b"%PDF"))


@tagged("post_install", "-at_install")
class TestLayoutCssMargins(MultiArticleReportCase):
    def _bodies(self):
        html = self.env["ir.actions.report"]._render_qweb_html(
            self.report, self.partners.ids
        )[0]
        bodies, _res_ids, _args = self.report._prepare_weasyprint_html(
            html, report_model="res.partner"
        )
        return [str(body) for body in bodies]

    def test_a_report_without_xmlid_gets_its_own_paperformat_margins(self):
        Paperformat = self.env["report.paperformat"]
        self.env.company.paperformat_id = Paperformat.create(
            {"name": "audit company", "css_margins": False}
        )
        self.report.paperformat_id = Paperformat.create(
            {"name": "audit report", "css_margins": True}
        )
        self.assertFalse(self.report.xml_id)
        for body in self._bodies():
            self.assertIn(
                "o_css_margins",
                body,
                "the layout resolved the paperformat by xmlid, which a "
                "UI-created report does not have, so it fell back to the company's",
            )
        self.report.paperformat_id.css_margins = False
        for body in self._bodies():
            self.assertNotIn("o_css_margins", body)

    def test_a_direct_layout_render_still_falls_back_to_the_company(self):
        self.env.company.paperformat_id = self.env["report.paperformat"].create(
            {"name": "audit company", "css_margins": True}
        )
        html = self.env["ir.actions.report"]._render_template(
            "web.minimal_layout", {"subst": True, "body": "audit"}
        )
        self.assertIn(b"o_css_margins", html)


@tagged("post_install", "-at_install")
class TestLayoutRenderedOncePerLanguage(MultiArticleReportCase):
    def test_three_articles_render_the_layout_once(self):
        self.partners |= self.env["res.partner"].create({"name": "Audit Gamma"})
        html = self.env["ir.actions.report"]._render_qweb_html(
            self.report, self.partners.ids
        )[0]
        layout_id = self.env.ref("web.minimal_layout").id
        registry_cls = type(self.env["ir.qweb"])
        original_render = registry_cls._render
        layout_renders = []

        def counting_render(model, template, values=None, **options):
            if template == layout_id:
                layout_renders.append(values)
            return original_render(model, template, values, **options)

        with patch.object(registry_cls, "_render", counting_render):
            bodies, res_ids, _args = self.report._prepare_weasyprint_html(
                html, report_model="res.partner"
            )
        self.assertEqual(res_ids, self.partners.ids)
        self.assertEqual(len(layout_renders), 1)
        for body, partner in zip(bodies, self.partners, strict=True):
            self.assertIn(partner.name, str(body))
            self.assertEqual(str(body).count("<html"), 1)
        self.assertNotIn("odoo-report-body", str(bodies[0]))


@tagged("post_install", "-at_install")
class TestHtmlToImageUsesTheEngine(TransactionCase):
    def test_bodies_are_rendered_by_the_shared_engine(self):
        registry_cls = type(self.env["ir.actions.report"])
        engine = MagicMock()
        engine.render_each_tolerant.return_value = [None, None]
        with patch.object(
            registry_cls, "_prepare_weasyprint_engine", return_value=engine
        ):
            result = (
                self.env["ir.actions.report"]
                .with_context(force_report_rendering=True)
                ._render_html_to_image(["<div>a</div>", "<div>b</div>"], 10, 10)
            )
        self.assertEqual(result, [None, None])
        engine.render_each_tolerant.assert_called_once()
        bodies, page_css = engine.render_each_tolerant.call_args.args
        self.assertEqual(len(bodies), 2)
        self.assertIn("size: 10px 10px", page_css)
