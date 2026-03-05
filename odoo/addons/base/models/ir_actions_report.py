import io
import logging
import mimetypes
import re
import threading
from ast import literal_eval
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import parse_qs, urlparse
from warnings import deprecated

import cssselect2.compiler as _cs2_compiler
import lxml.html
import requests
import weasyprint
from cssselect2 import parser as _cs2_parser
from lxml import etree
from markupsafe import Markup
from PIL import Image, ImageFile
from weasyprint.css.counters import CounterStyle
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetcher, URLFetcherResponse

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import (
    AccessError,
    RedirectWarning,
    UserError,
    ValidationError,
)
from odoo.fields import Domain
from odoo.http import request, root
from odoo.libs.barcode import (
    check_barcode_encoding,
    createBarcodeDrawing,
    get_barcode_font,
)
from odoo.libs.json import loads as json_loads
from odoo.service import security
from odoo.tools import config, is_html_empty
from odoo.tools.pdf import PdfFileReader, PdfFileWriter, PdfReadError
from odoo.tools.safe_eval import safe_eval, time

if TYPE_CHECKING:
    from collections.abc import Callable

# WeasyPrint logs thousands of CSS warnings (box-shadow, @keyframes, vendor
# pseudo-elements, responsive @media queries, etc.) because the full web client
# CSS bundle includes Bootstrap and theme CSS designed for browsers, not paged
# media. These warnings are harmless — the properties are simply ignored — but
# they pollute logs and slow rendering. We suppress them here.
logging.getLogger("weasyprint").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Module-level WeasyPrint singletons — survive across requests within a
# worker process.  These expensive objects are created once and reused:
#
# - _weasy_font_config: Holds the Pango font map with loaded @font-face data.
#   The first write_pdf() call discovers system fonts via fontconfig (~30s cold,
#   <1s warm).  Subsequent calls reuse the loaded font map.
#
# - _weasy_image_cache: Decoded image data (company logo etc.) shared across
#   all renders — avoids re-decoding the same PNG for every body.
# ---------------------------------------------------------------------------
_weasy_font_config = FontConfiguration()
_weasy_image_cache = {}

# Regex to extract and strip <link rel="stylesheet"> tags from HTML.
# Lookaheads match rel="stylesheet" and href="..." in any attribute order.
_RE_CSS_LINK = re.compile(
    r'<link\b(?=[^>]*\brel=["\']stylesheet["\'])(?=[^>]*\bhref=["\']([^"\']+)["\'])[^>]*/?>',
    re.IGNORECASE,
)

# Pre-compiled XPath for report HTML structure extraction (lxml 6.0 best practice).
_xpath_main = etree.ETXPath("//main")
_xpath_header = etree.ETXPath(
    "//div[contains(concat(' ', normalize-space(@class), ' '), ' header ')]"
)
_xpath_footer = etree.ETXPath(
    "//div[contains(concat(' ', normalize-space(@class), ' '), ' footer ')]"
)
_xpath_article = etree.ETXPath(
    "//div[contains(concat(' ', normalize-space(@class), ' '), ' article ')]"
)

# Allow truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Workaround for CPython 3.14 compile() regression (bpo-XXXXX).
#
# Python 3.14 exhibits O(2^n) time in compile() for deeply nested generator
# expressions.  cssselect2 generates such expressions for descendant selectors
# like "ol ol ol ... ol" (common in Bootstrap CSS for list-style cycling).
# A 20-level selector takes ~9s to compile in 3.14 vs 0.001s in 3.12.
#
# Fix: wrap cssselect2's _compile_node to limit CombinedSelector recursion
# depth.  Selectors deeper than the limit return '0' (never match) — this is
# harmless since 10+-level descendant selectors never match in PDF reports.
# ---------------------------------------------------------------------------
_original_compile_node = _cs2_compiler._compile_node
_MAX_SELECTOR_DEPTH = 10
_selector_depth = threading.local()


def _compile_node_depth_limited(selector: Any) -> str:
    """Depth-limited wrapper around cssselect2's _compile_node.

    Uses thread-local storage to track recursion depth safely across Odoo's
    concurrent threaded workers.  The original approach of temporarily patching
    ``_cs2_compiler._compile_node`` was not thread-safe: two concurrent PDF
    renders could corrupt each other's depth counter via the shared global.
    """
    if isinstance(selector, _cs2_parser.CombinedSelector):
        depth = getattr(_selector_depth, "value", 0)
        if depth >= _MAX_SELECTOR_DEPTH:
            return "0"
        _selector_depth.value = depth + 1
        try:
            return _original_compile_node(selector)
        finally:
            _selector_depth.value = depth
    return _original_compile_node(selector)


_cs2_compiler._compile_node = _compile_node_depth_limited

# Regex patterns for local URL resolution (avoid HTTP self-requests)
_WEB_IMAGE_MODEL_RE = re.compile(
    r"^/web/image/(?P<model>[\w.]+)/(?P<id>\d+)/(?P<field>\w+)"
    r"(?:/(?P<width>\d+)x(?P<height>\d+))?"
)
_WEB_IMAGE_ID_RE = re.compile(
    r"^/web/image/(?P<id>\d+)(?:-[\w]+)?"
    r"(?:/(?P<width>\d+)x(?P<height>\d+))?"
)
_BARCODE_RE = re.compile(r"^/report/barcode/(?P<type>[^/]+)/(?P<value>.+)")


