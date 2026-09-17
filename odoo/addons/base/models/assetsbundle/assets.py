import functools
import posixpath
import re
from contextlib import suppress
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lxml import etree
from rjsmin import jsmin as rjsmin

from odoo.libs.debug_log import DebugLog
from odoo.tools import profiler
from odoo.tools.assets.constants import DOTTED_ASSET_EXTENSIONS as EXTENSIONS
from odoo.tools.assets.esbuild import (
    has_nested_template_literal,
    minify_js,
)
from odoo.tools.assets.esm_graph import (
    _parse_odoo_module_header,
    url_to_module_path,
)
from odoo.tools.json import scriptsafe as json
from odoo.tools.misc import file_open, file_path
from odoo.tools.sass_embedded import (
    SassCompileError,
    SassNotFoundError,
    SassProtocolError,
    get_sass_path,
)

if TYPE_CHECKING:
    from .bundle import AssetsBundle
    from odoo.addons.base.models.ir_attachment import IrAttachment
from .common import (
    _CSS_STRING_OR_COMMENT,
    _SCSS_STRING_OR_COMMENT,
    AssetError,
    AssetNotFoundError,
    XMLAssetError,
    _logger,
    _rewrite_css_outside_strings,
    _run_cli_pipe,
)

_debug = DebugLog(__name__)


class WebAsset:
    def __init__(
        self,
        bundle: AssetsBundle,
        inline: str | None = None,
        url: str | None = None,
        filename: str | None = None,
        last_modified: float | None = None,
    ) -> None:
        self.bundle = bundle
        self.inline = inline
        self.url = url
        self._filename = filename
        self._content: str | None = None
        self._ir_attach: IrAttachment | None = None
        self._last_modified = last_modified
        if not inline and not url:
            bundle_name = bundle.name if bundle is not None else "<no bundle>"
            _debug.logic("asset_rejected", bundle=bundle_name, reason="no_source")
            raise ValueError(
                f"An asset should either be inlined or url linked, defined in bundle {bundle_name!r}"
            )

    def generate_error(self, msg: str) -> str:
        msg = f"{msg!r} in file {self.url!r}"
        _logger.error(msg)
        return msg

    @functools.cached_property
    def unique_descriptor(self) -> str:
        return f"{self.url or self.inline},{self.last_modified}"

    @functools.cached_property
    def name(self) -> str:
        return "<inline asset>" if self.inline else self.url

    def _load_attachment(self) -> None:
        if not (self.inline or self._filename or self._ir_attach):
            try:
                self._ir_attach = (
                    self.bundle.env["ir.attachment"]
                    .sudo()
                    ._get_serve_attachment(self.url)
                )
                self._ir_attach.check_singleton()
            except ValueError:
                _debug.logic("attachment_asset_missing", name=self.name, url=self.url)
                raise AssetNotFoundError(f"Could not find {self.name}") from None
            _debug.logic(
                "attachment_asset_loaded", name=self.name, attachment=self._ir_attach.id
            )

    @property
    def last_modified(self) -> float | int:
        if self._last_modified is None:
            with suppress(AssetNotFoundError):
                self._load_attachment()
            if self._filename:
                with suppress(OSError):
                    self._last_modified = Path(self._filename).stat().st_mtime
            elif self._ir_attach:
                self._last_modified = self._ir_attach.write_date.replace(
                    tzinfo=UTC
                ).timestamp()
            if self._last_modified is None:
                self._last_modified = -1
                _debug.logic("last_modified_unknown", name=self.name)
        return self._last_modified

    @property
    def content(self) -> str:
        if self._content is None:
            self._content = self._raw_source()
        return self._content

    def _raw_source(self) -> str:
        return self.inline or self._get_content()

    def _get_content(self) -> str:
        try:
            self._load_attachment()
            if self._filename:
                with file_open(self._filename, "rb", filter_ext=EXTENSIONS) as fp:
                    return fp.read().decode("utf-8")
            else:
                return self._ir_attach.raw.decode()
        except UnicodeDecodeError:
            _debug.logic("asset_not_utf8", name=self.name, url=self.url)
            raise AssetError(f"{self.name} is not utf-8 encoded.") from None
        except OSError:
            _debug.logic("asset_missing", name=self.name, url=self.url)
            raise AssetNotFoundError(f"File {self.name} does not exist.") from None
        except AssetError:
            raise
        except ValueError as e:
            _debug.logic("asset_content_invalid", name=self.name, url=self.url)
            raise AssetError(f"Could not get content for {self.name}.") from e

    def minify(self) -> str:
        return self.content

    def with_header(self, content: str | None = None) -> str:
        if content is None:
            content = self.content
        return f"\n/* {self.name} */\n{content}"


