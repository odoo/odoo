import base64
import io
import logging
import mimetypes
import re
import threading
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, Self
from urllib.parse import parse_qs, urlparse

import cssselect2.compiler as _cs2_compiler
import lxml.html
import requests
import weasyprint
from cssselect2 import parser as _cs2_parser
from lxml import etree
from markupsafe import Markup
from PIL import Image, ImageFile
from weasyprint.css.counters import CounterStyle
from weasyprint.document import Document as WeasyDocument
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetcher, URLFetcherResponse

from odoo import _, api, models, modules, tools
from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.http import request, root
from odoo.libs import guarded_http, netguard
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import loads as json_loads
from odoo.libs.netguard import DestinationRefused
from odoo.service import security
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.base.models.report_paperformat import PAPER_SIZE_BY_KEY

_LOOPBACK_HOSTS = frozenset(
    {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    }
)

_DEFAULT_PORTS = {"http": 80, "https": 443}

_EXTERNAL_RESOURCE_TIMEOUT = (5.0, 10.0)
_EXTERNAL_RESOURCE_MAX_SECONDS = 30.0
_EXTERNAL_RESOURCE_MAX_BYTES = 16 * 1024 * 1024
_DECODED_RESPONSE_HEADERS = frozenset(
    {"content-encoding", "content-length", "transfer-encoding"}
)


def _get_port_effective(parsed: Any) -> int:
    return parsed.port or _DEFAULT_PORTS.get(parsed.scheme or "http", 80)


def _is_tls_verification_required(url: str) -> bool:
    return urlparse(url).hostname not in _LOOPBACK_HOSTS


def _get_own_origin(
    url: str, cookies: dict[str, str], verify: bool
) -> requests.Response:
    with guarded_http.guarded_session(netguard.PRIVATE_ALLOWED) as session:
        return session.get(url, cookies=cookies, timeout=10, verify=verify)


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("1", "true", "yes", "on"):
            return True
        if token in ("0", "false", "no", "off", ""):
            return False
    return default


def _add_page_css(html: str, css: str) -> str:
    html_str = str(html)
    style_tag = f'<style type="text/css">{css}</style>'
    if "</head>" in html_str:
        return html_str.replace("</head>", f"{style_tag}</head>", 1)
    return f"{style_tag}{html_str}"


def _escape_css_string(text: str) -> str:
    collapsed = " ".join(str(text).split())
    return collapsed.replace("\\", "\\\\").replace('"', '\\"')


def _prepare_watermark_css(text: str) -> str:
    return (
        "\nbody::before {"
        f' content: "{_escape_css_string(text)}";'
        " position: fixed;"
        " top: 50%; left: 50%;"
        " transform: translate(-50%, -50%) rotate(-35deg);"
        " font-size: 6rem; font-weight: 700; letter-spacing: 0.1em;"
        " white-space: nowrap; text-transform: uppercase;"
        " color: rgba(33, 37, 41, 0.08);"
        " z-index: 1000;"
        " }\n"
    )


_WEASY_WARNING_KEEP = 5

_weasy_warning_sink = threading.local()


class _WeasyWarningRouter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        sink = getattr(_weasy_warning_sink, "sink", None)
        if sink is None:
            return record.levelno >= logging.ERROR
        sink.append(record.getMessage())
        return False


@contextmanager
def _capture_weasy_warnings() -> Iterator[deque[str]]:
    sink: deque[str] = deque(maxlen=_WEASY_WARNING_KEEP)
    previous = getattr(_weasy_warning_sink, "sink", None)
    _weasy_warning_sink.sink = sink
    try:
        yield sink
    finally:
        _weasy_warning_sink.sink = previous


_WEASY_CSS_CACHE_MAX = 32

_WEASY_DB_STATE_MAX = 8

_IMMUTABLE_ASSET_CSS_RE = re.compile(r"^/web/assets/(?!debug/)[^/]+/")

_NATIVE_MERGE_MAX = 50

PDF_OPTIONS_DATA_KEY = "__pdf_options__"
_PER_BODY_PDF_OPTION_KEYS = frozenset(("dpi", "jpeg_quality"))
_DOCUMENT_PDF_OPTION_KEYS = frozenset(("pdf_variant", "attachments", "xmp_metadata"))
_LAYOUT_BODY_TOKEN = "<!--odoo-report-body-->"
_PDF_OPTION_KEYS = (
    "pdf_variant",
    "attachments",
    "xmp_metadata",
    "dpi",
    "jpeg_quality",
)

_OS2_MAX_UNICODE_RANGE_BIT = 122

_tolerant_fonts = threading.local()


class _WeasyDatabaseState:
    def __init__(self) -> None:
        self.font_config = FontConfiguration()
        self.css_cache: dict[tuple[str, str], Any] = {}
        self.css_lock = threading.Lock()


class _WeasySharedState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._db_states: dict[str, _WeasyDatabaseState] = {}
        self._process_setup_done = False

    def setup_process(self) -> None:
        if self._process_setup_done:
            return
        with self._lock:
            if self._process_setup_done:
                return
            weasy_logger = logging.getLogger("weasyprint")
            weasy_logger.setLevel(logging.WARNING)
            weasy_logger.addFilter(_WeasyWarningRouter())
            logging.getLogger("fontTools").propagate = False
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            if _cs2_compiler._compile_node is not _compile_node_depth_limited:
                _cs2_compiler._compile_node = _compile_node_depth_limited
            _install_tolerant_font_guard()
            self._process_setup_done = True

    def for_database(self, dbname: str) -> _WeasyDatabaseState:
        with self._lock:
            state = self._db_states.pop(dbname, None)
            if state is None:
                state = _WeasyDatabaseState()
                while len(self._db_states) >= _WEASY_DB_STATE_MAX:
                    self._db_states.pop(next(iter(self._db_states)))
            self._db_states[dbname] = state
            return state

    def get_parsed_css(
        self,
        state: _WeasyDatabaseState,
        key: tuple[str, str],
        parse: Callable[[], Any],
    ) -> Any:
        with state.css_lock:
            if key in state.css_cache:
                return state.css_cache[key]
        parsed = parse()
        with state.css_lock:
            if key not in state.css_cache:
                while len(state.css_cache) >= _WEASY_CSS_CACHE_MAX:
                    state.css_cache.pop(next(iter(state.css_cache)))
                state.css_cache[key] = parsed
            return state.css_cache[key]

    def clear_for_tests(self) -> None:
        with self._lock:
            self._db_states.clear()


_weasy_state = _WeasySharedState()


def _install_tolerant_font_guard() -> None:
    from fontTools.ttLib.tables.O_S_2f_2 import table_O_S_2f_2

    original = table_O_S_2f_2.setUnicodeRanges
    if getattr(original, "_odoo_tolerant_guard", False):
        return

    def set_unicode_ranges(self, bits):
        if not getattr(_tolerant_fonts, "active", False):
            return original(self, bits)
        sanitized = {b for b in bits if 0 <= b <= _OS2_MAX_UNICODE_RANGE_BIT}
        dropped = set(bits) - sanitized
        if dropped:
            _logger.warning(
                "Dropped invalid OS/2 unicode range bits: %s", sorted(dropped)
            )
        return original(self, sanitized)

    set_unicode_ranges._odoo_tolerant_guard = True
    table_O_S_2f_2.setUnicodeRanges = set_unicode_ranges


