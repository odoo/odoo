import io
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from odoo import http
from odoo.libs.json import dumps as json_dumps
from odoo.tests.common import BaseCase, HttpCase, TransactionCase, tagged
from odoo.tools import file_path, mute_logger


@tagged("web_http", "web_controllers_audit")
class TestBarcodeInvalidType(HttpCase):
    def test_barcode_invalid_type_returns_400(self):
        response = self.url_open("/report/barcode/TOTALLY_INVALID_TYPE/testvalue")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)


@tagged("web_controllers_audit")
class TestBarcodeDimensionClamp(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.web.controllers.report import (
            _MAX_BARCODE_DIM,
            _clamp_barcode_dimension,
        )

        cls._clamp = staticmethod(_clamp_barcode_dimension)
        cls._max = _MAX_BARCODE_DIM

    def test_oversized_is_clamped_to_max(self):
        self.assertEqual(self._clamp(100_000, 600), self._max)
        self.assertEqual(self._clamp(self._max + 1, 100), self._max)

    def test_reasonable_value_passes_through(self):
        self.assertEqual(self._clamp(200, 600), 200)
        self.assertEqual(self._clamp("300", 600), 300)

    def test_invalid_or_nonpositive_falls_back_to_default(self):
        self.assertEqual(self._clamp("not-a-number", 600), 600)
        self.assertEqual(self._clamp(None, 100), 100)
        self.assertEqual(self._clamp(0, 600), 600)
        self.assertEqual(self._clamp(-5, 100), 100)


@tagged("web_http", "web_controllers_audit")
class TestBarcodeDimensionClampHttp(HttpCase):
    def test_huge_dimensions_do_not_500(self):
        response = self.url_open(
            "/report/barcode/Code128/hello?width=100000&height=100000"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_clamped_single_dimension_renders(self):
        response = self.url_open(
            "/report/barcode/Code128/hello?width=100000&height=100"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")

    def test_oversized_value_rejected(self):
        huge = "A" * 40000
        response = self.url_open(f"/report/barcode/Code128/{huge}")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_normal_value_still_renders(self):
        response = self.url_open("/report/barcode/Code128/HELLO-12345")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")


@tagged("web_http", "web_controllers_audit")
class TestImageDimensionGuard(HttpCase):
    def test_garbage_width_does_not_500(self):
        response = self.url_open("/web/image/99999999?width=abc&height=xyz")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")


@tagged("web_controllers_audit")
class TestCsvFormulaNeutralization(BaseCase):
    def test_dangerous_leading_chars_are_prefixed(self):
        from odoo.addons.web.controllers.export import CSVExport

        rows = [["=cmd"], ["+cmd"], ["-cmd"], ["@cmd"], ["\t=x"]]
        out = CSVExport().from_data([], ["header"], rows).decode()
        for payload in ("=cmd", "+cmd", "-cmd", "@cmd"):
            self.assertIn(
                f"'{payload}",
                out,
                f"{payload!r} must be apostrophe-prefixed to defuse the formula",
            )

    def test_benign_values_are_not_mangled(self):
        from odoo.addons.web.controllers.export import CSVExport

        out = CSVExport().from_data([], ["header"], [["a=b"], ["safe"]]).decode()
        self.assertIn("a=b", out)
        self.assertNotIn("'a=b", out)
        self.assertNotIn("'safe", out)


@tagged("web_http", "web_controllers_audit")
class TestPivotNegativeInputs(HttpCase):
    def test_export_xlsx_negative_measure_count(self):
        self.authenticate("admin", "admin")
        jdata = {
            "title": "Test",
            "model": "res.partner",
            "measure_count": -5,
            "origin_count": 1,
            "col_group_headers": [],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_export_xlsx_negative_header_width(self):
        self.authenticate("admin", "admin")
        jdata = {
            "title": "Test",
            "model": "res.partner",
            "measure_count": 1,
            "origin_count": 1,
            "col_group_headers": [[{"title": "A", "width": -3, "height": 1}]],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_export_xlsx_huge_indent_is_clamped(self):
        self.authenticate("admin", "admin")
        jdata = {
            "title": "Test",
            "model": "res.partner",
            "measure_count": 1,
            "origin_count": 1,
            "col_group_headers": [],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [{"indent": 400_000_000, "title": "row", "values": []}],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertLess(len(response.content), 1_000_000)


@tagged("web_http", "web_controllers_audit")
class TestWebClientOpenRedirect(HttpCase):
    def test_backslash_redirect_rejected(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/odoo?redirect=%2F%5Cevil.com",
            allow_redirects=False,
        )
        location = response.headers.get("Location", "")
        self.assertNotIn("evil.com", location)

    def test_local_path_redirect_accepted(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/odoo?redirect=/odoo/contacts",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, HTTPStatus.SEE_OTHER)
        self.assertIn("/odoo/contacts", response.headers.get("Location", ""))


@tagged("web_http", "web_controllers_audit")
class TestCompanyLogoFallback(HttpCase):
    def test_a_failing_lookup_serves_the_odoo_logo(self):
        odoo_logo = Path(file_path("web/static/img/logo.png")).read_bytes()
        with (
            patch(
                "odoo.addons.web.controllers.binary.guess_mimetype",
                side_effect=RuntimeError("simulated"),
            ),
            mute_logger("odoo.addons.web.controllers.binary"),
        ):
            response = self.url_open("/logo?company=1")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.content, odoo_logo)


@tagged("web_http", "web_controllers_audit")
class TestDatabaseRestoreLogging(HttpCase):
    def test_restore_logs_exception_on_failure(self):
        with (
            patch(
                "odoo.tools.config.configmanager.is_valid_admin_password",
                return_value=False,
            ),
            patch("odoo.service.db.check_super"),
            patch(
                "odoo.service.db.restore_db",
                side_effect=Exception("simulated restore error"),
            ),
            self.assertLogs(
                "odoo.addons.web.controllers.database", level="ERROR"
            ) as log_cm,
        ):
            response = self.url_open(
                "/web/database/restore",
                data={
                    "master_pwd": "admin",
                    "name": "test_audit_nonexistent_db",
                    "copy": "false",
                    "neutralize_database": "false",
                },
                files={
                    "backup_file": (
                        "test.zip",
                        io.BytesIO(b"fake content"),
                        "application/zip",
                    )
                },
            )
        self.assertIn("Database restore error", response.text)
        self.assertTrue(
            any("Database restore error" in msg for msg in log_cm.output),
            f"Expected 'Database restore error' in logs, got: {log_cm.output}",
        )


@tagged("web_http", "web_controllers_audit")
class TestExportGroupbyValidation(HttpCase):
    @mute_logger("odoo.addons.web.controllers.export")
    def test_invalid_groupby_field_returns_descriptive_error(self):
        self.authenticate("admin", "admin")
        data = json_dumps(
            {
                "model": "res.partner",
                "fields": [{"name": "name", "label": "Name"}],
                "ids": [],
                "domain": [],
                "import_compat": False,
                "groupby": ["totally_nonexistent_xyz"],
            }
        )
        response = self.url_open(
            "/web/export/xlsx",
            data={"data": data, "csrf_token": http.Request.csrf_token(self)},
        )
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertIn("Unknown groupby fields", response.text)
        self.assertIn("totally_nonexistent_xyz", response.text)


@tagged("web_controllers_audit")
class TestIsLocalUrl(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.web.controllers.utils import _is_local_url

        cls._is_local_url = staticmethod(_is_local_url)

    def test_local_paths_accepted(self):
        self.assertTrue(self._is_local_url("/odoo"))
        self.assertTrue(self._is_local_url("/odoo/contacts"))
        self.assertTrue(self._is_local_url("/web"))
        self.assertTrue(self._is_local_url("/web/login"))

    def test_protocol_relative_rejected(self):
        self.assertFalse(self._is_local_url("//evil.com"))

    def test_backslash_trick_rejected(self):
        self.assertFalse(self._is_local_url("/\\evil.com"))

    def test_absolute_url_rejected(self):
        self.assertFalse(self._is_local_url("https://evil.com"))
        self.assertFalse(self._is_local_url("http://evil.com/odoo"))

    def test_unparseable_url_rejected_rather_than_raising(self):
        for vector in ("http://[", "http://[x", "http://a[b"):
            with self.subTest(vector=vector):
                self.assertFalse(self._is_local_url(vector))

    def test_a_bracket_outside_an_authority_is_an_ordinary_path(self):
        self.assertTrue(self._is_local_url("/["))
        self.assertTrue(self._is_local_url("/a[b"))

    def test_embedded_tab_newline_rejected(self):
        for vector in (
            "/\t\t//evil.com",
            "/\r\r//evil.com",
            "/\n\n//evil.com",
            "/\t/\t/evil.com",
            "\t//evil.com",
        ):
            with self.subTest(vector=vector):
                self.assertFalse(self._is_local_url(vector))

    def test_multiple_leading_slashes_rejected(self):
        self.assertFalse(self._is_local_url("///evil.com"))
        self.assertFalse(self._is_local_url("////evil.com"))

    def test_whitespace_only_rejected(self):
        self.assertFalse(self._is_local_url("\t"))
        self.assertFalse(self._is_local_url("\r\n"))

    def test_empty_and_none_rejected(self):
        self.assertFalse(self._is_local_url(""))
        self.assertFalse(self._is_local_url(None))


@tagged("web_controllers_audit")
class TestJsonHelpers(TransactionCase):
    def test_get_groupby_with_default_group_by(self):
        from odoo.addons.web.controllers.json_helpers import get_groupby

        tree = etree.fromstring(
            '<kanban default_group_by="partner_id"><templates/></kanban>'
        )
        groupby, fields = get_groupby(tree)
        self.assertIsNone(groupby)
        self.assertEqual(fields, ["partner_id"])

    def test_get_groupby_no_default_group_by(self):
        from odoo.addons.web.controllers.json_helpers import get_groupby

        tree = etree.fromstring("<kanban><templates/></kanban>")
        groupby, fields = get_groupby(tree)
        self.assertIsNone(groupby)
        self.assertIsNone(fields)

    def test_get_groupby_explicit_param_overrides_view(self):
        from odoo.addons.web.controllers.json_helpers import get_groupby

        tree = etree.fromstring(
            '<kanban default_group_by="stage_id"><templates/></kanban>'
        )
        groupby, fields = get_groupby(tree, groupby="partner_id,user_id")
        self.assertEqual(groupby, ["partner_id", "user_id"])
        self.assertIsNone(fields)

    def test_get_view_id_and_type_returns_false_for_unset_view(self):
        from odoo.addons.web.controllers.json_helpers import get_view_id_and_type

        action = self.env["ir.actions.act_window"].create(
            {
                "name": "_AuditTest",
                "res_model": "res.partner",
                "view_mode": "list,form",
            }
        )
        view_id, view_type = get_view_id_and_type(action, "list")
        self.assertIs(
            view_id, False, "Must be False (Odoo 'no ID' convention), not None"
        )
        self.assertEqual(view_type, "list")


@tagged("web_http", "web_controllers_audit")
class TestActionLoadEdges(HttpCase):
    def _rpc(self, path, params):
        return self.url_open(
            path,
            headers={"Content-Type": "application/json"},
            data=json_dumps({"params": params}),
        ).json()

    def test_load_with_a_null_id_is_a_missing_action_not_a_type_error(self):
        self.authenticate("admin", "admin")
        with mute_logger("odoo.http"):
            body = self._rpc("/web/action/load", {"action_id": None})
        self.assertIn("error", body)
        self.assertIn("MissingActionError", body["error"]["data"]["name"])

    def test_breadcrumb_of_a_report_action_with_a_record_has_no_res_model(self):
        self.authenticate("admin", "admin")
        report = self.env["ir.actions.report"].search([], limit=1)
        body = self._rpc(
            "/web/action/load_breadcrumbs",
            {"actions": [{"action": report.id, "resId": 1}]},
        )
        self.assertEqual(body["result"], [{"display_name": report.name}])


@tagged("web_http", "web_controllers_audit")
class TestSignFonts(HttpCase):
    def _rpc(self, path):
        return self.url_open(
            path,
            headers={"Content-Type": "application/json"},
            data=json_dumps({"params": {}}),
        ).json()

    def test_unknown_font_is_not_found(self):
        with mute_logger("odoo.http"):
            body = self._rpc("/web/sign/get_fonts/no_such_font.ttf")
        self.assertIn("NotFound", body["error"]["data"]["name"])

    def test_wrong_extension_is_not_found(self):
        with mute_logger("odoo.http"):
            body = self._rpc("/web/sign/get_fonts/__manifest__.py")
        self.assertIn("NotFound", body["error"]["data"]["name"])

    def test_listing_answers_every_sign_font(self):
        body = self._rpc("/web/sign/get_fonts")
        self.assertGreater(len(body["result"]), 0)
        fonts_dir = Path(file_path("web/static/fonts/sign"))
        first = min(
            p.name
            for p in fonts_dir.iterdir()
            if p.suffix in (".ttf", ".otf", ".woff", ".woff2")
        )
        one = self._rpc(f"/web/sign/get_fonts/{first}")
        self.assertEqual(one["result"], body["result"][:1])


@tagged("web_http", "web_controllers_audit")
class TestBaseSetupData(HttpCase):
    def test_pending_users_are_the_internal_ones_that_never_logged_in(self):
        never = self.env["res.users"].create(
            {"name": "Never Logged", "login": "never_logged_audit"}
        )
        self.authenticate("admin", "admin")
        body = self.url_open(
            "/base_setup/data",
            headers={"Content-Type": "application/json"},
            data=json_dumps({"params": {}}),
        ).json()["result"]
        self.assertEqual(body["pending_users"][0], [never.id, never.login])
        self.assertEqual(body["pending_count"], len(body["pending_users"]))
        self.assertGreaterEqual(body["active_users"], body["pending_count"] + 1)
        self.assertEqual(body["action_pending_users"]["res_model"], "res.users")


@tagged("web_controllers_audit")
class TestObservabilityHelpers(BaseCase):
    def test_clamped_metric_rejects_bool_nan_negative_and_oversized(self):
        from odoo.addons.web.controllers.observability import _get_clamped_metric

        self.assertIsNone(_get_clamped_metric(True, 10))
        self.assertIsNone(_get_clamped_metric(float("nan"), 10))
        self.assertIsNone(_get_clamped_metric(-1, 10))
        self.assertIsNone(_get_clamped_metric(11, 10))
        self.assertIsNone(_get_clamped_metric("5", 10))
        self.assertEqual(_get_clamped_metric(5, 10), 5.0)

    def test_capped_str_and_positive_int(self):
        from odoo.addons.web.controllers.observability import (
            _get_capped_str,
            _get_positive_int,
        )

        self.assertEqual(_get_capped_str("abcdef", 3), "abc")
        self.assertEqual(_get_capped_str(42, 3), "")
        self.assertEqual(_get_positive_int(-1), 0)
        self.assertEqual(_get_positive_int(3.9), 3)
        self.assertEqual(_get_positive_int("3"), 0)


@tagged("web_controllers_audit")
class TestReportHelpers(BaseCase):
    def test_parse_docids_keeps_digits_only(self):
        from odoo.addons.web.controllers.report import _parse_docids

        self.assertIsNone(_parse_docids(None))
        self.assertIsNone(_parse_docids(""))
        self.assertEqual(_parse_docids("1,x,3"), [1, 3])

    def test_download_url_splits_report_docids_and_query(self):
        from odoo.http import BadRequest

        from odoo.addons.web.controllers.report import ReportController

        parse = ReportController()._parse_report_download_url
        self.assertEqual(
            parse("/report/pdf/base.report_x/1,2?context=%7B%7D", "pdf"),
            ("base.report_x", "1,2", {"context": "{}"}),
        )
        self.assertEqual(
            parse("/report/text/base.report_x?a=1&a=2", "text"),
            ("base.report_x", None, {"a": "1"}),
        )
        with self.assertRaises(BadRequest):
            parse("/report/pdf/base.report_x", "text")


@tagged("web_controllers_audit")
class TestCappedWorksheet(BaseCase):
    def test_write_counts_and_refuses_past_the_cap(self):
        from odoo.http import UnprocessableEntity

        from odoo.addons.web.controllers.pivot import _CappedWorksheet

        class Sheet:
            written = []

            def write(self, *args, **kwargs):
                self.written.append(args)

            def freeze_panes(self, *args):
                return args

        sheet = Sheet()
        capped = _CappedWorksheet(sheet, 2, "t")
        capped.write(0, 0, "a")
        capped.write(0, 1, "b")
        self.assertEqual(capped.cells_written, 2)
        self.assertEqual(capped.freeze_panes(1, 0), (1, 0))
        with self.assertRaises(UnprocessableEntity):
            capped.write(0, 2, "c")
        self.assertEqual(len(sheet.written), 2)


@tagged("web_http", "web_controllers_audit")
class TestReportConverters(HttpCase):
    def test_unknown_converter_is_a_client_error(self):
        self.authenticate("admin", "admin")
        with mute_logger("odoo.http"):
            resp = self.url_open("/report/docx/web.report_irmodulereference/1")
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

    def test_describing_a_mixin_on_the_read_only_route_writes_nothing(self):
        self.authenticate("admin", "admin")
        module = self.env.ref("base.module_base")
        with self.assertNoLogs(
            "odoo.addons.web.reports.report_web_report_irmodulereference",
            level="WARNING",
        ):
            resp = self.url_open(
                f"/report/html/web.report_irmodulereference/{module.id}"
            )
        self.assertEqual(resp.status_code, HTTPStatus.OK)

    def test_text_converter_answers_plain_text(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            f"/report/text/web.preview_internalreport/{self.env.company.id}"
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertTrue(resp.headers["Content-Type"].startswith("text/plain"))
        self.assertEqual(int(resp.headers["Content-Length"]), len(resp.content))


@tagged("web_http", "web_controllers_audit")
class TestUncoveredRoutes(HttpCase):
    def _rpc(self, path, params=None):
        return self.url_open(
            path,
            headers={"Content-Type": "application/json"},
            data=json_dumps({"params": params or {}}),
        ).json()

    def test_robots_disallows_everything_by_default(self):
        resp = self.url_open("/robots.txt")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertTrue(resp.headers["Content-Type"].startswith("text/plain"))
        self.assertEqual(resp.text.splitlines(), ["User-agent: *", "Disallow: /"])

    def test_filestore_is_never_served_by_odoo(self):
        with mute_logger("odoo.http"):
            resp = self.url_open("/web/filestore/odoo7f/00/deadbeef")
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_become_promotes_a_system_user_and_nobody_else(self):
        self.authenticate("admin", "admin")
        resp = self.url_open("/web/become", allow_redirects=False)
        self.assertEqual(resp.status_code, HTTPStatus.SEE_OTHER)
        self.assertEqual(self._rpc("/web/session/get_session_info")["result"]["uid"], 1)

        user = self.env["res.users"].create(
            {
                "name": "Plain Internal",
                "login": "plain_internal_audit",
                "password": "plain_internal_audit",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.authenticate("plain_internal_audit", "plain_internal_audit")
        resp = self.url_open("/web/become", allow_redirects=False)
        self.assertEqual(resp.status_code, HTTPStatus.SEE_OTHER)
        self.assertEqual(
            self._rpc("/web/session/get_session_info")["result"]["uid"], user.id
        )

    def test_openapi_document_is_for_system_users_only(self):
        self.authenticate("admin", "admin")
        resp = self.url_open("/web/openapi.json")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        document = resp.json()
        self.assertEqual(document["info"]["title"], "Odoo HTTP API")
        self.assertIsInstance(document["paths"], dict)

        self.env["res.users"].create(
            {
                "name": "Plain Internal",
                "login": "plain_internal_audit",
                "password": "plain_internal_audit",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.authenticate("plain_internal_audit", "plain_internal_audit")
        with mute_logger("odoo.http"):
            resp = self.url_open("/web/openapi.json")
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

    def test_edit_custom_writes_only_the_owner_s_view(self):
        view = self.env.ref("base.view_partner_form")
        admin = self.env.ref("base.user_admin")
        other = self.env["res.users"].create(
            {
                "name": "Other Internal",
                "login": "other_internal_audit",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        own = self.env["ir.ui.view.custom"].create(
            {"ref_id": view.id, "user_id": admin.id, "arch": "<form/>"}
        )
        theirs = self.env["ir.ui.view.custom"].create(
            {"ref_id": view.id, "user_id": other.id, "arch": "<form/>"}
        )
        self.authenticate("admin", "admin")
        body = self._rpc(
            "/web/view/edit_custom",
            {"custom_id": own.id, "arch": "<form><sheet/></form>"},
        )
        self.assertEqual(body["result"], {"result": True})
        self.assertEqual(own.arch, "<form><sheet/></form>")
        with mute_logger("odoo.http"):
            body = self._rpc(
                "/web/view/edit_custom", {"custom_id": theirs.id, "arch": "<form/>"}
            )
        self.assertIn("AccessError", body["error"]["data"]["name"])

    def test_scoped_app_icon_is_rasterised_with_padding(self):
        resp = self.url_open("/scoped_app_icon_png?app_id=web")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(resp.headers["Content-Type"], "image/png")
        self.assertTrue(resp.content.startswith(b"\x89PNG"))

    def test_esm_library_url_without_an_attachment_is_not_found(self):
        with mute_logger("odoo.http"):
            resp = self.url_open("/web/assets/lib/nope/vendor/thing.js")
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)


@tagged("web_controllers_audit")
class TestGroupedXlsxHeaderTolerance(BaseCase):
    def test_a_field_without_a_type_gets_the_plain_bold_header(self):
        from unittest.mock import MagicMock

        from odoo.addons.web.controllers.export_writers import GroupExportXlsxWriter

        writer = GroupExportXlsxWriter.__new__(GroupExportXlsxWriter)
        writer.fields = [{"name": "name"}, {"name": "id"}]
        writer.monetary_decimal_places = 2
        writer.header_bold_style = "bold"
        writer.header_bold_style_float = "float"
        writer.header_bold_style_monetary = "monetary"
        writer.write = MagicMock()
        group = MagicMock(count=2, aggregated_values={"id": 7})
        self.assertEqual(writer._write_group_header(0, 0, "G", group), (1, 0))
        writer.write.assert_any_call(0, 1, "7", "bold")