class JavascriptAsset(WebAsset):
    _HEADER_LINE_COUNT = 5

    @functools.cached_property
    def parsed_header(self) -> re.Match[str] | None:
        return _parse_odoo_module_header(self.raw_content)

    def generate_error(self, msg: str) -> str:
        msg = super().generate_error(msg)
        return f"console.error({json.dumps(msg)});"

    @functools.cached_property
    def is_native(self) -> bool:
        header = self.parsed_header
        return bool(header and header["native"])

    @functools.cached_property
    def module_path(self) -> str:
        return url_to_module_path(self.url)

    @property
    def raw_content(self) -> str:
        # the name tools/assets' NativeModuleLike protocol reads; a script's
        # content is never rewritten, so it is the content itself
        return self.content

    def minify(self) -> str:
        content = self.content
        if not has_nested_template_literal(content):
            with _debug.perf("js_minify", name=self.name, tool="rjsmin"):
                return self.with_header(rjsmin(content, keep_bang_comments=True))
        with _debug.perf("js_minify", name=self.name, tool="esbuild") as span:
            minified = minify_js(content, label=self.url or self.name)
            span.set(minified=minified is not None)
        return self.with_header(minified if minified is not None else content)

    def _get_content(self) -> str:
        try:
            return super()._get_content()
        except AssetError as e:
            _debug.logic("js_asset_error_inlined", name=self.name, url=self.url)
            return self.generate_error(str(e))

    def with_header(self, content: str | None = None, minimal: bool = True) -> str:
        if minimal:
            return super().with_header(content)

        line_count = content.count("\n")
        lines = [
            f"Filepath: {self.url}",
            f"Lines: {line_count}",
        ]
        length = max(map(len, lines))
        return "\n".join(
            [
                "",
                "/" + "*" * (length + 5),
                *(f"*  {line:<{length}}  *" for line in lines),
                "*" * (length + 5) + "/",
                content,
            ]
        )


class XMLAsset(WebAsset):
    @property
    def _parsed_root(self) -> etree._Element:
        result = self._parse_result
        if isinstance(result, XMLAssetError):
            raise result
        return result

    @functools.cached_property
    def _parse_result(self) -> etree._Element | XMLAssetError:
        try:
            raw = self._raw_source()
        except AssetError as e:
            _debug.logic("xml_asset_unreadable", name=self.name, url=self.url)
            return self._prepare_asset_error(str(e))
        parser = etree.XMLParser(
            ns_clean=True, remove_comments=True, resolve_entities=False
        )
        try:
            return etree.fromstring(raw.encode("utf-8"), parser=parser)
        except etree.XMLSyntaxError as e:
            _debug.logic(
                "xml_asset_invalid", name=self.name, url=self.url, line=e.lineno
            )
            return self._prepare_asset_error(f"Invalid XML template: {e.msg}")

    @functools.cached_property
    def template_elements(self) -> list[etree._Element]:
        root = self._parsed_root
        if root.tag in ("templates", "template", "odoo"):
            elements = [el for el in root if isinstance(el.tag, str)]
            _debug.perf.count(
                "xml_templates_parsed", name=self.name, elements=len(elements)
            )
            return elements
        _debug.logic("xml_single_root", name=self.name, tag=root.tag)
        return [root]

    def _prepare_asset_error(self, msg: str) -> XMLAssetError:
        return XMLAssetError(super().generate_error(msg))