class OdooURLFetcher(URLFetcher):
    """WeasyPrint URL fetcher with Odoo resource resolution.

    Subclasses URLFetcher (v68+) so that HTTP redirects also go through
    :meth:`fetch`, fixing the SSRF vulnerability in the old function-based
    approach (CVE-2025-68616).

    Resolution order for local URLs:
    1. Asset bundles — ``/web/assets/<unique>/<filename>``
    2. Static files — ``/<module>/static/...`` from the filesystem
    3. HTTP fallback — session-authenticated request to the Odoo server

    External URLs are delegated to the parent :class:`URLFetcher`.

    Use as a context manager to ensure the temporary session is cleaned up::

        with OdooURLFetcher(env) as fetcher:
            weasyprint.HTML(string=html, url_fetcher=fetcher).write_pdf()
    """

    def __init__(self, env: Any, base_url: str | None = None) -> None:
        super().__init__(
            allowed_protocols=["http", "https", "file", "data"],
            allow_redirects=True,
        )
        self._env = env
        self._base_url = base_url or env["ir.actions.report"]._get_report_url()
        self._parsed_base = urlparse(self._base_url)
        self._addons_paths = config["addons_path"]
        self._session_cookie = None
        self._temp_session = None
        self._setup_session()

    # -- Context manager --------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Delete the temporary session created for authenticated fetches."""
        if self._temp_session is not None:
            root.session_store.delete(self._temp_session)
            self._temp_session = None

    # -- Session setup ----------------------------------------------------

    def _setup_session(self) -> None:
        if request and request.db:
            self._temp_session = root.session_store.new()
            self._temp_session.update(
                {
                    **request.session,
                    "debug": "",
                    "_trace_disable": True,
                }
            )
            if self._temp_session.uid:
                self._temp_session.session_token = security.compute_session_token(
                    self._temp_session,
                    self._env,
                )
            root.session_store.save(self._temp_session)
            self._session_cookie = self._temp_session.sid

    # -- Core fetch -------------------------------------------------------

    def fetch(
        self, url: str, headers: dict[str, str] | None = None
    ) -> URLFetcherResponse:
        """Resolve Odoo URLs locally or delegate to the parent fetcher."""
        parsed = urlparse(url)

        # Non-HTTP schemes (data:, file:) are handled natively by the parent
        # URLFetcher via urllib handlers — don't intercept them.
        if parsed.scheme and parsed.scheme not in ("http", "https", ""):
            return super().fetch(url, headers)

        is_local = not parsed.hostname or parsed.hostname in (
            self._parsed_base.hostname,
            "localhost",
        )
        if not is_local:
            return super().fetch(url, headers)

        path = parsed.path or ""

        # 1. Asset bundles: /web/assets/<unique>/<filename>
        if "/web/assets/" in path:
            result = self._resolve_asset_bundle(url, path)
            if result:
                return result

        # 2. Static files: /module/static/...
        if "/static/" in path:
            result = self._resolve_static_file(url, path)
            if result:
                return result

        # 3. Images: /web/image/<model>/<id>/<field> or /web/image/<id>
        if "/web/image/" in path:
            result = self._resolve_web_image(url, path, parsed.query)
            if result:
                return result

        # 4. Barcodes: /report/barcode/<type>/<value>
        if "/report/barcode/" in path:
            result = self._resolve_barcode(url, path, parsed.query)
            if result:
                return result

        # 5. HTTP fallback with session cookie
        return self._fetch_via_http(url, path)

    # -- Resolution helpers -----------------------------------------------

    def _resolve_asset_bundle(self, url: str, path: str) -> URLFetcherResponse | None:
        """Resolve ``/web/assets/<unique>/<filename>`` from ir.attachment or on-the-fly."""
        parts = path.strip("/").split("/")
        if len(parts) < 4 or parts[0] != "web" or parts[1] != "assets":
            return None

        unique = parts[2]
        filename = parts[3]
        debug_assets = unique == "debug"

        # Try cached attachment first
        if not debug_assets:
            attachment = (
                self._env["ir.attachment"]
                .sudo()
                .search(
                    [
                        ("public", "=", True),
                        ("url", "=", path),
                        ("res_model", "=", "ir.ui.view"),
                        ("res_id", "=", 0),
                    ],
                    limit=1,
                )
            )
            if attachment and attachment.raw:
                return self._make_response(
                    url, attachment.raw, attachment.mimetype or "text/css"
                )

        # Generate the bundle on-the-fly
        try:
            bundle_name, rtl, asset_type, autoprefix = self._env[
                "ir.asset"
            ]._parse_bundle_name(filename, debug_assets)
            bundle = self._env["ir.qweb"]._get_asset_bundle(
                bundle_name,
                css=(asset_type == "css"),
                js=(asset_type == "js"),
                debug_assets=debug_assets,
                rtl=rtl,
                autoprefix=autoprefix,
            )
            attachment = None
            if asset_type == "css" and bundle.stylesheets:
                attachment = bundle.css()
            elif asset_type == "js" and bundle.javascripts:
                attachment = bundle.js()
            if attachment and attachment.raw:
                return self._make_response(
                    url, attachment.raw, attachment.mimetype or "text/css"
                )
        except Exception:
            _logger.warning("Failed to generate asset bundle for %s", path)
        return None

    def _resolve_static_file(self, url: str, path: str) -> URLFetcherResponse | None:
        """Resolve ``/<module>/static/...`` from the filesystem."""
        parts = path.lstrip("/").split("/")
        if len(parts) < 3 or parts[1] != "static":
            return None
        module_name = parts[0]
        static_path = "/".join(parts[1:])
        for addons_path in self._addons_paths:
            root = Path(addons_path.strip()).resolve()
            candidate = (root / module_name / static_path).resolve()
            # Ensure resolved path stays within the addons directory.
            # Use is_relative_to() for proper path-component checking —
            # str.startswith() would accept sibling dirs (e.g. addons-private).
            if not candidate.is_relative_to(root):
                continue
            if candidate.is_file():
                mime = mimetypes.guess_type(candidate)[0] or "application/octet-stream"
                with Path(candidate).open("rb") as f:
                    return self._make_response(url, f.read(), mime)
        return None

    def _resolve_web_image(
        self, url: str, path: str, query: str,
    ) -> URLFetcherResponse | None:
        """Resolve ``/web/image/`` URLs directly from the database/filestore.

        Avoids HTTP self-requests that deadlock when all workers are busy.
        Falls back to None so the caller can try the HTTP fetcher.
        """
        try:
            model, res_id, field, width, height = self._parse_image_url(path, query)
            ir_binary = self._env["ir.binary"].sudo()
            record = ir_binary._find_record(res_model=model, res_id=res_id, field=field)
            stream = ir_binary._get_image_stream_from(
                record, field, width=width, height=height,
            )
            data = stream.read()
            if data:
                return self._make_response(url, data, stream.mimetype or "image/png")
        except Exception:
            _logger.debug("Local image resolution failed for %s", path)
        return None

    def _resolve_barcode(
        self, url: str, path: str, query: str,
    ) -> URLFetcherResponse | None:
        """Resolve ``/report/barcode/`` URLs by generating the barcode directly.

        Avoids HTTP self-requests that deadlock when all workers are busy.
        """
        try:
            match = _BARCODE_RE.match(path)
            if match:
                barcode_type = match.group("type")
                value = match.group("value")
            else:
                params = parse_qs(query)
                barcode_type = params.get("barcode_type", [None])[0]
                value = params.get("value", [None])[0]

            if not barcode_type or not value:
                return None

            params = parse_qs(query)
            kwargs = {}
            for key in ("width", "height", "humanreadable", "quiet", "mask", "barLevel"):
                val = params.get(key, [None])[0]
                if val is not None:
                    kwargs[key] = val

            barcode_bytes = (
                self._env["ir.actions.report"].sudo().barcode(
                    barcode_type, value, **kwargs,
                )
            )
            if barcode_bytes:
                return self._make_response(url, barcode_bytes, "image/png")
        except Exception:
            _logger.debug("Local barcode resolution failed for %s", path)
        return None

    @staticmethod
    def _parse_image_url(path: str, query: str) -> tuple:
        """Extract model, id, field, width, height from a ``/web/image/`` URL."""
        width = 0
        height = 0

        match = _WEB_IMAGE_MODEL_RE.match(path)
        if match:
            model = match.group("model")
            res_id = int(match.group("id"))
            field = match.group("field")
            if match.group("width"):
                width = int(match.group("width"))
                height = int(match.group("height"))
            return model, res_id, field, width, height

        match = _WEB_IMAGE_ID_RE.match(path)
        if match:
            res_id = int(match.group("id"))
            if match.group("width"):
                width = int(match.group("width"))
                height = int(match.group("height"))
            return "ir.attachment", res_id, "raw", width, height

        params = parse_qs(query)
        model = params.get("model", ["ir.attachment"])[0]
        res_id = int(params.get("id", [0])[0])
        field = params.get("field", ["raw"])[0]
        if "width" in params:
            width = int(params["width"][0])
        if "height" in params:
            height = int(params["height"][0])

        if not res_id:
            msg = f"Cannot parse image URL: {path}"
            raise ValueError(msg)

        return model, res_id, field, width, height

    def _fetch_via_http(self, url: str, path: str) -> URLFetcherResponse:
        """Authenticated HTTP fallback for URLs that aren't static or asset bundles."""
        parsed = urlparse(url)
        full_url = url if parsed.hostname else f"{self._base_url}{path}"
        try:
            cookies = (
                {"session_id": self._session_cookie} if self._session_cookie else {}
            )
            resp = self._do_get(full_url, cookies)
            try:
                resp.raise_for_status()
                content_type = resp.headers.get(
                    "Content-Type", "application/octet-stream"
                )
                return self._make_response(url, resp.content, content_type)
            finally:
                resp.close()
        except Exception:
            _logger.warning("WeasyPrint URL fetch failed for %s", full_url)
            return super().fetch(url)

    @staticmethod
    def _do_get(url: str, cookies: dict[str, str]) -> requests.Response:
        """Issue a GET request, handling test-mode lock and cookie.

        During tests the main thread holds ``_registry_test_lock``.  The HTTP
        worker that serves this request needs the same lock to open a
        ``TestCursor``.  We must therefore:

        1. Set the ``test_request_key`` cookie so ``assertCanOpenTestCursor``
           accepts the request.
        2. Temporarily release the lock so the worker thread can acquire it.
        """
        current_test = modules.module.current_test
        if not current_test:
            return requests.get(url, cookies=cookies, timeout=10, verify=False)

        from odoo.tests.common import TEST_CURSOR_COOKIE_NAME, release_test_lock

        # Use the existing key if allow_requests() was called, otherwise
        # generate a temporary key from the test's canonical tag.
        key = (
            getattr(current_test, "http_request_key", "") or current_test.canonical_tag
        )
        cookies[TEST_CURSOR_COOKIE_NAME] = key
        saved_key = current_test.http_request_key
        current_test.http_request_key = key
        try:
            with release_test_lock():
                return requests.get(url, cookies=cookies, timeout=10, verify=False)
        finally:
            current_test.http_request_key = saved_key

    @staticmethod
    def _make_response(
        url: str, body: bytes, content_type: str = "application/octet-stream"
    ) -> URLFetcherResponse:
        return URLFetcherResponse(
            url, body=body, headers={"Content-Type": content_type}
        )