@contextmanager
def _tolerant_fonts_enabled() -> Iterator[None]:
    was_active = getattr(_tolerant_fonts, "active", False)
    _tolerant_fonts.active = True
    try:
        yield
    finally:
        _tolerant_fonts.active = was_active


def _render_html_document(
    html_string: str,
    url_fetcher: Any,
    stylesheets: list | None,
    font_config: Any,
    image_cache: dict[str, Any] | None,
) -> WeasyDocument:
    return weasyprint.HTML(string=html_string, url_fetcher=url_fetcher).render(
        font_config=font_config,
        counter_style=CounterStyle(),
        stylesheets=stylesheets or None,
        presentational_hints=True,
        optimize_images=True,
        cache={} if image_cache is None else image_cache,
    )


def _write_pdf_tolerant_fonts(
    html_string,
    url_fetcher,
    stylesheets,
    pdf_options=None,
    font_config=None,
    image_cache=None,
):
    _weasy_state.setup_process()
    with _tolerant_fonts_enabled():
        return _render_html_document(
            html_string,
            url_fetcher,
            stylesheets,
            font_config if font_config is not None else FontConfiguration(),
            image_cache,
        ).write_pdf(**(pdf_options or {}))


_RE_CSS_LINK = re.compile(
    r'<link\b(?=[^>]*\brel=["\']stylesheet["\'])(?=[^>]*\bhref=["\']([^"\']+)["\'])[^>]*/?>',
    re.IGNORECASE,
)