class StylesheetAsset(WebAsset):
    rx_import = re.compile(
        r"""@import\s+(?P<q>'|")(?!'|"|/|https?://)(?P<path>[^'"]*)(?P=q)"""
    )
    rx_url = re.compile(
        r"""url\s*\(\s*(?P<q>['"]|)"""
        r"""(?!['"]|/|https?://|data:|\#\{str|\#(?!\{))"""
        r"""(?P<body>[^'")\s]*)(?P=q)""",
    )
    rx_charset = re.compile(r'(@charset "[^"]+";)')
    _CSS_TOKEN_RE = _CSS_STRING_OR_COMMENT
    _SOURCE_TOKEN_RE = _CSS_STRING_OR_COMMENT
    _IDENT_CHAR = re.compile(r"[\w-]")
    # plain CSS resolves @import here; a preprocessor resolves it on its own
    # load paths, so the rewrite would break every library import
    _REWRITES_IMPORTS = True
    id = "0"

    def __init__(
        self,
        *args: Any,
        rtl: bool = False,
        autoprefix: bool = False,
        split_id: str = "0",
        **kw: Any,
    ) -> None:
        self.rtl = rtl
        self.autoprefix = autoprefix
        self.id = split_id
        self.errors: list[str] = []
        super().__init__(*args, **kw)

    @functools.cached_property
    def unique_descriptor(self) -> str:
        direction = (self.rtl and "rtl") or "ltr"
        autoprefixed = (self.autoprefix and "autoprefixed") or ""
        return (
            f"{self.url or self.inline},{self.last_modified},{direction},{autoprefixed}"
        )

    def _get_content(self) -> str:
        try:
            content = super()._get_content()
            web_dir = posixpath.dirname(self.url)

            def _rewrite_import(match: re.Match[str]) -> str:
                q = match.group("q")
                return f"@import {q}{web_dir}/{match.group('path')}{q}"

            if self._REWRITES_IMPORTS:
                content = _rewrite_css_outside_strings(
                    self.rx_import, _rewrite_import, content, self._SOURCE_TOKEN_RE
                )

            def _rewrite_url(match: re.Match[str]) -> str:
                q = match.group("q")
                body = match.group("body")
                if not body:
                    return match.group(0)
                normalised = posixpath.normpath(f"{web_dir}/{body}")
                return f"url({q}{normalised}{q}"

            content = _rewrite_css_outside_strings(
                self.rx_url, _rewrite_url, content, self._SOURCE_TOKEN_RE
            )

            return self.rx_charset.sub("", content)
        except AssetError as e:
            self.errors.append(str(e))
            _debug.logic("stylesheet_content_failed", name=self.name, url=self.url)
            return ""

    def get_source(self) -> str:
        return f"/*! odoo-split:{self.id} */\n{self._raw_source()}"

    @classmethod
    def _minify_css_body(cls, content: str) -> str:
        content = content.replace("\x00", "")

        protected: list[str] = []

        def _mask(match: re.Match[str]) -> str:
            token = match.group()
            if token[0] in "\"'" or token.startswith("/*!"):
                protected.append(token)
                return f"\x00{len(protected) - 1}\x00"
            before = content[match.start() - 1 : match.start()]
            after = content[match.end() : match.end() + 1]
            if cls._IDENT_CHAR.match(before) and cls._IDENT_CHAR.match(after):
                return " "
            return ""

        masked = cls._CSS_TOKEN_RE.sub(_mask, content)
        masked = re.sub(r"\s+", " ", masked)
        masked = re.sub(r" *([{}]) *", r"\1", masked)
        _debug.perf.count("css_minified", chars=len(content), minified=len(masked))
        return re.sub(r"\x00(\d+)\x00", lambda m: protected[int(m.group(1))], masked)

    def minify(self) -> str:
        if self.bundle.is_debug_assets:
            return self.with_header(self.content)
        return self.with_header(self._minify_css_body(self.content))