class IrActionsReport(models.Model):
    _name = "ir.actions.report"
    _description = "Report Action"
    _inherit = ["ir.actions.actions"]
    _table = "ir_act_report_xml"
    _order = "name, id"
    _allow_sudo_commands = False

    type = fields.Char(default="ir.actions.report")
    binding_type = fields.Selection(default="report")
    model = fields.Char(required=True, string="Model Name")
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        compute="_compute_model_id",
        search="_search_model_id",
    )

    report_type = fields.Selection(
        [
            ("qweb-html", "HTML"),
            ("qweb-pdf", "PDF"),
            ("qweb-text", "Text"),
        ],
        required=True,
        default="qweb-pdf",
        help="The type of the report that will be rendered, each one having its own"
        " rendering method. HTML means the report will be opened directly in your"
        " browser. PDF means the report will be rendered using WeasyPrint and"
        " downloaded by the user.",
    )
    report_name = fields.Char(string="Template Name", required=True)
    report_file = fields.Char(
        string="Report File",
        required=False,
        readonly=False,
        store=True,
        help="The path to the main report file (depending on Report Type) or empty if the content is in another field",
    )
    group_ids = fields.Many2many(
        "res.groups", "res_groups_report_rel", "uid", "gid", string="Groups"
    )
    multi = fields.Boolean(
        string="On Multiple Doc.",
        help="If set to true, the action will not be displayed on the right toolbar of a form view.",
    )

    paperformat_id = fields.Many2one(
        "report.paperformat", "Paper Format", index="btree_not_null"
    )
    print_report_name = fields.Char(
        "Printed Report Name",
        translate=True,
        help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the 'object' and 'time' variables.",
    )
    attachment_use = fields.Boolean(
        string="Reload from Attachment",
        help="If enabled, then the second time the user prints with same attachment name, it returns the previous report.",
    )
    attachment = fields.Char(
        string="Save as Attachment Prefix",
        help="This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.",
    )
    domain = fields.Char(
        string="Filter domain",
        help="If set, the action will only appear on records that matches the domain.",
    )

    @api.depends("model")
    def _compute_model_id(self) -> None:
        for action in self:
            action.model_id = self.env["ir.model"]._get(action.model).id

    def _search_model_id(self, operator: str, value: Any) -> Any:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        models = self.env["ir.model"]
        if isinstance(value, str):
            models = models.search(Domain("display_name", operator, value))
        elif isinstance(value, Domain):
            models = models.search(value)
        elif operator == "any!":
            models = models.sudo().search(Domain("id", operator, value))
        elif operator == "any" or isinstance(value, int):
            models = models.search(Domain("id", operator, value))
        elif operator == "in":
            models = models.search(
                Domain.OR(
                    Domain(
                        "id" if isinstance(v, int) else "display_name",
                        operator,
                        v,
                    )
                    for v in value
                    if v
                )
            )
        return Domain("model", "in", models.mapped("model"))

    def _get_readable_fields(self) -> set[str]:
        return super()._get_readable_fields() | {
            "report_name",
            "report_type",
            "target",
            # these two are not real fields of ir.actions.report but are
            # expected in the route /report/<converter>/<reportname> and must
            # not be removed by clean_action
            "context",
            "data",
            # and this one is used by the frontend later on.
            "close_on_report_download",
            "domain",
        }

    def associated_view(self) -> dict[str, Any] | bool:
        """Used in the ir.actions.report form view in order to search naively after the view(s)
        used in the rendering.
        """
        self.ensure_one()
        action_ref = self.env.ref("base.action_ui_view")
        if not action_ref or len(self.report_name.split(".")) < 2:
            return False
        action_data = action_ref.read()[0]
        action_data["domain"] = [
            ("name", "ilike", self.report_name.split(".")[1]),
            ("type", "=", "qweb"),
        ]
        return action_data

    def create_action(self) -> bool:
        """Create a contextual action for each report."""
        for report in self:
            model = self.env["ir.model"]._get(report.model)
            report.write({"binding_model_id": model.id, "binding_type": "report"})
        return True

    def unlink_action(self) -> bool:
        """Remove the contextual actions created for the reports."""
        self.check_access("write")
        self.filtered("binding_model_id").write({"binding_model_id": False})
        return True

    # --------------------------------------------------------------------------
    # Main report methods
    # --------------------------------------------------------------------------

    def retrieve_attachment(self, record: Any) -> Any | None:
        """Retrieve an attachment for a specific record.

        :param record: The record owning of the attachment.
        :return: A recordset of length <=1 or None
        """
        attachment_name = (
            safe_eval(self.attachment, {"object": record, "time": time})
            if self.attachment
            else ""
        )
        if not attachment_name:
            return None
        return self.env["ir.attachment"].search(
            [
                ("name", "=", attachment_name),
                ("res_model", "=", self.model),
                ("res_id", "=", record.id),
            ],
            limit=1,
        )

    @api.model
    @deprecated("Use _get_pdf_engine_state() instead")
    def get_wkhtmltopdf_state(self) -> str:
        """Get PDF engine state. Returns 'ok' — WeasyPrint is always available.

        Kept for backward compatibility with frontend /report/check_wkhtmltopdf route.
        """
        return "ok"

    def get_paperformat(self) -> Any:
        return self.paperformat_id or self.env.company.paperformat_id

    def get_paperformat_by_xmlid(self, xml_id: str) -> Any:
        return (
            self.env.ref(xml_id).get_paperformat()
            if xml_id
            else self.env.company.paperformat_id
        )

    def _get_layout(self) -> Any:
        return self.env.ref("web.minimal_layout", raise_if_not_found=False)

    def _get_report_url(self, layout: Any = None) -> str:
        report_url = self.env["ir.config_parameter"].sudo().get_param("report.url")
        return report_url or (layout or self._get_layout() or self).get_base_url()

    # -------------------------------------------------------------------------
    # WeasyPrint PDF engine
    # -------------------------------------------------------------------------

    # CSS page size names supported by WeasyPrint (CSS Paged Media Level 3).
    # Paper formats not in this set use explicit mm dimensions.
    _WEASYPRINT_PAGE_SIZES = {
        "a3",
        "a4",
        "a5",
        "b4",
        "b5",
        "letter",
        "legal",
        "ledger",
    }

    @api.model
    def _get_pdf_engine_state(self) -> str:
        """Check PDF engine availability.

        WeasyPrint is a pip dependency — always available.
        Kept for backward compatibility with frontend status checks.
        """
        return "ok"

    @api.model
    def _paperformat_to_css(
        self,
        paperformat_id: Any,
        landscape: bool = False,
        specific_paperformat_args: dict[str, str] | None = None,
    ) -> str:
        """Convert a report.paperformat record into CSS @page rules.

        :param paperformat_id: report.paperformat record
        :param bool landscape: force landscape orientation
        :param specific_paperformat_args: data-report-* overrides from HTML
        :type specific_paperformat_args: dict[str, str] | None
        :return: CSS string with @page rules and running element declarations
        """
        args = specific_paperformat_args or {}
        orientation = (
            "landscape"
            if landscape
            else (
                "landscape" if paperformat_id.orientation == "Landscape" else "portrait"
            )
        )

        # Page size
        if paperformat_id.format and paperformat_id.format != "custom":
            fmt = paperformat_id.format.lower()
            if fmt in self._WEASYPRINT_PAGE_SIZES:
                size_css = f"{fmt} {orientation}"
            else:
                # Use explicit dimensions from PAPER_SIZES
                from odoo.addons.base.models.report_paperformat import (
                    PAPER_SIZES,
                )

                ps = next(
                    (p for p in PAPER_SIZES if p["key"] == paperformat_id.format),
                    None,
                )
                if ps:
                    size_css = f"{ps['width']}mm {ps['height']}mm"
                    if orientation == "landscape":
                        size_css = f"{ps['height']}mm {ps['width']}mm"
                else:
                    size_css = f"A4 {orientation}"
        elif paperformat_id.page_width and paperformat_id.page_height:
            w, h = paperformat_id.page_width, paperformat_id.page_height
            if orientation == "landscape":
                w, h = h, w
            size_css = f"{w}mm {h}mm"
        else:
            size_css = f"A4 {orientation}"

        # Margins (data-report-* overrides take priority)
        margin_top = float(
            args.get("data-report-margin-top", paperformat_id.margin_top)
        )
        margin_bottom = float(
            args.get("data-report-margin-bottom", paperformat_id.margin_bottom)
        )
        margin_left = float(paperformat_id.margin_left)
        margin_right = float(paperformat_id.margin_right)

        # Header line
        header_border = (
            "border-bottom: 1px solid black;" if paperformat_id.header_line else ""
        )

        # Running elements (.header/.footer) and page counters (span.page/topage)
        # are declared statically in report_paged_media.css. Only emit per-report
        # @page rules and the optional header border here.
        return (
            f"@page {{\n"
            f"  size: {size_css};\n"
            f"  margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm;\n"
            f"  @top-left {{ content: element(page-header); margin: 0; padding: 0; width: 100%; }}\n"
            f"  @bottom-left {{ content: element(page-footer); margin: 0; padding: 0; width: 100%; }}\n"
            f"}}\n" + (f".header {{ {header_border} }}\n" if header_border else "")
        )

    def _build_url_fetcher(self) -> OdooURLFetcher:
        """Build a URL fetcher for WeasyPrint that resolves Odoo resources.

        Returns an :class:`OdooURLFetcher` (v68+ URLFetcher subclass) that
        resolves asset bundles, static files, and HTTP fallbacks.  Use as a
        context manager to ensure the temporary session is cleaned up::

            with self._build_url_fetcher() as fetcher:
                weasyprint.HTML(..., url_fetcher=fetcher).write_pdf()

        :return: OdooURLFetcher instance (context manager)
        """
        return OdooURLFetcher(self.env)

    def _prepare_weasyprint_html(
        self, html: str, report_model: str | bool = False
    ) -> tuple[list[str], list[int | None], dict[str, str]]:
        """Prepare HTML documents for WeasyPrint rendering.

        Unlike _prepare_html() which extracts headers/footers into separate files
        for wkhtmltopdf, this method keeps headers/footers in the document and
        relies on CSS running elements to place them in page margins.

        :param str html: rendered QWeb HTML containing all records
        :param report_model: model name for record identification
        :type report_model: str | bool
        :return: tuple (bodies, res_ids, specific_paperformat_args)
            - bodies: list of complete HTML strings (one per record)
            - res_ids: list of record IDs (or None) matching bodies
            - specific_paperformat_args: dict of data-report-* overrides
        """
        layout = self._get_layout()
        if not layout:
            return [], [], {}

        base_url = self._get_report_url(layout=layout)
        root = lxml.html.fromstring(html, parser=lxml.html.HTMLParser(encoding="utf-8"))

        # Extract data-report-* attributes from root HTML element
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith("data-report-"):
                specific_paperformat_args[attribute[0]] = attribute[1]

        headers = _xpath_header(root)
        footers = _xpath_footer(root)
        articles = _xpath_article(root)

        bodies = []
        res_ids = []

        if not articles:
            # No article tags — render the entire body as one document
            main_nodes = _xpath_main(root)
            if not main_nodes:
                raise ValueError("Report HTML is missing a <main> element")
            body_parent = main_nodes[0]
            body_html = "".join(
                lxml.html.tostring(c, encoding="unicode") for c in body_parent
            )
            body = self.env["ir.qweb"]._render(
                layout.id,
                {
                    "subst": False,
                    "body": Markup(body_html),
                    "base_url": base_url,
                    "report_xml_id": self.xml_id,
                },
                raise_if_not_found=False,
            )
            bodies.append(body)
            res_ids.append(None)
            return bodies, res_ids, specific_paperformat_args

        for i, article_node in enumerate(articles):
            # Pair each article with its header and footer by index
            header_node = headers[i] if i < len(headers) else None
            footer_node = footers[i] if i < len(footers) else None

            # Build combined body: header + footer + article content.
            # Running elements (position: running()) must appear BEFORE the
            # content they should display on — WeasyPrint captures them at the
            # point they appear in the document flow.
            parts = []
            if header_node is not None:
                parts.append(lxml.html.tostring(header_node, encoding="unicode"))
            if footer_node is not None:
                parts.append(lxml.html.tostring(footer_node, encoding="unicode"))
            parts.append(lxml.html.tostring(article_node, encoding="unicode"))

            combined_html = "".join(parts)

            # Set context language from article's data-oe-lang
            IrQweb = self.env["ir.qweb"]
            if article_node.get("data-oe-lang"):
                IrQweb = IrQweb.with_context(lang=article_node.get("data-oe-lang"))

            # Render through minimal_layout to get complete HTML with CSS assets
            body = IrQweb._render(
                layout.id,
                {
                    "subst": False,
                    "body": Markup(combined_html),
                    "base_url": base_url,
                    "report_xml_id": self.xml_id,
                    "debug": self.env.context.get("debug"),
                },
                raise_if_not_found=False,
            )
            bodies.append(body)

            if article_node.get("data-oe-model") == report_model:
                res_ids.append(int(article_node.get("data-oe-id", 0)))
            else:
                res_ids.append(None)

        return bodies, res_ids, specific_paperformat_args

    @api.model
    def _render_html_to_pdf(
        self,
        bodies: list[str],
        report_ref: int | str | Any = False,
        landscape: bool = False,
        specific_paperformat_args: dict[str, str] | None = None,
        *,
        _split: bool = False,
    ) -> bytes | list[bytes]:
        """Render HTML bodies to PDF using WeasyPrint.

        All bodies share a single WeasyPrint session: one URL fetcher, one
        fontconfig initialization, and one resource cache.  After the first
        body warms the cache with CSS bundles and images, subsequent bodies
        hit the cache directly — no HTTP fetches.

        :param bodies: list of complete HTML strings
        :type bodies: list[str]
        :param report_ref: report reference for paperformat resolution
        :param bool landscape: force landscape orientation
        :param specific_paperformat_args: data-report-* overrides
        :type specific_paperformat_args: dict[str, str] | None
        :param bool _split: if True, return ``list[bytes]`` — one PDF per
            body — instead of a single merged PDF.
        :return: PDF content as bytes, or list[bytes] when ``_split=True``
        """
        paperformat_id = (
            self._get_report(report_ref).get_paperformat()
            if report_ref
            else self.get_paperformat()
        )

        # Build @page CSS from paperformat
        page_css = self._paperformat_to_css(
            paperformat_id,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
        )

        with self._build_url_fetcher() as fetcher:
            # Pre-parse external CSS stylesheets from the first body so that
            # subsequent bodies skip fetching and parsing the same ~300KB
            # Bootstrap CSS.  weasyprint.CSS() parses once; write_pdf() reuses
            # the parsed rules via the `stylesheets` parameter.
            pre_parsed_css = []
            parsed_css_urls = set()
            if bodies:
                first_html = self._inject_page_css(bodies[0], page_css)
                css_urls = _RE_CSS_LINK.findall(first_html)
                for css_url in css_urls:
                    try:
                        pre_parsed_css.append(
                            weasyprint.CSS(url=css_url, url_fetcher=fetcher)
                        )
                        parsed_css_urls.add(css_url)
                    except Exception:
                        _logger.warning("Failed to pre-parse CSS: %s", css_url)

            pdf_results = []

            for body in bodies:
                # Inject @page CSS into the HTML <head>
                html_with_css = self._inject_page_css(body, page_css)

                # Strip only the <link> tags whose CSS was successfully
                # pre-parsed — leave any failed ones so WeasyPrint can
                # still attempt to fetch them inline.
                if parsed_css_urls:
                    html_with_css = _RE_CSS_LINK.sub(
                        lambda m: ("" if m.group(1) in parsed_css_urls else m.group(0)),
                        html_with_css,
                    )

                try:
                    pdf_bytes = weasyprint.HTML(
                        string=html_with_css,
                        url_fetcher=fetcher,
                    ).write_pdf(
                        font_config=_weasy_font_config,
                        counter_style=CounterStyle(),
                        stylesheets=pre_parsed_css or None,
                        presentational_hints=True,
                        optimize_images=True,
                        cache=_weasy_image_cache,
                    )
                    pdf_results.append(pdf_bytes)
                except Exception as e:
                    _logger.error("WeasyPrint PDF rendering failed: %s", e)
                    raise UserError(
                        _(
                            "PDF rendering failed. Please check the report template.\n\nDetails: %s",
                            str(e),
                        )
                    )

            if not pdf_results:
                raise UserError(_("No content to render as PDF."))

            if _split:
                return pdf_results

            # Merge multiple PDFs into one
            if len(pdf_results) == 1:
                return pdf_results[0]

            writer = PdfFileWriter()
            for pdf_bytes in pdf_results:
                try:
                    reader = PdfFileReader(io.BytesIO(pdf_bytes))
                    writer.append_pages_from_reader(reader)
                except (PdfReadError, TypeError, ValueError) as e:
                    _logger.warning("Failed to merge PDF stream: %s", e)
            result = io.BytesIO()
            writer.write(result)
            return result.getvalue()

    @staticmethod
    def _inject_page_css(html: str, css: str) -> str:
        """Inject CSS @page rules into an HTML document's <head>.

        :param str html: HTML string (may be Markup)
        :param str css: CSS string to inject
        :return: modified HTML string (plain str, not Markup)
        """
        # Convert from Markup to plain str to avoid auto-escaping
        # (Markup.replace() would escape <style> tags to &lt;style&gt;)
        html_str = str(html)
        style_tag = f'<style type="text/css">{css}</style>'
        if "</head>" in html_str:
            return html_str.replace("</head>", f"{style_tag}</head>", 1)
        return f"{style_tag}{html_str}"

    def _render_html_to_image(
        self,
        bodies: list[str],
        width: int,
        height: int,
        image_format: str = "jpg",
    ) -> list[bytes | None]:
        """Render HTML bodies to images using WeasyPrint.

        Replaces _run_wkhtmltoimage(). Uses WeasyPrint for PNG rendering,
        then PIL for format conversion and resizing.

        :param bodies: list of HTML strings
        :type bodies: list[str]
        :param int width: target width in pixels
        :param int height: target height in pixels
        :param str image_format: 'jpg' or 'png'
        :return: list of image bytes (or None on error)
        """
        if modules.module.current_test:
            return [None] * len(bodies)

        output_images = []
        for body in bodies:
            try:
                png_bytes = weasyprint.HTML(string=body).write_png()
                img = Image.open(io.BytesIO(png_bytes))
                img = img.resize((width, height), Image.Resampling.LANCZOS)

                buf = io.BytesIO()
                if image_format == "png":
                    img.save(buf, format="PNG")
                else:
                    img.convert("RGB").save(buf, format="JPEG")
                output_images.append(buf.getvalue())
            except Exception as e:
                _logger.warning("WeasyPrint image rendering failed: %s", e)
                output_images.append(None)
        return output_images

    def _prepare_html(
        self, html: str, report_model: str | bool = False
    ) -> dict | tuple[list[str], list[int | None], str, str, dict[str, str]]:
        """Split HTML into separate bodies, headers, and footers.

        Legacy method kept for callers that need HTML splitting (e.g. account's
        _get_splitted_report). For PDF rendering, use _prepare_weasyprint_html instead.
        """

        # Return empty dictionary if 'web.minimal_layout' not found.
        layout = self._get_layout()
        if not layout:
            return {}
        base_url = self._get_report_url(layout=layout)

        root = lxml.html.fromstring(html, parser=lxml.html.HTMLParser(encoding="utf-8"))

        header_node = etree.Element("div", id="minimal_layout_report_headers")
        footer_node = etree.Element("div", id="minimal_layout_report_footers")
        bodies = []
        res_ids = []

        main_nodes = _xpath_main(root)
        if not main_nodes:
            raise ValueError("Report HTML is missing a <main> element")
        body_parent = main_nodes[0]
        # Retrieve headers
        for node in _xpath_header(root):
            node.getparent().remove(node)
            header_node.append(node)

        # Retrieve footers
        for node in _xpath_footer(root):
            node.getparent().remove(node)
            footer_node.append(node)

        # Retrieve bodies
        for node in _xpath_article(root):
            # set context language to body language
            IrQweb = self.env["ir.qweb"]
            if node.get("data-oe-lang"):
                IrQweb = IrQweb.with_context(lang=node.get("data-oe-lang"))
            body = IrQweb._render(
                layout.id,
                {
                    "subst": False,
                    "body": Markup(lxml.html.tostring(node, encoding="unicode")),
                    "base_url": base_url,
                    "report_xml_id": self.xml_id,
                    "debug": self.env.context.get("debug"),
                },
                raise_if_not_found=False,
            )
            bodies.append(body)
            if node.get("data-oe-model") == report_model:
                res_ids.append(int(node.get("data-oe-id", 0)))
            else:
                res_ids.append(None)

        if not bodies:
            body = "".join(
                lxml.html.tostring(c, encoding="unicode") for c in body_parent
            )
            bodies.append(body)

        # Get paperformat arguments set in the root html tag. They are prioritized over
        # paperformat-record arguments.
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith("data-report-"):
                specific_paperformat_args[attribute[0]] = attribute[1]

        header = self.env["ir.qweb"]._render(
            layout.id,
            {
                "subst": True,
                "body": Markup(lxml.html.tostring(header_node, encoding="unicode")),
                "base_url": base_url,
                "report_xml_id": self.xml_id,
                "debug": self.env.context.get("debug"),
            },
        )
        footer = self.env["ir.qweb"]._render(
            layout.id,
            {
                "subst": True,
                "body": Markup(lxml.html.tostring(footer_node, encoding="unicode")),
                "base_url": base_url,
                "report_xml_id": self.xml_id,
                "debug": self.env.context.get("debug"),
            },
        )

        return bodies, res_ids, header, footer, specific_paperformat_args

    @deprecated("Use _render_html_to_image() instead")
    def _run_wkhtmltoimage(
        self,
        bodies: list[str],
        width: int,
        height: int,
        image_format: str = "jpg",
    ) -> list[bytes | None]:
        """Backward-compat shim — delegates to _render_html_to_image (WeasyPrint)."""
        return self._render_html_to_image(
            bodies, width, height, image_format=image_format
        )

    @api.model
    @deprecated("Use _render_html_to_pdf() instead")
    def _run_wkhtmltopdf(
        self,
        bodies: list[str],
        report_ref: int | str | Any = False,
        header: str | None = None,
        footer: str | None = None,
        landscape: bool = False,
        specific_paperformat_args: dict[str, str] | None = None,
        set_viewport_size: bool = False,
        *,
        _split: bool = False,
    ) -> bytes | list[bytes]:
        """Backward-compat shim — delegates to _render_html_to_pdf (WeasyPrint).

        Accepts the old wkhtmltopdf signature (header=, footer=, set_viewport_size=)
        for callers in stock, account, and enterprise modules.
        If standalone header/footer HTML is passed, injects them as CSS running
        elements into each body before rendering.

        :param bodies: The html bodies of the report, one per page.
        :type bodies: list[str]
        :param report_ref: report reference for paperformat resolution.
        :param header: standalone header HTML (injected as running element).
        :type header: str | None
        :param footer: standalone footer HTML (injected as running element).
        :type footer: str | None
        :param landscape: force landscape orientation.
        :param specific_paperformat_args: dict of data-report-* overrides.
        :param set_viewport_size: ignored (was wkhtmltopdf-specific).
        :param bool _split: if True, return ``list[bytes]`` (one PDF per body).
        :return: PDF content as bytes, or list[bytes] when ``_split=True``
        """
        if header or footer:
            bodies = [
                self._inject_header_footer_html(body, header=header, footer=footer)
                for body in bodies
            ]
        return self._render_html_to_pdf(
            bodies,
            report_ref=report_ref,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            _split=_split,
        )

    @staticmethod
    def _inject_header_footer_html(
        body: str, header: str | None = None, footer: str | None = None
    ) -> str:
        """Inject standalone header/footer HTML into a body as CSS running elements.

        Used by the _run_wkhtmltopdf shim when callers pass separate header/footer.
        Extracts the content from the header/footer HTML and wraps it in
        <div class="header">/<div class="footer"> inside the body.

        :param str body: complete HTML document
        :param header: standalone header HTML document (or None)
        :type header: str | None
        :param footer: standalone footer HTML document (or None)
        :type footer: str | None
        :return: modified HTML body with header/footer injected
        """
        inject = ""
        if header:
            tree = lxml.html.fromstring(header)
            header_body = tree.xpath("//body")
            if header_body:
                content = "".join(
                    lxml.html.tostring(c, encoding="unicode") for c in header_body[0]
                )
                inject += f'<div class="header">{content}</div>'
        if footer:
            tree = lxml.html.fromstring(footer)
            footer_body = tree.xpath("//body")
            if footer_body:
                content = "".join(
                    lxml.html.tostring(c, encoding="unicode") for c in footer_body[0]
                )
                inject += f'<div class="footer">{content}</div>'
        if inject and "<body" in body:
            # Insert after opening <body...> tag
            idx = body.find(">", body.find("<body")) + 1
            return body[:idx] + inject + body[idx:]
        return body

    @api.model
    def _get_report_from_name(self, report_name: str) -> Self:
        """Get the first record of ir.actions.report having the ``report_name`` as value for
        the field report_name.
        """
        report_obj = self.env["ir.actions.report"]
        conditions = [("report_name", "=", report_name)]
        context = self.env["res.users"].context_get()
        return report_obj.with_context(context).sudo().search(conditions, limit=1)

    @api.model
    def _get_report(self, report_ref: int | str | Any) -> Self:
        """Get the report (with sudo) from a reference

        :param report_ref: can be one of

            - ir.actions.report id
            - ir.actions.report record
            - ir.model.data reference to ir.actions.report
            - ir.actions.report report_name
        """
        ReportSudo = self.env["ir.actions.report"].sudo()
        if isinstance(report_ref, int):
            return ReportSudo.browse(report_ref)
        if isinstance(report_ref, models.Model):
            if report_ref._name != self._name:
                raise ValueError(
                    "Expected report of type %s, got %s"
                    % (self._name, report_ref._name)
                )
            return report_ref.sudo()
        report = ReportSudo.search([("report_name", "=", report_ref)], limit=1)
        if report:
            return report
        report = self.env.ref(report_ref, raise_if_not_found=False)
        if report:
            if report._name != "ir.actions.report":
                raise ValueError(
                    f"Fetching report {report_ref!r}: type {report._name}, expected ir.actions.report"
                )
            return report.sudo()
        raise ValueError(f"Fetching report {report_ref!r}: report not found")

    @api.model
    def barcode(self, barcode_type: str, value: str, **kwargs: Any) -> bytes:
        defaults = {
            "width": (600, int),
            "height": (100, int),
            "humanreadable": (False, lambda x: bool(int(x))),
            "quiet": (True, lambda x: bool(int(x))),
            "mask": (None, lambda x: x),
            "barBorder": (4, int),
            # The QR code can have different layouts depending on the Error Correction Level
            # See: https://en.wikipedia.org/wiki/QR_code#Error_correction
            # Level 'L' - up to 7% damage   (default)
            # Level 'M' - up to 15% damage  (i.e. required by l10n_ch QR bill)
            # Level 'Q' - up to 25% damage
            # Level 'H' - up to 30% damage
            "barLevel": (
                "L",
                lambda x: (x in ("L", "M", "Q", "H") and x) or "L",
            ),
        }
        kwargs = {
            k: validator(kwargs.get(k, v)) for k, (v, validator) in defaults.items()
        }
        kwargs["humanReadable"] = kwargs.pop("humanreadable")
        if kwargs["humanReadable"]:
            kwargs["fontName"] = get_barcode_font()

        if (
            kwargs["width"] * kwargs["height"] > 1200000
            or max(kwargs["width"], kwargs["height"]) > 10000
        ):
            msg = "Barcode too large"
            raise ValueError(msg)

        if barcode_type == "UPCA" and len(value) in (11, 12, 13):
            barcode_type = "EAN13"
            if len(value) in (11, 12):
                value = f"0{value}"
        elif barcode_type == "auto":
            symbology_guess = {8: "EAN8", 13: "EAN13"}
            barcode_type = symbology_guess.get(len(value), "Code128")
        elif barcode_type == "QR":
            # for `QR` type, `quiet` is not supported. And is simply ignored.
            # But we can use `barBorder` to get a similar behaviour.
            # quiet=True & barBorder=4 by default cf above, remove border only if quiet=False
            if not kwargs["quiet"]:
                kwargs["barBorder"] = 0

        if barcode_type in ("EAN8", "EAN13") and not check_barcode_encoding(
            value, barcode_type
        ):
            # If the barcode does not respect the encoding specifications, convert its type into Code128.
            # Otherwise, the report-lab method may return a barcode different from its value. For instance,
            # if the barcode type is EAN-8 and the value 11111111, the report-lab method will take the first
            # seven digits and will compute the check digit, which gives: 11111115 -> the barcode does not
            # match the expected value.
            barcode_type = "Code128"

        try:
            barcode = createBarcodeDrawing(
                barcode_type, value=value, format="png", **kwargs
            )

            # If a mask is asked and it is available, call its function to
            # post-process the generated QR-code image
            if kwargs["mask"]:
                available_masks = self.get_available_barcode_masks()
                mask_to_apply = available_masks.get(kwargs["mask"])
                if mask_to_apply:
                    mask_to_apply(kwargs["width"], kwargs["height"], barcode)

            return barcode.asString("png")
        except ValueError, AttributeError:
            if barcode_type == "Code128":
                msg = "Cannot convert into barcode."
                raise ValueError(msg)
            if barcode_type == "QR":
                msg = "Cannot convert into QR code."
                raise ValueError(msg)
            return self.barcode("Code128", value, **kwargs)

    @api.model
    def get_available_barcode_masks(self) -> dict[str, Callable]:
        """Hook for extension.

        This function returns the available QR-code masks, in the form of a
        list of (code, mask_function) elements, where code is a string identifying
        the mask uniquely, and mask_function is a function returning a reportlab
        Drawing object with the result of the mask, and taking as parameters:

            - width of the QR-code, in pixels
            - height of the QR-code, in pixels
            - reportlab Drawing object containing the barcode to apply the mask on
        """
        return {}

    def _render_template(
        self, template: str, values: dict[str, Any] | None = None
    ) -> bytes:
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.
        :param values: additional methods/variables used in the rendering
        :returns: html representation of the template
        :rtype: bytes
        """
        if values is None:
            values = {}

        # Browse the user instead of using the sudo self.env.user
        user = self.env["res.users"].browse(self.env.uid)
        view_obj = self.env["ir.ui.view"].with_context(inherit_branding=False)
        values.update(
            time=time,
            context_timestamp=lambda t: fields.Datetime.context_timestamp(
                self.with_context(tz=user.tz), t
            ),
            user=user,
            res_company=self.env.company,
            web_base_url=self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", default=""),
        )
        return view_obj._render_template(template, values).encode()

    def _handle_merge_pdfs_error(
        self,
        error: Exception | None = None,
        error_stream: io.BytesIO | None = None,
    ) -> None:
        raise UserError(_("Odoo is unable to merge the generated PDFs."))

    @api.model
    def _merge_pdfs(
        self,
        streams: list[io.BytesIO],
        handle_error: Callable = _handle_merge_pdfs_error,
    ) -> io.BytesIO:
        writer = PdfFileWriter()
        for stream in streams:
            try:
                reader = PdfFileReader(stream)
                writer.append_pages_from_reader(reader)
            except (
                PdfReadError,
                TypeError,
                NotImplementedError,
                ValueError,
            ) as e:
                handle_error(error=e, error_stream=stream)
        result_stream = io.BytesIO()
        try:
            writer.write(result_stream)
        except PdfReadError:
            raise UserError(_("Odoo is unable to merge the generated PDFs."))
        return result_stream

    def _render_qweb_pdf_prepare_streams(
        self,
        report_ref: int | str | Any,
        data: dict[str, Any],
        res_ids: list[int] | None = None,
    ) -> dict[int | bool, dict[str, Any]]:
        if not data:
            data = {}
        data.setdefault("report_type", "pdf")

        # access the report details with sudo() but evaluation context as current user
        report_sudo = self._get_report(report_ref)
        has_duplicated_ids = res_ids and len(res_ids) != len(set(res_ids))

        collected_streams = {}

        # Fetch the existing attachments from the database for later use.
        # Reload the stream from the attachment in case of 'attachment_use'.
        if res_ids:
            records = self.env[report_sudo.model].browse(res_ids)
            for record in records:
                res_id = record.id
                if res_id in collected_streams:
                    continue

                stream = None
                attachment = None
                if (
                    not has_duplicated_ids
                    and report_sudo.attachment
                    and not self.env.context.get("report_pdf_no_attachment")
                ):
                    attachment = report_sudo.retrieve_attachment(record)

                    # Extract the stream from the attachment.
                    if attachment and report_sudo.attachment_use:
                        stream = io.BytesIO(attachment.raw)

                        # Ensure the stream can be saved in Image.
                        if attachment.mimetype.startswith("image"):
                            img = Image.open(stream)
                            new_stream = io.BytesIO()
                            img.convert("RGB").save(new_stream, format="pdf")
                            stream.close()
                            stream = new_stream

                collected_streams[res_id] = {
                    "stream": stream,
                    "attachment": attachment,
                }

        # Render PDFs for records missing a cached attachment stream.
        res_ids_wo_stream = [
            res_id
            for res_id, stream_data in collected_streams.items()
            if not stream_data["stream"]
        ]
        all_res_ids_wo_stream = res_ids if has_duplicated_ids else res_ids_wo_stream
        is_pdf_needed = not res_ids or res_ids_wo_stream

        if is_pdf_needed:
            # Force debug=False so asset bundles are single minified files,
            # not split into individual source files.
            data.setdefault("debug", False)
            additional_context = {"debug": False}

            html = self.with_context(**additional_context)._render_qweb_html(
                report_ref,
                all_res_ids_wo_stream,
                data=data,
            )[0]

            (
                bodies,
                html_ids,
                specific_paperformat_args,
            ) = report_sudo.with_context(**additional_context)._prepare_weasyprint_html(
                html,
                report_model=report_sudo.model,
            )

            if (
                not has_duplicated_ids
                and report_sudo.attachment
                and set(res_ids_wo_stream) != set(html_ids)
            ):
                raise UserError(
                    _(
                        "Report template \u201c%s\u201d has an issue, please contact your administrator. \n\n"
                        "Cannot separate file to save as attachment because the report\u2019s template does not contain the"
                        " attributes 'data-oe-model' and 'data-oe-id' as part of the div with 'article' classname.",
                        report_sudo.name,
                    )
                )

            # Per-record rendering: each body becomes a separate PDF.
            landscape = self.env.context.get("landscape")

            # Determine if we can split per-record
            html_ids_valid = [x for x in html_ids if x is not None]
            can_split = (
                not has_duplicated_ids
                and res_ids
                and html_ids_valid
                and set(html_ids_valid) == set(res_ids_wo_stream)
            )

            if can_split:
                # Batch all bodies into a single WeasyPrint session so they
                # share one FontConfiguration, one URL fetcher session, and
                # one resource cache.  The first body warms the cache (CSS
                # bundles, images); subsequent bodies hit it directly.
                render_bodies = []
                render_res_ids = []
                for body, res_id in zip(bodies, html_ids, strict=False):
                    if res_id is not None and res_id in res_ids_wo_stream:
                        render_bodies.append(body)
                        render_res_ids.append(res_id)
                if render_bodies:
                    pdf_contents = self._render_html_to_pdf(
                        render_bodies,
                        report_ref=report_ref,
                        landscape=landscape,
                        specific_paperformat_args=specific_paperformat_args,
                        _split=True,
                    )
                    for pdf_content, res_id in zip(
                        pdf_contents, render_res_ids, strict=False
                    ):
                        collected_streams[res_id]["stream"] = io.BytesIO(pdf_content)
            else:
                # Can't split per-record (no data-oe-id, duplicates, or no res_ids).
                # Render all bodies into a single merged PDF.
                pdf_content = self._render_html_to_pdf(
                    bodies,
                    report_ref=report_ref,
                    landscape=landscape,
                    specific_paperformat_args=specific_paperformat_args,
                )
                pdf_content_stream = io.BytesIO(pdf_content)

                if not res_ids or has_duplicated_ids:
                    return {
                        False: {
                            "stream": pdf_content_stream,
                            "attachment": None,
                        }
                    }

                # Single record without split: assign directly
                if len(res_ids_wo_stream) == 1:
                    collected_streams[res_ids_wo_stream[0]][
                        "stream"
                    ] = pdf_content_stream
                else:
                    # Multiple records but can't split — return as unsplit
                    collected_streams[False] = {
                        "stream": pdf_content_stream,
                        "attachment": None,
                    }

        return collected_streams

    def _prepare_pdf_report_attachment_vals_list(
        self, report: Self, streams: dict[int | bool, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Hook to prepare attachment values needed for attachments creation
        during the pdf report generation.

        :param report: The report (with sudo) from a reference report_ref.
        :param streams: Dict of streams for each report containing the pdf content and existing attachments.
        :return: attachment values list needed for attachments creation.
        """
        attachment_vals_list = []
        for res_id, stream_data in streams.items():
            # An attachment already exists.
            if stream_data["attachment"]:
                continue

            # if res_id is false
            # we are unable to fetch the record, it won't be saved as we can't split the documents unambiguously
            if not res_id or not stream_data["stream"]:
                _logger.warning(
                    "These documents were not saved as an attachment because the template of %s doesn't "
                    "have any headers seperating different instances of it. If you want it saved,"
                    "please print the documents separately",
                    report.report_name,
                )
                continue
            record = self.env[report.model].browse(res_id)
            attachment_name = safe_eval(
                report.attachment, {"object": record, "time": time}
            )

            # Unable to compute a name for the attachment.
            if not attachment_name:
                continue

            attachment_vals_list.append(
                {
                    "name": attachment_name,
                    "raw": stream_data["stream"].getvalue(),
                    "res_model": report.model,
                    "res_id": record.id,
                    "type": "binary",
                }
            )
        return attachment_vals_list

    def _pre_render_qweb_pdf(
        self,
        report_ref: int | str | Any,
        res_ids: list[int] | None = None,
        data: dict[str, Any] | None = None,
    ) -> tuple[Any, str]:
        if not data:
            data = {}
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        data.setdefault("report_type", "pdf")
        # In test environment, fallback to render_html unless force_report_rendering is set.
        if (
            modules.module.current_test or tools.config["test_enable"]
        ) and not self.env.context.get("force_report_rendering"):
            return self._render_qweb_html(report_ref, res_ids, data=data)

        self = self.with_context(webp_as_jpg=True)
        return (
            self._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids),
            "pdf",
        )

    def _render_qweb_pdf(
        self,
        report_ref: int | str | Any,
        res_ids: list[int] | None = None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        if not data:
            data = {}
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        data.setdefault("report_type", "pdf")

        collected_streams, report_type = self._pre_render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )
        if report_type != "pdf":
            return collected_streams, report_type

        has_duplicated_ids = res_ids and len(res_ids) != len(set(res_ids))

        # access the report details with sudo() but keep evaluation context as current user
        report_sudo = self._get_report(report_ref)

        # Generate the ir.attachment if needed.
        if (
            not has_duplicated_ids
            and report_sudo.attachment
            and not self.env.context.get("report_pdf_no_attachment")
        ):
            attachment_vals_list = self._prepare_pdf_report_attachment_vals_list(
                report_sudo, collected_streams
            )
            if attachment_vals_list:
                attachment_names = ", ".join(x["name"] for x in attachment_vals_list)
                try:
                    self.env["ir.attachment"].create(attachment_vals_list)
                except AccessError:
                    _logger.info(
                        "Cannot save PDF report %r attachments for user %r",
                        attachment_names,
                        self.env.user.display_name,
                    )
                else:
                    _logger.info(
                        "The PDF documents %r are now saved in the database",
                        attachment_names,
                    )

        def custom_handle_merge_pdfs_error(
            error: Exception, error_stream: io.BytesIO
        ) -> None:
            error_record_ids.append(stream_to_ids[error_stream])

        stream_to_ids = {
            v["stream"]: k for k, v in collected_streams.items() if v["stream"]
        }
        # Merge all streams together for a single record.
        streams_to_merge = list(stream_to_ids.keys())
        error_record_ids = []

        if len(streams_to_merge) == 1:
            pdf_content = streams_to_merge[0].getvalue()
        else:
            with self._merge_pdfs(
                streams_to_merge, custom_handle_merge_pdfs_error
            ) as pdf_merged_stream:
                pdf_content = pdf_merged_stream.getvalue()

        if error_record_ids:
            action = {
                "type": "ir.actions.act_window",
                "name": _("Problematic record(s)"),
                "res_model": report_sudo.model,
                "domain": [("id", "in", error_record_ids)],
                "views": [(False, "list"), (False, "form")],
            }
            num_errors = len(error_record_ids)
            if num_errors == 1:
                action.update(
                    {
                        "views": [(False, "form")],
                        "res_id": error_record_ids[0],
                    }
                )
            raise RedirectWarning(
                message=_(
                    "Odoo is unable to merge the generated PDFs because of %(num_errors)s corrupted file(s)",
                    num_errors=num_errors,
                ),
                action=action,
                button_text=_("View Problematic Record(s)"),
            )

        for stream in streams_to_merge:
            stream.close()

        if res_ids:
            _logger.info(
                "The PDF report has been generated for model: %s, records %s.",
                report_sudo.model,
                res_ids,
            )

        return pdf_content, "pdf"

    @api.model
    def _render_qweb_text(
        self,
        report_ref: int | str | Any,
        docids: list[int] | None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        if not data:
            data = {}
        data.setdefault("report_type", "text")
        report = self._get_report(report_ref)
        data = self._get_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), "text"

    @api.model
    def _render_qweb_html(
        self,
        report_ref: int | str | Any,
        docids: list[int] | None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        if not data:
            data = {}
        data.setdefault("report_type", "html")
        report = self._get_report(report_ref)
        data = self._get_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), "html"

    def _get_rendering_context_model(self, report: Self) -> Any | None:
        report_model_name = f"report.{report.report_name}"
        return self.env.get(report_model_name)

    def _get_rendering_context(
        self, report: Self, docids: list[int] | None, data: dict[str, Any]
    ) -> dict[str, Any]:
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model = self._get_rendering_context_model(report)

        data = (data and dict(data)) or {}

        if report_model is not None:
            data.update(report_model._get_report_values(docids, data=data))
        else:
            docs = self.env[report.model].browse(docids)
            data.update(
                {
                    "doc_ids": docids,
                    "doc_model": report.model,
                    "docs": docs,
                }
            )
        data["is_html_empty"] = is_html_empty
        return data

    @api.model
    def _render(
        self,
        report_ref: int | str | Any,
        res_ids: list[int] | None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str] | None:
        report = self._get_report(report_ref)
        report_type = report.report_type.lower().replace("-", "_")
        render_func = getattr(self, "_render_" + report_type, None)
        if not render_func:
            return None
        return render_func(report_ref, res_ids, data=data)

    def report_action(
        self,
        docids: Any,
        data: dict[str, Any] | None = None,
        config: bool = True,
    ) -> dict[str, Any]:
        """Return an action of type ir.actions.report.

        :param docids: id/ids/browse record of the records to print (if not used, pass an empty list)
        :param data:
        :param bool config:
        :rtype: dict[str, Any]
        """
        context = self.env.context
        if docids:
            if isinstance(docids, models.Model):
                active_ids = docids.ids
            elif isinstance(docids, int):
                active_ids = [docids]
            elif isinstance(docids, list):
                active_ids = docids
            context = dict(self.env.context, active_ids=active_ids)

        report_action = {
            "context": context,
            "data": data,
            "type": "ir.actions.report",
            "report_name": self.report_name,
            "report_type": self.report_type,
            "report_file": self.report_file,
            "name": self.name,
        }

        discard_logo_check = self.env.context.get("discard_logo_check")
        if (
            self.env.is_admin()
            and not self.env.company.external_report_layout_id
            and config
            and not discard_logo_check
        ):
            return self._action_configure_external_report_layout(report_action)

        return report_action

    def _action_configure_external_report_layout(
        self,
        report_action: dict[str, Any],
        xml_id: str = "web.action_base_document_layout_configurator",
    ) -> dict[str, Any]:
        action = self.env["ir.actions.actions"]._for_xml_id(xml_id)
        py_ctx = json_loads(action.get("context", {}))
        report_action["close_on_report_download"] = True
        py_ctx["report_action"] = report_action
        action["context"] = py_ctx
        return action

    def get_valid_action_reports(self, model: str, record_ids: list[int]) -> list[int]:
        """Return the list of ids of actions for which the domain is
        satisfied by at least one record in record_ids.
        :param model: the model of the records to validate
        :param record_ids: list of ids of records to validate
        """
        records = self.env[model].browse(record_ids)
        actions_with_domain = self.filtered("domain")
        valid_action_report_ids = (
            self - actions_with_domain
        ).ids  # actions without domain are always valid
        for action in actions_with_domain:
            if records.filtered_domain(literal_eval(action.domain)):
                valid_action_report_ids.append(action.id)
        return valid_action_report_ids

    @api.model
    def _prepare_local_attachments(self, attachments: Any) -> Any:
        for attachment in attachments:
            if attachment._is_remote_source():
                try:
                    attachment._migrate_remote_to_local()
                except (
                    ValidationError,
                    requests.exceptions.RequestException,
                ) as e:
                    _logger.error(
                        "Failed to migrate attachment %s to local: %s",
                        attachment.id,
                        e,
                    )
        return attachments.filtered(lambda a: not a._is_remote_source())