_xpath_main = etree.ETXPath("//main")
_xpath_article = etree.ETXPath(
    "//div[contains(concat(' ', normalize-space(@class), ' '), ' article ')]"
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_original_compile_node = _cs2_compiler._compile_node
_MAX_SELECTOR_COMBINATORS = 11
_selector_depth = threading.local()


def _compile_node_depth_limited(selector: Any) -> str:
    if isinstance(selector, _cs2_parser.CombinedSelector):
        depth = getattr(_selector_depth, "value", 0)
        if depth >= _MAX_SELECTOR_COMBINATORS:
            _logger.warning(
                "Dropped a CSS selector nesting more than %d combinators; it "
                "will not match. Flatten it in the report stylesheet.",
                _MAX_SELECTOR_COMBINATORS,
            )
            return "0"
        _selector_depth.value = depth + 1
        try:
            return _original_compile_node(selector)
        finally:
            _selector_depth.value = depth
    return _original_compile_node(selector)


_WEB_IMAGE_MODEL_RE = re.compile(
    r"^/web/image/(?P<model>[\w.]+)/(?P<id>\d+)/(?P<field>\w+)"
    r"(?:/(?P<width>\d+)x(?P<height>\d+))?"
)
_WEB_IMAGE_ID_RE = re.compile(
    r"^/web/image/(?P<id>\d+)(?:-[\w]+)?"
    r"(?:/(?P<width>\d+)x(?P<height>\d+))?"
)
_BARCODE_RE = re.compile(r"^/report/barcode/(?P<type>[^/]+)/(?P<value>.+)")


def _path_has_route(path: str, route: str) -> bool:
    return path.endswith(route) or f"{route}/" in path


class OdooURLFetcher(URLFetcher):
    def __init__(self, env: Any, base_url: str | None = None) -> None:
        super().__init__(
            allowed_protocols=["http", "https", "data"],
            allow_redirects=False,
        )
        self._env = env
        self._base_url = base_url or env["ir.actions.report"]._get_report_url()
        self._parsed_base = urlparse(self._base_url)
        self._addons_paths = tools.config["addons_path"]
        self._session_cookie = None
        self._temp_session = None
        self._asset_attachments: dict[str, Any] = {}
        self._setup_session()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._temp_session is not None:
            root.session_store.delete(self._temp_session)
            self._temp_session = None

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
                self._temp_session.session_token = security.get_session_token(
                    self._temp_session,
                    self._env,
                )
            root.session_store.save(self._temp_session)
            self._session_cookie = self._temp_session.sid

    def _is_same_origin(self, parsed: Any) -> bool:
        base = self._parsed_base
        if _get_port_effective(parsed) != _get_port_effective(base):
            return False
        if parsed.hostname == base.hostname:
            return True
        return {parsed.hostname, base.hostname} <= _LOOPBACK_HOSTS

    def fetch(
        self, url: str, headers: dict[str, str] | None = None
    ) -> URLFetcherResponse:
        parsed = urlparse(url)

        if parsed.scheme and parsed.scheme not in ("http", "https", ""):
            return super().fetch(url, headers)

        is_local = not parsed.hostname or self._is_same_origin(parsed)
        if not is_local:
            return self._get_external_resource(url, parsed.hostname, headers)

        path = parsed.path or ""

        if "/web/assets/" in path:
            result = self._resolve_asset_bundle(url, path)
            if result:
                return result

        if "/static/" in path:
            result = self._resolve_static_file(url, path)
            if result:
                return result

        if _path_has_route(path, "/web/image"):
            result = self._resolve_web_image(url, path, parsed.query)
            if result:
                return result

        if _path_has_route(path, "/report/barcode"):
            result = self._resolve_barcode(url, path, parsed.query)
            if result:
                return result

        _debug.logic("fetch_via_http", path=path[:120])
        return self._get_via_http(url, path)

    def _get_external_resource(
        self, url: str, hostname: str | None, headers: dict[str, str] | None
    ) -> URLFetcherResponse:
        try:
            response = self._env["ir.egress"].request(
                "GET",
                url,
                purpose="report_resource",
                headers=headers,
                timeout=_EXTERNAL_RESOURCE_TIMEOUT,
                max_bytes=_EXTERNAL_RESOURCE_MAX_BYTES,
                max_seconds=_EXTERNAL_RESOURCE_MAX_SECONDS,
            )
        except DestinationRefused as refusal:
            _logger.warning(
                "WeasyPrint refused a report resource (possible SSRF): %s: %s",
                url,
                refusal,
            )
            _debug.logic("fetch_blocked", host=hostname)
            raise
        _debug.logic("fetch_external", host=hostname, status=response.status_code)
        response.raise_for_status()
        return URLFetcherResponse(
            response.url,
            body=response.content,
            headers={
                name: value
                for name, value in response.headers.items()
                if name.lower() not in _DECODED_RESPONSE_HEADERS
            },
            status=response.status_code,
        )

    def _get_asset_attachment(self, path: str) -> Any:
        if path not in self._asset_attachments:
            self._asset_attachments[path] = (
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
        return self._asset_attachments[path]

    @staticmethod
    def _has_asset_blob(attachment: Any) -> bool:
        if not attachment:
            return False
        if attachment.store_fname:
            backend = attachment._get_storage_backend_for_key(attachment.store_fname)
            return bool(backend.read(attachment.store_fname, 1))
        return bool(attachment.db_datas)

    def get_asset_checksum(self, url: str) -> str | None:
        attachment = self._get_asset_attachment(urlparse(url).path or "")
        if not self._has_asset_blob(attachment):
            return None
        return attachment.checksum or None

    def _resolve_asset_bundle(self, url: str, path: str) -> URLFetcherResponse | None:
        parts = path.strip("/").split("/")
        if len(parts) < 4 or parts[0] != "web" or parts[1] != "assets":
            return None

        unique = parts[2]
        filename = parts[3]
        debug_assets = unique == "debug"

        if not debug_assets:
            attachment = self._get_asset_attachment(path)
            if attachment and attachment.raw:
                return self._prepare_fetcher_response(
                    url, attachment.raw, attachment.mimetype or "text/css"
                )

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
                return self._prepare_fetcher_response(
                    url, attachment.raw, attachment.mimetype or "text/css"
                )
        except Exception:
            _logger.warning(
                "Failed to generate asset bundle for %s", path, exc_info=True
            )
        return None

    def _resolve_static_file(self, url: str, path: str) -> URLFetcherResponse | None:
        parts = path.lstrip("/").split("/")
        if len(parts) < 3 or parts[1] != "static":
            return None
        module_name = parts[0]
        static_path = "/".join(parts[1:])
        for addons_path in self._addons_paths:
            addons_root = Path(addons_path.strip()).resolve()
            candidate = (addons_root / module_name / static_path).resolve()
            if not candidate.is_relative_to(addons_root):
                continue
            if candidate.is_file():
                mime = mimetypes.guess_type(candidate)[0] or "application/octet-stream"
                return self._prepare_fetcher_response(
                    url, Path(candidate).read_bytes(), mime
                )
        return None

    def _resolve_web_image(
        self,
        url: str,
        path: str,
        query: str,
    ) -> URLFetcherResponse | None:
        try:
            model, res_id, field, width, height = self._parse_image_url(path, query)
            ir_binary = self._env["ir.binary"]
            record = ir_binary._get_record(
                res_model=model, res_id=res_id, field_name=field
            )
            stream = ir_binary._get_stream_image_from_record(
                record,
                field,
                width=width,
                height=height,
            )
            data = stream.read()
            if data:
                return self._prepare_fetcher_response(
                    url, data, stream.mimetype or "image/png"
                )
        except Exception:
            _logger.debug("Local image resolution failed for %s", path, exc_info=True)
        return None

    def _resolve_barcode(
        self,
        url: str,
        path: str,
        query: str,
    ) -> URLFetcherResponse | None:
        try:
            params = parse_qs(query)
            match = _BARCODE_RE.match(path)
            if match:
                barcode_type = match.group("type")
                value = match.group("value")
            else:
                barcode_type = params.get("barcode_type", [None])[0]
                value = params.get("value", [None])[0]

            if not barcode_type or not value:
                return None

            kwargs = {}
            for key in (
                "width",
                "height",
                "humanreadable",
                "quiet",
                "mask",
                "barLevel",
                "barBorder",
            ):
                val = params.get(key, [None])[0]
                if val is not None:
                    kwargs[key] = val

            barcode_bytes = (
                self._env["ir.actions.report"]
                .sudo()
                .prepare_barcode(
                    barcode_type,
                    value,
                    **kwargs,
                )
            )
            if barcode_bytes:
                return self._prepare_fetcher_response(url, barcode_bytes, "image/png")
        except Exception:
            _logger.debug("Local barcode resolution failed for %s", path, exc_info=True)
        return None

    @staticmethod
    def _parse_image_url(path: str, query: str) -> tuple:
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

    def _get_via_http(self, url: str, path: str) -> URLFetcherResponse:
        parsed = urlparse(url)
        if parsed.hostname:
            full_url = url
        else:
            query = f"?{parsed.query}" if parsed.query else ""
            full_url = f"{self._base_url}{path}{query}"
        try:
            cookies = (
                {"session_id": self._session_cookie} if self._session_cookie else {}
            )
            resp = self._get_http_response(
                full_url, cookies, verify=_is_tls_verification_required(full_url)
            )
            try:
                resp.raise_for_status()
                content_type = resp.headers.get(
                    "Content-Type", "application/octet-stream"
                )
                return self._prepare_fetcher_response(url, resp.content, content_type)
            finally:
                resp.close()
        except Exception:
            _logger.warning(
                "WeasyPrint URL fetch failed for %s", full_url, exc_info=True
            )
            _debug.logic("fetch_http_failed", path=path[:120])
            return super().fetch(full_url)

    @staticmethod
    def _get_http_response(
        url: str, cookies: dict[str, str], verify: bool = True
    ) -> requests.Response:
        current_test = modules.module.current_test
        if not current_test:
            return _get_own_origin(url, cookies, verify)

        from odoo.tests.common import TEST_CURSOR_COOKIE_NAME, release_test_lock

        key = (
            getattr(current_test, "http_request_key", "") or current_test.canonical_tag
        )
        cookies[TEST_CURSOR_COOKIE_NAME] = key
        saved_key = getattr(current_test, "http_request_key", "")
        current_test.http_request_key = key
        try:
            with release_test_lock():
                return _get_own_origin(url, cookies, verify)
        finally:
            current_test.http_request_key = saved_key

    @staticmethod
    def _prepare_fetcher_response(
        url: str, body: bytes, content_type: str = "application/octet-stream"
    ) -> URLFetcherResponse:
        return URLFetcherResponse(
            url, body=body, headers={"Content-Type": content_type}
        )


class WeasyPrintEngine:
    def __init__(
        self,
        fetcher_factory: Callable[[], OdooURLFetcher],
        merge_pdfs: Callable[[list[io.BytesIO]], io.BytesIO],
        native_merge_max: int = _NATIVE_MERGE_MAX,
        dbname: str = "",
    ) -> None:
        self._fetcher_factory = fetcher_factory
        self._merge_pdfs = merge_pdfs
        self._native_merge_max = native_merge_max
        self._dbname = dbname
        self.warnings: deque[str] = deque(maxlen=_WEASY_WARNING_KEEP)

    def _database_state(self) -> _WeasyDatabaseState:
        _weasy_state.setup_process()
        return _weasy_state.for_database(self._dbname)

    def render(
        self,
        bodies: list[str],
        page_css: str,
        *,
        split: bool = False,
        pdf_options: dict[str, Any] | None = None,
    ) -> bytes | list[bytes]:
        if not bodies:
            raise UserError(_("No content to render as PDF."))

        db_state = self._database_state()
        image_cache: dict[str, Any] = {}
        opts = pdf_options or {}
        wants_pdfa = bool(opts.get("pdf_variant"))
        wants_single_document = any(opts.get(key) for key in _DOCUMENT_PDF_OPTION_KEYS)
        if wants_pdfa:
            page_css = f"{page_css}\nhtml {{ image-rendering: crisp-edges; }}\n"

        with (
            _capture_weasy_warnings() as sink,
            self._fetcher_factory() as fetcher,
        ):
            self.warnings = sink
            parsed_css_by_url: dict[str, Any] = {}
            processed = [
                self._prepare_body_and_stylesheets(
                    body, page_css, parsed_css_by_url, fetcher, db_state
                )
                for body in bodies
            ]
            _debug.pipeline(
                "weasy_render",
                bodies=len(bodies),
                split=split,
                pdfa=wants_pdfa,
                single_document=wants_single_document,
                stylesheets=len(parsed_css_by_url),
                incremental=(
                    not split
                    and not wants_single_document
                    and len(processed) > self._native_merge_max
                ),
            )

            if split:
                body_options = self._prepare_body_pdf_options(pdf_options)
                return [
                    self._render_and_serialize_body(
                        html_str, fetcher, body_css, body_options, db_state, image_cache
                    )
                    for html_str, body_css in processed
                ]

            if not wants_single_document and len(processed) > self._native_merge_max:
                return self._render_and_merge_incrementally(
                    processed, fetcher, db_state, image_cache, pdf_options
                )

            documents = [
                self._render_body_document(
                    html_str, fetcher, body_css, db_state, image_cache
                )
                for html_str, body_css in processed
            ]

            try:
                return self._serialize_documents(documents, pdf_options=pdf_options)
            except ValueError as ve:
                if "expected 0 <= int" in str(ve):
                    _logger.warning(
                        "fontTools setUnicodeRanges failed during PDF serialization "
                        "(%s). A system font has invalid OS/2 unicode range bits. "
                        "Retrying all bodies with patched setUnicodeRanges.",
                        ve,
                    )
                    return self._serialize_with_tolerant_fonts(
                        processed,
                        fetcher,
                        db_state,
                        image_cache,
                        pdf_options=pdf_options,
                    )
                _logger.exception("WeasyPrint PDF serialization failed")
                raise self._prepare_pdf_render_error(str(ve)) from None
            except Exception as e:
                _logger.exception("WeasyPrint PDF serialization failed")
                raise self._prepare_pdf_render_error(str(e)) from None

    def render_each_tolerant(
        self, bodies: list[str], page_css: str
    ) -> list[bytes | None]:
        db_state = self._database_state()
        image_cache: dict[str, Any] = {}
        results: list[bytes | None] = []
        with (
            _capture_weasy_warnings() as sink,
            self._fetcher_factory() as fetcher,
        ):
            self.warnings = sink
            parsed_css_by_url: dict[str, Any] = {}
            for body in bodies:
                sink.clear()
                try:
                    html_str, body_css = self._prepare_body_and_stylesheets(
                        body, page_css, parsed_css_by_url, fetcher, db_state
                    )
                    results.append(
                        self._render_and_serialize_body(
                            html_str, fetcher, body_css, None, db_state, image_cache
                        )
                    )
                except Exception as e:
                    _logger.warning("HTML-to-PDF rendering failed for one body: %s", e)
                    results.append(None)
        _debug.pipeline(
            "render_each_tolerant",
            bodies=len(bodies),
            failed=sum(1 for result in results if result is None),
        )
        return results

    @staticmethod
    def _prepare_body_pdf_options(
        pdf_options: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        body_options = {
            key: value
            for key, value in (pdf_options or {}).items()
            if key in _PER_BODY_PDF_OPTION_KEYS
        }
        return body_options or None

    def _render_and_merge_incrementally(
        self,
        processed: list[tuple[str, Any]],
        fetcher: Any,
        db_state: Any,
        image_cache: dict[str, Any],
        pdf_options: dict[str, Any] | None = None,
    ) -> bytes:
        body_options = self._prepare_body_pdf_options(pdf_options)
        _logger.info(
            "WeasyPrint: %d bodies exceeds the native-merge threshold "
            "(%d); serializing incrementally and merging with pypdf to "
            "bound peak memory.",
            len(processed),
            self._native_merge_max,
        )
        streams = [
            io.BytesIO(
                self._render_and_serialize_body(
                    html_str,
                    fetcher,
                    body_css,
                    body_options,
                    db_state,
                    image_cache,
                )
            )
            for html_str, body_css in processed
        ]
        return self._merge_pdfs(streams).getvalue()

    def _render_and_serialize_body(
        self,
        html_str: str,
        fetcher: OdooURLFetcher,
        body_css: list,
        pdf_options: dict[str, Any] | None = None,
        db_state: _WeasyDatabaseState | None = None,
        image_cache: dict[str, Any] | None = None,
    ) -> bytes:
        document = self._render_body_document(
            html_str, fetcher, body_css, db_state, image_cache
        )
        buf = io.BytesIO()
        try:
            document.write_pdf(target=buf, **(pdf_options or {}))
        except ValueError as ve:
            if "expected 0 <= int" in str(ve):
                _logger.warning(
                    "fontTools setUnicodeRanges failed serializing one body "
                    "(%s); retrying it with patched setUnicodeRanges.",
                    ve,
                )
                return _write_pdf_tolerant_fonts(
                    html_str,
                    fetcher,
                    body_css,
                    pdf_options,
                    (db_state or self._database_state()).font_config,
                    image_cache,
                )
            _logger.exception("WeasyPrint PDF serialization failed")
            raise self._prepare_pdf_render_error(str(ve)) from None
        return buf.getvalue()

    def _prepare_body_and_stylesheets(
        self,
        body: str,
        page_css: str,
        parsed_css_by_url: dict[str, Any],
        fetcher: OdooURLFetcher | None = None,
        db_state: _WeasyDatabaseState | None = None,
    ) -> tuple[str, list]:
        html_with_css = _add_page_css(body, page_css)
        body_css = []
        strip_urls = set()
        for css_url in _RE_CSS_LINK.findall(html_with_css):
            if css_url not in parsed_css_by_url:
                if fetcher is None:
                    continue
                parsed_css_by_url[css_url] = self._parse_stylesheet(
                    css_url, fetcher, db_state or self._database_state()
                )
            parsed = parsed_css_by_url[css_url]
            if parsed is not None and css_url not in strip_urls:
                body_css.append(parsed)
                strip_urls.add(css_url)
        if strip_urls:
            html_with_css = _RE_CSS_LINK.sub(
                lambda m: "" if m.group(1) in strip_urls else m.group(0),
                html_with_css,
            )
        return html_with_css, body_css

    @staticmethod
    def _parse_stylesheet(
        css_url: str, fetcher: OdooURLFetcher, db_state: _WeasyDatabaseState
    ) -> Any:

        def parse() -> Any:
            return weasyprint.CSS(
                url=css_url,
                url_fetcher=fetcher,
                font_config=db_state.font_config,
            )

        try:
            if _IMMUTABLE_ASSET_CSS_RE.match(css_url):
                checksum = fetcher.get_asset_checksum(css_url)
                if checksum:
                    return _weasy_state.get_parsed_css(
                        db_state, (css_url, checksum), parse
                    )
            return parse()
        except Exception:
            _logger.warning("Failed to pre-parse CSS: %s", css_url, exc_info=True)
            return None

    def _render_body_document(
        self,
        html_str: str,
        fetcher: OdooURLFetcher,
        body_css: list,
        db_state: _WeasyDatabaseState | None = None,
        image_cache: dict[str, Any] | None = None,
    ) -> WeasyDocument:
        state = db_state or self._database_state()
        try:
            return _render_html_document(
                html_str, fetcher, body_css, state.font_config, image_cache
            )
        except Exception as e:
            _logger.exception(
                "WeasyPrint layout failed; renderer said: %s",
                "; ".join(self.warnings) or "nothing",
            )
            raise self._prepare_pdf_render_error(str(e)) from None

    @staticmethod
    def _serialize_documents(
        documents: list[WeasyDocument],
        *,
        pdf_options: dict[str, Any] | None = None,
    ) -> bytes:
        opts = pdf_options or {}
        if len(documents) == 1:
            buf = io.BytesIO()
            documents[0].write_pdf(target=buf, **opts)
            return buf.getvalue()

        all_pages = [p for doc in documents for p in doc.pages]
        buf = io.BytesIO()
        documents[0].copy(all_pages).write_pdf(target=buf, **opts)
        return buf.getvalue()

    def _serialize_with_tolerant_fonts(
        self,
        processed: list[tuple[str, list]],
        fetcher: OdooURLFetcher,
        db_state: _WeasyDatabaseState,
        image_cache: dict[str, Any],
        *,
        pdf_options: dict[str, Any] | None = None,
    ) -> bytes:
        with _tolerant_fonts_enabled():
            documents = [
                self._render_body_document(
                    html_str, fetcher, body_css, db_state, image_cache
                )
                for html_str, body_css in processed
            ]
            return self._serialize_documents(documents, pdf_options=pdf_options)

    def _prepare_pdf_render_error(self, detail: str) -> UserError:
        message = _(
            "PDF rendering failed. Please check the report template.\n\nDetails: %s",
            detail,
        )
        warnings = list(self.warnings)
        if warnings:
            message += _("\n\nRenderer warnings (last %s):\n", len(warnings))
            message += "\n".join(warnings)
        return UserError(message)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_layout(self) -> Any:
        return self.env.ref("web.minimal_layout", raise_if_not_found=False)

    def _get_report_url(self, layout: Any = None) -> str:
        report_url = self.env["ir.config_parameter"].sudo().get_param("report.url")
        return report_url or (layout or self._get_layout() or self).get_base_url()

    _WEASYPRINT_PAGE_SIZES = {
        "a3",
        "a4",
        "a5",
        "b4",
        "b5",
        "letter",
        "legal",
    }

    @api.model
    def _prepare_paperformat_css(
        self,
        paperformat: Any,
        landscape: bool = False,
        specific_paperformat_args: dict[str, str] | None = None,
    ) -> str:
        args = specific_paperformat_args or {}
        for dead_attr in ("data-report-header-spacing", "data-report-dpi"):
            if dead_attr in args:
                _logger.warning(
                    "_prepare_paperformat_css: %r is a wkhtmltopdf-specific attribute "
                    "with no WeasyPrint equivalent and is silently ignored. "
                    "Remove it from the report template to suppress this warning.",
                    dead_attr,
                )
        _force_landscape = args.get("data-report-landscape")
        if _force_landscape and _force_landscape not in ("False", "0", "false", ""):
            landscape = True
        orientation = (
            "landscape"
            if landscape or paperformat.orientation == "Landscape"
            else "portrait"
        )

        if paperformat.format and paperformat.format != "custom":
            fmt = paperformat.format.lower()
            if fmt in self._WEASYPRINT_PAGE_SIZES:
                size_css = f"{fmt} {orientation}"
            else:
                ps = PAPER_SIZE_BY_KEY.get(paperformat.format)
                if ps:
                    size_css = f"{ps['width']}mm {ps['height']}mm"
                    if orientation == "landscape":
                        size_css = f"{ps['height']}mm {ps['width']}mm"
                else:
                    size_css = f"A4 {orientation}"
        elif paperformat.page_width and paperformat.page_height:
            w, h = paperformat.page_width, paperformat.page_height
            if orientation == "landscape":
                w, h = h, w
            size_css = f"{w}mm {h}mm"
        else:
            size_css = f"A4 {orientation}"

        def _margin(attr, fallback):
            raw = args.get(attr, fallback)
            try:
                return float(raw)
            except TypeError, ValueError:
                _logger.warning(
                    "_prepare_paperformat_css: %r=%r is not a valid number; "
                    "falling back to the paperformat value %r.",
                    attr,
                    raw,
                    fallback,
                )
                return float(fallback)

        margin_top = _margin("data-report-margin-top", paperformat.margin_top)
        margin_bottom = _margin("data-report-margin-bottom", paperformat.margin_bottom)
        margin_left = _margin("data-report-margin-left", paperformat.margin_left)
        margin_right = _margin("data-report-margin-right", paperformat.margin_right)

        header_border = (
            "border-bottom: 1px solid black;" if paperformat.header_line else ""
        )

        return (
            f"@page {{\n"
            f"  size: {size_css};\n"
            f"  margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm;\n"
            f"  @top-left {{ content: element(page-header); margin: 0; padding: 0; width: 100%; }}\n"
            f"  @bottom-left {{ content: element(page-footer); margin: 0; padding: 0; width: 100%; }}\n"
            f"}}\n" + (f".header {{ {header_border} }}\n" if header_border else "")
        )

    def _prepare_url_fetcher(self) -> OdooURLFetcher:
        return OdooURLFetcher(self.env)

    @api.model
    def _get_native_merge_max(self) -> int:
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("report.weasyprint_native_merge_max")
        )
        if param:
            try:
                return int(param)
            except TypeError, ValueError:
                _logger.warning(
                    "Invalid report.weasyprint_native_merge_max=%r; using default %d.",
                    param,
                    _NATIVE_MERGE_MAX,
                )
                _debug.logic("native_merge_max_invalid", param=param)
        return _NATIVE_MERGE_MAX

    @api.model
    def _prepare_weasyprint_engine(self) -> WeasyPrintEngine:
        report_model = self.env["ir.actions.report"]
        return WeasyPrintEngine(
            fetcher_factory=report_model._prepare_url_fetcher,
            merge_pdfs=report_model._merge_pdfs,
            native_merge_max=report_model._get_native_merge_max(),
            dbname=self.env.cr.dbname,
        )

    def _prepare_weasyprint_html(
        self, html: str, report_model: str | bool = False
    ) -> tuple[list[str], list[int | None], dict[str, str]]:
        layout = self._get_layout()
        if not layout:
            raise UserError(
                _(
                    "The report layout web.minimal_layout is missing, so no PDF "
                    "body can be built. Update or reinstall the web module."
                )
            )

        base_url = self._get_report_url(layout=layout)
        html_root = lxml.html.fromstring(
            html, parser=lxml.html.HTMLParser(encoding="utf-8")
        )

        specific_paperformat_args = {}
        for attribute in html_root.items():
            if attribute[0].startswith("data-report-"):
                specific_paperformat_args[attribute[0]] = attribute[1]

        articles = _xpath_article(html_root)

        if not articles:
            body = self._render_whole_document_body(layout, html_root, base_url)
            return [body], [None], specific_paperformat_args

        bodies, res_ids = self._render_article_bodies(
            layout, articles, base_url, report_model
        )
        return bodies, res_ids, specific_paperformat_args

    def _render_whole_document_body(
        self, layout: Any, html_root: Any, base_url: str
    ) -> str:
        main_nodes = _xpath_main(html_root)
        if not main_nodes:
            raise UserError(
                _("Report HTML has no <main> element. Check the report template.")
            )
        body_parent = main_nodes[0]
        body_html = "".join(
            lxml.html.tostring(c, encoding="unicode") for c in body_parent
        )
        return self.env["ir.qweb"]._render(
            layout.id,
            {**self._prepare_layout_values(base_url), "body": Markup(body_html)},
            raise_if_not_found=False,
        )

    def _prepare_layout_values(
        self, base_url: str, title: str | None = None
    ) -> dict[str, Any]:
        return {
            "subst": False,
            "base_url": base_url,
            "report_xml_id": self.xml_id,
            "css_margins": bool(self.get_paperformat().css_margins),
            "title": title or self.name or "",
            "subject": self.name or "",
            "debug": self.env.context.get("debug"),
        }

    def _render_article_bodies(
        self, layout: Any, articles: list, base_url: str, report_model: str | bool
    ) -> tuple[list[str], list[int | None]]:
        titles_by_res_id = self._get_document_titles(articles, report_model)

        bodies = []
        res_ids = []
        layouts_by_key: dict[tuple[str | None, str], str] = {}
        for article_node in articles:
            header_node, footer_node = self._get_article_header_footer(article_node)

            article_res_id = None
            if article_node.get("data-oe-model") == report_model:
                article_res_id = int(article_node.get("data-oe-id") or 0)

            parts = []
            if header_node is not None:
                parts.append(lxml.html.tostring(header_node, encoding="unicode"))
            if footer_node is not None:
                parts.append(lxml.html.tostring(footer_node, encoding="unicode"))
            parts.append(lxml.html.tostring(article_node, encoding="unicode"))

            combined_html = "".join(parts)

            lang = article_node.get("data-oe-lang") or None
            title = titles_by_res_id.get(article_res_id) or self.name or ""
            key = (lang, title)
            if key not in layouts_by_key:
                IrQweb = self.env["ir.qweb"]
                if lang:
                    IrQweb = IrQweb.with_context(lang=lang)
                layouts_by_key[key] = str(
                    IrQweb._render(
                        layout.id,
                        {
                            **self._prepare_layout_values(base_url, title),
                            "body": Markup(_LAYOUT_BODY_TOKEN),
                        },
                        raise_if_not_found=False,
                    )
                )
            bodies.append(
                Markup(layouts_by_key[key].replace(_LAYOUT_BODY_TOKEN, combined_html))
            )
            res_ids.append(article_res_id)

        return bodies, res_ids

    @staticmethod
    def _has_html_class(node: Any, name: str) -> bool:
        return name in (node.get("class") or "").split()

    @classmethod
    def _get_article_header_footer(cls, article_node: Any) -> tuple[Any, Any]:
        header_node = None
        for sibling in article_node.itersiblings(preceding=True):
            if cls._has_html_class(sibling, "article"):
                break
            if cls._has_html_class(sibling, "header"):
                header_node = sibling
                break
        footer_node = None
        for sibling in article_node.itersiblings():
            if cls._has_html_class(sibling, "article") or cls._has_html_class(
                sibling, "header"
            ):
                break
            if cls._has_html_class(sibling, "footer"):
                footer_node = sibling
                break
        return header_node, footer_node

    def _get_document_titles(
        self, articles: list, report_model: str | bool
    ) -> dict[int, str]:
        if not (self.print_report_name and report_model):
            return {}
        res_ids = [
            int(node.get("data-oe-id", 0))
            for node in articles
            if node.get("data-oe-model") == report_model and node.get("data-oe-id")
        ]
        titles = {}
        for record in self.env[report_model].browse(res_ids).exists():
            try:
                name = safe_eval(
                    self.print_report_name, {"object": record, "time": time}
                )
            except Exception:
                _logger.debug(
                    "print_report_name %r failed for %s(%s); falling back to the "
                    "report label as PDF title.",
                    self.print_report_name,
                    report_model,
                    record.id,
                    exc_info=True,
                )
                continue
            if name and isinstance(name, str):
                titles[record.id] = name
        return titles

    @staticmethod
    def _has_duplicated_ids(res_ids: list[int] | None) -> bool:
        return bool(res_ids and len(res_ids) != len(set(res_ids)))

    @staticmethod
    def _prepare_pdf_options(
        pdf_variant: str | None = None,
        attachments: list[Any] | None = None,
        xmp_metadata: list[bytes | str] | None = None,
        dpi: int | None = None,
        jpeg_quality: int | None = None,
    ) -> dict[str, Any] | None:
        if not (pdf_variant or attachments or xmp_metadata or dpi or jpeg_quality):
            return None
        options: dict[str, Any] = {}
        if dpi:
            options["dpi"] = int(dpi)
        if jpeg_quality:
            options["jpeg_quality"] = int(jpeg_quality)
        if pdf_variant:
            options["pdf_variant"] = pdf_variant
            options["custom_metadata"] = True
        if attachments:
            options["attachments"] = [
                att
                if isinstance(att, weasyprint.Attachment)
                else weasyprint.Attachment(
                    string=att["content"],
                    name=att.get("name"),
                    description=att.get("description"),
                    relationship=att.get("relationship", "Unspecified"),
                )
                for att in attachments
            ]
        if xmp_metadata:
            uris = []
            for fragment in xmp_metadata:
                raw = fragment.encode() if isinstance(fragment, str) else fragment
                uris.append(
                    "data:application/rdf+xml;base64," + base64.b64encode(raw).decode()
                )
            options["xmp_metadata"] = uris
        return options

    @api.model
    def _render_html_to_pdf(
        self,
        bodies: list[str],
        report_ref: int | str | Any = False,
        landscape: bool = False,
        specific_paperformat_args: dict[str, str] | None = None,
        *,
        _split: bool = False,
        pdf_variant: str | None = None,
        attachments: list[Any] | None = None,
        xmp_metadata: list[bytes | str] | None = None,
        dpi: int | None = None,
        jpeg_quality: int | None = None,
    ) -> bytes | list[bytes]:
        if not bodies:
            raise UserError(_("No content to render as PDF."))

        report = self._get_report(report_ref) if report_ref else None
        paperformat = report.get_paperformat() if report else self.get_paperformat()
        page_css = self._prepare_paperformat_css(
            paperformat,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
        )
        watermark = self.env.context.get("report_watermark")
        if watermark:
            page_css += _prepare_watermark_css(watermark)
        pdf_options = self._prepare_pdf_options(
            pdf_variant, attachments, xmp_metadata, dpi, jpeg_quality
        )
        start = perf_counter()
        engine = self._prepare_weasyprint_engine()
        with _debug.perf(
            "html_to_pdf",
            report=report.report_name if report else None,
            bodies=len(bodies),
            split=_split,
            variant=pdf_variant,
        ) as span:
            result = engine.render(
                bodies, page_css, split=_split, pdf_options=pdf_options
            )
            span.set(warnings=len(engine.warnings))
        if engine.warnings:
            _logger.debug(
                "WeasyPrint emitted %d warning(s) rendering %s; last: %s",
                len(engine.warnings),
                report.report_name if report else "(no report ref)",
                engine.warnings[-1],
            )
        size = sum(len(pdf) for pdf in result) if _split else len(result)
        _logger.info(
            "WeasyPrint rendered %s: %d body(ies), %.2fs, %.0f KiB.",
            report.report_name if report else "(no report ref)",
            len(bodies),
            perf_counter() - start,
            size / 1024,
        )
        return result

    def _render_html_to_image(
        self,
        bodies: list[str],
        width: int,
        height: int,
        image_format: str = "jpg",
    ) -> list[bytes | None]:
        if not self._is_pdf_rendering_enabled():
            return [None] * len(bodies)

        try:
            import pymupdf
        except ImportError as e:
            _logger.warning("HTML-to-image rendering unavailable (PyMuPDF): %s", e)
            return [None] * len(bodies)

        page_css = f"@page {{ size: {width}px {height}px; margin: 0; }}"
        engine = self._prepare_weasyprint_engine()
        output_images: list[bytes | None] = []
        for pdf_bytes in engine.render_each_tolerant(bodies, page_css):
            if pdf_bytes is None:
                output_images.append(None)
                continue
            try:
                output_images.append(
                    self._convert_pdf_page_to_image(
                        pymupdf, pdf_bytes, width, height, image_format
                    )
                )
            except Exception as e:
                _logger.warning("HTML-to-image conversion failed: %s", e)
                output_images.append(None)
        return output_images

    @staticmethod
    def _convert_pdf_page_to_image(
        pymupdf: Any, pdf_bytes: bytes, width: int, height: int, image_format: str
    ) -> bytes:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            png_bytes = doc[0].get_pixmap(dpi=96, alpha=True).tobytes("png")
        with Image.open(io.BytesIO(png_bytes)) as src:
            img = src.resize((width, height), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        if image_format == "png":
            img.save(buf, format="PNG")
        else:
            img.convert("RGB").save(buf, format="JPEG")
        return buf.getvalue()

    @staticmethod
    def _get_html_with_header_footer(
        body: str, header: str | None = None, footer: str | None = None
    ) -> str:
        body = str(body)
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
            idx = body.find(">", body.find("<body")) + 1
            return body[:idx] + inject + body[idx:]
        return body

    @staticmethod
    def _prepare_attachment_stream(attachment: Any) -> io.BytesIO:
        stream = io.BytesIO(attachment.raw)
        if not (attachment.mimetype or "").startswith("image"):
            return stream
        converted = io.BytesIO()
        with Image.open(stream) as img:
            img.convert("RGB").save(converted, format="pdf")
        stream.close()
        return converted

    def _get_saved_attachment_streams(
        self,
        report: Self,
        res_ids: list[int] | None,
        has_duplicated_ids: bool,
    ) -> dict[int | bool, dict[str, Any]]:
        if not res_ids:
            return {}
        records = self.env[report.model].browse(res_ids)
        wants_attachment = (
            not has_duplicated_ids
            and report.attachment
            and not self.env.context.get("report_pdf_no_attachment")
        )
        attachment_names = {}
        attachments_by_id = {}
        if wants_attachment:
            records.check_access("read")
            attachment_names = report._get_attachment_filenames(records)
            attachments_by_id = report._get_attachments(records, attachment_names)
        collected: dict[int | bool, dict[str, Any]] = {}
        for record in records:
            res_id = record.id
            if res_id in collected:
                continue
            attachment = attachments_by_id.get(res_id) or None
            stream = None
            if attachment and report.attachment_use:
                stream = self._prepare_attachment_stream(attachment)
            collected[res_id] = {
                "stream": stream,
                "attachment": attachment,
                "attachment_name": attachment_names.get(res_id, "")
                if wants_attachment
                else None,
            }
        _debug.logic(
            "saved_attachment_streams",
            report=report.report_name,
            records=len(records),
            wants_attachment=bool(wants_attachment),
            reused=sum(1 for v in collected.values() if v["stream"]),
        )
        return collected

    def _render_qweb_pdf_prepare_streams(
        self,
        report_ref: int | str | Any,
        data: dict[str, Any],
        res_ids: list[int] | None = None,
    ) -> dict[int | bool, dict[str, Any]]:
        res_ids, data = self._normalize_render_args(res_ids, data, "pdf")
        _weasy_state.setup_process()

        pdf_options = data.pop(PDF_OPTIONS_DATA_KEY, None) or {}
        render_pdf_kwargs = {
            key: pdf_options[key] for key in _PDF_OPTION_KEYS if pdf_options.get(key)
        }

        report_sudo = self._get_report(report_ref)
        has_duplicated_ids = self._has_duplicated_ids(res_ids)

        collected_streams = self._get_saved_attachment_streams(
            report_sudo, res_ids, has_duplicated_ids
        )

        res_ids_wo_stream = [
            res_id
            for res_id, stream_data in collected_streams.items()
            if not stream_data["stream"]
        ]
        all_res_ids_wo_stream = res_ids if has_duplicated_ids else res_ids_wo_stream
        is_pdf_needed = not res_ids or res_ids_wo_stream
        _debug.pipeline(
            "prepare_streams", to_render=len(all_res_ids_wo_stream), pdf=is_pdf_needed
        )

        if is_pdf_needed:
            data.setdefault("debug", False)
            additional_context = {"debug": False}

            html = self.with_context(**additional_context)._render_qweb_html(
                report_sudo,
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

            self._check_attachment_split_ids(
                report_sudo, has_duplicated_ids, res_ids_wo_stream, html_ids
            )

            render_kwargs = {
                "report_ref": report_sudo,
                "landscape": self.env.context.get("landscape"),
                "specific_paperformat_args": specific_paperformat_args,
                **render_pdf_kwargs,
            }

            wants_single_document = any(
                render_pdf_kwargs.get(key) for key in _DOCUMENT_PDF_OPTION_KEYS
            )
            if not wants_single_document and self._can_split_pdf(
                has_duplicated_ids, res_ids, html_ids, res_ids_wo_stream
            ):
                self._collect_split_pdf_streams(
                    bodies,
                    html_ids,
                    res_ids_wo_stream,
                    collected_streams,
                    render_kwargs,
                )
            else:
                collected_streams = self._collect_single_pdf_stream(
                    bodies,
                    res_ids,
                    res_ids_wo_stream,
                    has_duplicated_ids,
                    collected_streams,
                    render_kwargs,
                )

        return collected_streams

    def _collect_single_pdf_stream(
        self,
        bodies: list,
        res_ids: list[int] | None,
        res_ids_wo_stream: list[int],
        has_duplicated_ids: bool,
        collected_streams: dict[int | bool, dict[str, Any]],
        render_kwargs: dict[str, Any],
    ) -> dict[int | bool, dict[str, Any]]:
        pdf_content_stream = io.BytesIO(
            self._render_html_to_pdf(bodies, **render_kwargs)
        )

        if not res_ids or has_duplicated_ids:
            return {
                False: {
                    "stream": pdf_content_stream,
                    "attachment": None,
                }
            }

        if len(res_ids_wo_stream) == 1:
            collected_streams[res_ids_wo_stream[0]]["stream"] = pdf_content_stream
        else:
            collected_streams[False] = {
                "stream": pdf_content_stream,
                "attachment": None,
            }
        return collected_streams

    @staticmethod
    def _check_attachment_split_ids(
        report_sudo: Self,
        has_duplicated_ids: bool,
        res_ids_wo_stream: list[int],
        html_ids: list[int | None],
    ) -> None:
        if (
            not has_duplicated_ids
            and report_sudo.attachment
            and set(res_ids_wo_stream) != set(html_ids)
        ):
            _debug.logic(
                "attachment_split_refused",
                report=report_sudo.id,
                expected=len(res_ids_wo_stream),
                html_ids=len(html_ids),
            )
            raise UserError(
                _(
                    "Report template \u201c%s\u201d has an issue, please contact your administrator. \n\n"
                    "Cannot separate file to save as attachment because the report\u2019s template does not contain the"
                    " attributes 'data-oe-model' and 'data-oe-id' as part of the div with 'article' classname.",
                    report_sudo.name,
                )
            )

    @staticmethod
    def _can_split_pdf(
        has_duplicated_ids: bool,
        res_ids: list[int] | None,
        html_ids: list[int | None],
        res_ids_wo_stream: list[int],
    ) -> bool:
        html_ids_valid = [x for x in html_ids if x is not None]
        return bool(
            not has_duplicated_ids
            and res_ids
            and html_ids_valid
            and len(html_ids_valid) == len(set(html_ids_valid))
            and set(html_ids_valid) == set(res_ids_wo_stream)
        )

    def _collect_split_pdf_streams(
        self,
        bodies: list,
        html_ids: list[int | None],
        res_ids_wo_stream: list[int],
        collected_streams: dict[int | bool, dict[str, Any]],
        render_kwargs: dict[str, Any],
    ) -> None:
        render_bodies = []
        render_res_ids = []
        for body, res_id in zip(bodies, html_ids, strict=True):
            if res_id is not None and res_id in res_ids_wo_stream:
                render_bodies.append(body)
                render_res_ids.append(res_id)
        if not render_bodies:
            return
        pdf_contents = self._render_html_to_pdf(
            render_bodies, _split=True, **render_kwargs
        )
        for pdf_content, res_id in zip(pdf_contents, render_res_ids, strict=True):
            collected_streams[res_id]["stream"] = io.BytesIO(pdf_content)

    def _prepare_pdf_report_attachment_vals_list(
        self, report: Self, streams: dict[int | bool, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        attachment_vals_list = []
        pending = []
        for res_id, stream_data in streams.items():
            if stream_data["attachment"]:
                continue

            if not res_id or not stream_data["stream"]:
                _logger.warning(
                    "These documents were not saved as an attachment because the template of %s doesn't "
                    "have any headers separating different instances of it. If you want it saved, "
                    "please print the documents separately",
                    report.report_name,
                )
                continue
            pending.append((res_id, stream_data))

        for res_id, stream_data in pending:
            attachment_name = stream_data.get("attachment_name")
            if not attachment_name:
                continue

            attachment_vals_list.append(
                {
                    "name": attachment_name,
                    "raw": stream_data["stream"].getvalue(),
                    "res_model": report.model,
                    "res_id": res_id,
                    "type": "binary",
                }
            )
        return attachment_vals_list

    def _is_pdf_rendering_enabled(self) -> bool:
        return not (
            (modules.module.current_test or tools.config["test_enable"])
            and not self.env.context.get("force_report_rendering")
        )

    def _pre_render_qweb_pdf(
        self,
        report_ref: int | str | Any,
        res_ids: list[int] | int | None = None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes | dict[int | bool, dict[str, Any]], str]:
        res_ids, data = self._normalize_render_args(res_ids, data, "pdf")
        report_sudo = self._get_report(report_ref)
        if not self._is_pdf_rendering_enabled():
            return self._render_qweb_html(report_sudo, res_ids, data=data)

        self = self.with_context(webp_as_jpg=True)
        return (
            self._render_qweb_pdf_prepare_streams(report_sudo, data, res_ids=res_ids),
            "pdf",
        )

    def _save_pdf_report_attachments(
        self, report: Self, streams: dict[int | bool, dict[str, Any]]
    ) -> None:
        attachment_vals_list = self._prepare_pdf_report_attachment_vals_list(
            report, streams
        )
        if not attachment_vals_list:
            return
        attachment_names = ", ".join(x["name"] for x in attachment_vals_list)
        _debug.lifecycle(
            "report_attachments_saved",
            report=report.report_name,
            count=len(attachment_vals_list),
        )
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

    def _prepare_corrupt_records_error(
        self, report: Self, error_record_ids: list[int]
    ) -> UserError:
        record_ids = [res_id for res_id in error_record_ids if res_id]
        if not record_ids:
            return self._prepare_merge_pdfs_error()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Problematic record(s)"),
            "res_model": report.model,
            "domain": [("id", "in", record_ids)],
            "views": [(False, "list"), (False, "form")],
        }
        num_errors = len(record_ids)
        if num_errors == 1:
            action.update({"views": [(False, "form")], "res_id": record_ids[0]})
        return RedirectWarning(
            message=_(
                "Odoo is unable to merge the generated PDFs because of "
                "%(num_errors)s corrupted file(s)",
                num_errors=num_errors,
            ),
            action=action,
            button_text=_("View Problematic Record(s)"),
        )

    def _render_qweb_pdf(
        self,
        report_ref: int | str | Any,
        res_ids: list[int] | int | None = None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        res_ids, data = self._normalize_render_args(res_ids, data, "pdf")

        report_sudo = self._get_report(report_ref)

        collected_streams, report_type = self._pre_render_qweb_pdf(
            report_sudo, res_ids=res_ids, data=data
        )
        if report_type != "pdf":
            return collected_streams, report_type

        if (
            not self._has_duplicated_ids(res_ids)
            and report_sudo.attachment
            and not self.env.context.get("report_pdf_no_attachment")
        ):
            self._save_pdf_report_attachments(report_sudo, collected_streams)

        def add_merge_pdfs_error(error: Exception, error_stream: io.BytesIO) -> None:
            error_record_ids.append(stream_to_ids[error_stream])

        stream_to_ids = {
            v["stream"]: k for k, v in collected_streams.items() if v["stream"]
        }
        streams_to_merge = list(stream_to_ids.keys())
        error_record_ids: list[int] = []

        try:
            if len(streams_to_merge) == 1:
                pdf_content = streams_to_merge[0].getvalue()
            else:
                with _debug.perf("merge_pdfs", streams=len(streams_to_merge)):
                    with self._merge_pdfs(
                        streams_to_merge, add_merge_pdfs_error
                    ) as pdf_merged_stream:
                        pdf_content = pdf_merged_stream.getvalue()
        finally:
            if error_record_ids:
                for stream in streams_to_merge:
                    stream.close()

        if error_record_ids:
            raise self._prepare_corrupt_records_error(report_sudo, error_record_ids)

        for stream in streams_to_merge:
            stream.close()

        if res_ids:
            _logger.info(
                '"%s" (%s) generated for %s %s.',
                report_sudo.name,
                report_sudo.report_name,
                report_sudo.model,
                res_ids,
            )

        return pdf_content, "pdf"

    def report_action(
        self,
        docids: Any,
        data: dict[str, Any] | None = None,
        config: bool = True,
    ) -> dict[str, Any]:
        report_action = super().report_action(docids, data=data, config=config)
        if (
            config
            and self.env.is_admin()
            and not self.env.company.external_report_layout_id
            and not self.env.context.get("discard_logo_check")
        ):
            return self._prepare_layout_configurator_action(report_action)
        return report_action

    def _prepare_layout_configurator_action(
        self,
        report_action: dict[str, Any],
        xml_id: str = "web.action_base_document_layout_configurator",
    ) -> dict[str, Any]:
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(xml_id)
        py_ctx = json_loads(action.get("context", {}))
        report_action["close_on_report_download"] = True
        py_ctx["report_action"] = report_action
        action["context"] = py_ctx
        return action