class PreprocessedCSS(StylesheetAsset):
    _REWRITES_IMPORTS = False
    _SOURCE_TOKEN_RE = _SCSS_STRING_OR_COMMENT

    _COMPILE_TIMEOUT_S: int = 180

    @property
    def output_style(self) -> str:
        return (
            "expanded" if self.bundle and self.bundle.is_debug_assets else "compressed"
        )

    def get_command(self) -> list[str]:
        raise NotImplementedError

    def compile(self, source: str) -> str:
        return _run_cli_pipe(self.get_command(), source, self._COMPILE_TIMEOUT_S)


class ScssStylesheetAsset(PreprocessedCSS):
    @classmethod
    def for_inline_compile(
        cls, source: str = "// inline compile"
    ) -> ScssStylesheetAsset:
        return cls(None, inline=source)

    _embedded_fallback_warned = False

    @classmethod
    def _warn_embedded_fallback(cls, exc: Exception) -> None:
        if cls._embedded_fallback_warned:
            _logger.debug("Dart Sass embedded unavailable, using CLI", exc_info=exc)
            return
        ScssStylesheetAsset._embedded_fallback_warned = True
        _debug.lifecycle("sass_embedded_fallback_warned", error=type(exc).__name__)
        _logger.warning(
            "Embedded Dart Sass unavailable (%s); falling back to the Dart Sass "
            "CLI for every SCSS compile. The CLI path is markedly slower (a "
            "per-bundle subprocess, up to %ss) — install/repair sass-embedded to "
            "restore the fast path. This warning fires once per process.",
            exc,
            cls._COMPILE_TIMEOUT_S,
        )

    @property
    def bootstrap_path(self) -> str:
        return file_path("web/static/lib/bootstrap/scss")

    _sass_syntax = "scss"

    def minify(self) -> str:
        return self.with_header()

    def compile(self, source: str) -> str:
        import odoo.addons

        try:
            from odoo.tools.sass_embedded import (
                OdooSassImporter,
                get_sass_compiler,
            )

            compiler = get_sass_compiler()
            profiler.force_hook()
            with _debug.perf(
                "sass_embedded", chars=len(source), style=self.output_style
            ):
                return compiler.compile_string(
                    source,
                    syntax=self._sass_syntax,
                    importers=[OdooSassImporter(self.bootstrap_path)],
                    load_paths=[self.bootstrap_path, *odoo.addons.__path__],
                    style=self.output_style,
                    quiet_deps=True,
                )
        except SassCompileError:
            raise
        except SassNotFoundError:
            raise
        except (SassProtocolError, OSError) as exc:
            # a transport failure of the embedded protocol; anything else is a
            # bug in this code and must surface, not run the slow path forever
            self._warn_embedded_fallback(exc)
            _debug.logic("sass_fallback_cli", error=type(exc).__name__)
            from odoo.tools.sass_embedded import close_sass_compiler

            close_sass_compiler()

        with _debug.perf("sass_cli", chars=len(source), style=self.output_style):
            return super().compile(source)

    def get_command(self) -> list[str]:
        import odoo.addons

        sass = get_sass_path()
        if sass is None:
            _debug.logic("sass_cli_missing", syntax=self._sass_syntax)
            raise SassNotFoundError(
                "Dart Sass not found. It is a required dependency of this fork: "
                "run `npm install` in the Odoo root (declared in package.json) "
                "or install a `sass` binary on PATH."
            )
        load_paths = [self.bootstrap_path, *odoo.addons.__path__]
        cmd = [
            sass,
            "--stdin",
            "--indented" if self._sass_syntax == "indented" else "--no-indented",
            "--no-source-map",
            "--no-charset",
            "--style",
            self.output_style,
            "--quiet-deps",
            "--silence-deprecation=import",
            "--silence-deprecation=global-builtin",
            "--silence-deprecation=if-function",
            "--silence-deprecation=duplicate-var-flags",
            "--silence-deprecation=color-functions",
        ]
        for path in load_paths:
            cmd.extend(["--load-path", path])
        return cmd


class SassStylesheetAsset(ScssStylesheetAsset):
    _sass_syntax = "indented"
