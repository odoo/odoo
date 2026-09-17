import functools
import hashlib
import os
import re
import shutil
import subprocess
import threading
from collections import OrderedDict
from collections.abc import Callable, Sequence
from contextlib import suppress
from pathlib import Path
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING

import odoo
from odoo.libs.debug_log import DebugLog
from odoo.tools import misc
from odoo.tools.config import config
from odoo.tools.misc import file_path
from odoo.tools.sass_embedded import SassCompileError

if TYPE_CHECKING:
    from odoo.libs.profiling import SourceMapGenerator

    from .bundle import AssetsBundle
from .assets import PreprocessedCSS, StylesheetAsset
from .common import (
    _SCSS_STATEMENT_SPANS,
    CompileError,
    _logger,
    _rewrite_css_outside_strings,
    _run_cli_pipe,
)

_debug = DebugLog(__name__)


@functools.cache
def _rtlcss_bin() -> str:
    names = ("rtlcss.cmd", "rtlcss") if os.name == "nt" else ("rtlcss",)
    for name in names:
        with suppress(OSError):
            return misc.get_executable_path(name)
    node_bin = str(Path(odoo.__path__[0]).parent / "node_modules" / ".bin")
    for name in names:
        if found := shutil.which(name, path=node_bin):
            return found
    return "rtlcss"


@functools.cache
def _is_rtlcss_available() -> bool:
    try:
        check = Popen([_rtlcss_bin(), "--version"], stdout=PIPE, stderr=PIPE)
        check.communicate(timeout=10)
    except OSError:
        _logger.warning(
            "rtlcss is required for RTL CSS support. Install with: npm install -g rtlcss"
        )
        _debug.logic("rtlcss_unavailable", reason="not_found")
        return False
    except subprocess.TimeoutExpired:
        check.kill()
        check.communicate()
        _logger.warning("rtlcss --version probe timed out; disabling RTL support")
        _debug.logic("rtlcss_unavailable", reason="timeout")
        return False
    if check.returncode:
        _logger.warning(
            "rtlcss --version exited with %s; disabling RTL support",
            check.returncode,
        )
        _debug.logic("rtlcss_unavailable", reason="exit", returncode=check.returncode)
        return False
    _debug.logic("rtlcss_available", bin=_rtlcss_bin())
    return True


@functools.cache
def _rtlcss_config_path() -> str:
    return file_path("base/data/rtlcss.json")


class CssPipeline:
    rx_preprocess_imports = re.compile(
        r"""@import\s*['"](?P<ref>[^'"]+)['"](?P<tail>[^;{]*;?)"""
    )
    rx_css_split = re.compile(r"/\*! odoo-split:([a-f0-9-]+) \*/")
    rx_css_import = re.compile(r"(@import[^;{]+;?)")

    _RTLCSS_TIMEOUT_S: int = 60

    _CSS_ERROR_HEADER = "\n\n/* ## CSS error message ##*/"

    def __init__(self, bundle: AssetsBundle) -> None:
        self._bundle = bundle
        self._rendered_assets: list[StylesheetAsset] = []

    def preprocess(self) -> str:
        bundle = self._bundle
        bundle.css_errors.clear()
        self._rendered_assets = []
        if not bundle.stylesheets:
            _debug.logic("css_preprocess_skipped", bundle=self._bundle.name)
            return ""

        for asset in bundle.stylesheets:
            asset.errors.clear()
            asset._content = None

        compiled = ""
        assets = [a for a in bundle.stylesheets if isinstance(a, PreprocessedCSS)]
        _logger.debug(
            "Bundle %r: preprocessing %s stylesheet(s), %s preprocessed, rtl=%s",
            self._bundle.name,
            len(bundle.stylesheets),
            len(assets),
            bundle.rtl,
        )
        if assets:
            dialects = {type(a) for a in assets}
            if len(dialects) != 1:
                msg = (
                    f"Bundle {bundle.name!r} mixes preprocessed-CSS dialects "
                    f"{sorted(t.__name__ for t in dialects)}: they compile as one "
                    "document and no compiler reads two syntaxes at once. Split "
                    "them into separate bundles."
                )
                _logger.warning(msg)
                bundle.css_errors.append(msg)
                _debug.logic(
                    "css_dialects_mixed", bundle=bundle.name, dialects=len(dialects)
                )
                return ""
            source = "\n".join(asset.get_source() for asset in assets)
            _logger.debug(
                "Bundle %r: compiling %s lines of %s from %s file(s)",
                self._bundle.name,
                source.count("\n") + 1,
                type(assets[0]).__name__,
                len(assets),
            )
            with _debug.perf(
                "css_compile",
                bundle=self._bundle.name,
                dialect=type(assets[0]).__name__,
                assets=len(assets),
                lines=source.count("\n") + 1,
            ) as span:
                compiled = self.compile_css(assets[0], source)
                span.set(compiled=len(compiled))

        if bundle.rtl and not bundle.css_errors:
            plain_css_assets = [
                asset
                for asset in bundle.stylesheets
                if not isinstance(asset, PreprocessedCSS)
            ]
            compiled += "\n".join(asset.get_source() for asset in plain_css_assets)
            _debug.pipeline(
                "css_rtl_conversion",
                bundle=self._bundle.name,
                plain=len(plain_css_assets),
                chars=len(compiled),
            )
            compiled = self.convert_css_to_rtl(compiled)

        compile_failed = bool(bundle.css_errors)
        if compile_failed:
            for asset in bundle.stylesheets:
                bundle.css_errors.extend(asset.errors)
            _debug.logic(
                "css_compile_failed", bundle=bundle.name, errors=len(bundle.css_errors)
            )
            return ""

        fragments = self.rx_css_split.split(compiled)
        at_rules = fragments.pop(0)
        rendered = list(bundle.stylesheets)
        if at_rules:
            rendered.insert(0, StylesheetAsset(bundle, inline=at_rules))
        self._rendered_assets = rendered
        _debug.pipeline(
            "css_split",
            bundle=self._bundle.name,
            fragments=len(fragments) // 2,
            at_rules=len(at_rules),
            rendered=len(rendered),
        )

        assets_by_id = {a.id: a for a in bundle.stylesheets}
        marker_iter = iter(fragments)
        for asset_id, content in zip(marker_iter, marker_iter, strict=True):
            asset = assets_by_id.get(asset_id)
            if asset is None:
                _debug.logic(
                    "css_split_out_of_sync", bundle=self._bundle.name, asset_id=asset_id
                )
                raise RuntimeError(
                    f"CSS asset {asset_id!r} not found in stylesheets — "
                    "compiled output is out of sync with the asset list"
                )
            asset._content = content

        if bundle.autoprefix:
            with _debug.perf(
                "css_autoprefix",
                bundle=self._bundle.name,
                assets=len(bundle.stylesheets),
            ):
                for asset in bundle.stylesheets:
                    asset._content = self._autoprefix_css(asset.content)

        with _debug.perf(
            "css_minify", bundle=self._bundle.name, assets=len(self._rendered_assets)
        ) as span:
            bundle_css = "\n".join(asset.minify() for asset in self._rendered_assets)
            span.set(bytes=len(bundle_css))
        for asset in bundle.stylesheets:
            bundle.css_errors.extend(asset.errors)
        _debug.pipeline(
            "css_preprocessed",
            bundle=self._bundle.name,
            bytes=len(bundle_css),
            errors=len(bundle.css_errors),
        )
        return bundle_css

    def sourcemap_bundle(
        self,
        generator: SourceMapGenerator,
        sourcemap_url: str,
        content_import_rules: str,
    ) -> str:
        content_bundle_list = [content_import_rules]
        content_line_count = content_import_rules.count("\n") + 1
        for asset in self._rendered_assets:
            if asset.content:
                content = asset.with_header(asset.content)
                if asset.url:
                    generator.add_source(asset.url, content, content_line_count)
                content = _rewrite_css_outside_strings(
                    self.rx_css_import,
                    lambda matchobj: f"/* {matchobj.group(0)} */",
                    content,
                )
                content_bundle_list.append(content)
                content_line_count += content.count("\n") + 1
        _debug.pipeline(
            "css_sourcemap_bundle",
            bundle=self._bundle.name,
            assets=len(self._rendered_assets),
            parts=len(content_bundle_list),
            lines=content_line_count,
        )
        return (
            "\n".join(content_bundle_list)
            + f"\n/*# sourceMappingURL={sourcemap_url} */"
        )

    def hoist_import_rules(self, css: str) -> tuple[list[str], str]:
        import_rules: list[str] = []

        def _hoist(match: re.Match) -> str:
            import_rules.append(match.group(0))
            return ""

        remainder = _rewrite_css_outside_strings(self.rx_css_import, _hoist, css)
        _debug.perf.count(
            "css_imports_hoisted", bundle=self._bundle.name, imports=len(import_rules)
        )
        return import_rules, remainder

    def compile_css(self, asset: PreprocessedCSS, source: str) -> str:
        bundle = self._bundle
        seen_imports: set[str] = set()

        def sanitize_import(matchobj: re.Match) -> str:
            ref = matchobj.group("ref")
            line = f'@import "{ref}"{matchobj.group("tail")}'
            if line in seen_imports:
                _debug.logic(
                    "scss_import_deduplicated", bundle=self._bundle.name, ref=ref
                )
                return ""
            seen_imports.add(line)
            if "." in ref or ref.startswith((".", "/", "~")):
                msg = (
                    f"Local import {ref!r} is forbidden for security reasons."
                    " Remove @import statements from custom files;"
                    " in Odoo, import files via the assets bundle instead."
                )
                _logger.warning(msg)
                bundle.css_errors.append(msg)
                _debug.logic("scss_import_forbidden", bundle=self._bundle.name, ref=ref)
                return ""
            return line

        source = _rewrite_css_outside_strings(
            self.rx_preprocess_imports,
            sanitize_import,
            source,
            _SCSS_STATEMENT_SPANS,
        )

        _debug.perf.count(
            "scss_imports_sanitized",
            bundle=self._bundle.name,
            imports=len(seen_imports),
        )
        try:
            return self._memoized_transform(
                ("compile", type(asset).__name__, asset.output_style),
                source,
                lambda src: asset.compile(src).strip(),
            )
        except (CompileError, SassCompileError) as e:
            error = self._format_compiler_error(str(e), source)
            _logger.warning(error)
            bundle.css_errors.append(error)
            _debug.logic(
                "scss_compile_failed", bundle=self._bundle.name, error=type(e).__name__
            )
            return ""

    _compiled_cache: OrderedDict[tuple, str] = OrderedDict()
    _COMPILED_CACHE_SIZE = 32
    _compiled_cache_lock = threading.Lock()

    @classmethod
    def _memoized_transform(
        cls, key: tuple, source: str, transform: Callable[[str], str]
    ) -> str:
        if config["dev_mode"]:
            _debug.logic("css_cache", stage=key[0], hit=False, reason="dev_mode")
            return transform(source)
        cache = cls._compiled_cache
        key = (*key, hashlib.sha256(source.encode()).hexdigest())
        with cls._compiled_cache_lock:
            if (hit := cache.get(key)) is not None:
                cache.move_to_end(key)
                _logger.debug("CSS %s: cache hit, %s chars", key[0], len(hit))
                _debug.logic("css_cache", stage=key[0], hit=True, chars=len(hit))
                return hit
        _logger.debug("CSS %s: cache miss, transforming %s chars", key[0], len(source))
        with _debug.perf("css_transform", stage=key[0], chars=len(source)):
            result = transform(source)
        with cls._compiled_cache_lock:
            cache[key] = result
            cache.move_to_end(key)
            evicted = 0  # debuglog
            while len(cache) > cls._COMPILED_CACHE_SIZE:
                cache.popitem(last=False)
                evicted += 1  # debuglog
        _debug.lifecycle(
            "css_cache_stored", stage=key[0], size=len(cache), evicted=evicted
        )
        return result

    _RX_APPEARANCE = re.compile(
        r"(?<=[{;\s])appearance\s*:\s*(?P<value>[\w-]+)(?P<important>\s*!important)?"
    )

    @classmethod
    def _autoprefix_css(cls, source: str) -> str:

        def _prefix(match: re.Match) -> str:
            value = match.group("value")
            important = match.group("important") or ""
            return (
                f"-webkit-appearance:{value}{important};"
                f"-moz-appearance:{value}{important};"
                f"appearance:{value}{important}"
            )

        return _rewrite_css_outside_strings(cls._RX_APPEARANCE, _prefix, source.strip())

    def convert_css_to_rtl(self, source: str) -> str:
        if not _is_rtlcss_available():
            _logger.debug(
                "rtlcss unavailable, serving %r left-to-right", self._bundle.name
            )
            _debug.logic("rtl_skipped", bundle=self._bundle.name, reason="unavailable")
            return source

        cmd = [_rtlcss_bin(), "-c", _rtlcss_config_path(), "-"]

        def _transform(src: str) -> str:
            out = _run_cli_pipe(cmd, src, self._RTLCSS_TIMEOUT_S).strip()
            if src.strip() and not out:
                _debug.logic(
                    "rtl_empty_output", bundle=self._bundle.name, chars=len(src)
                )
                raise CompileError("rtlcss: error processing payload\n")
            return out

        try:
            return self._memoized_transform(("rtlcss",), source, _transform)
        except CompileError as e:
            error = str(e)
            if "error processing payload" not in error:
                error = self._format_compiler_error(error)
            _logger.warning("%s", error)
            self._bundle.css_errors.append(error)
            _debug.logic("rtl_failed", bundle=self._bundle.name, chars=len(source))
            return ""

    _RX_ERROR_TRACE = re.compile(r"^\s*-?\s*(?P<line>\d+):\d+\s+\S", re.MULTILINE)
    _RX_ERROR_GUTTER = re.compile(r"^\s*(?P<line>\d+)\s*\u2502", re.MULTILINE)

    def _locate_source_line(self, source: str, line_no: int) -> str:
        """Name the asset that contributed line `line_no` of the compiled source.

        The compiler numbers its errors against the whole concatenated document,
        which is hundreds of files and tens of thousands of lines, so the number
        alone points at nothing and the caller is left reading a list of every
        file in the bundle. `get_source` opens each asset with an `odoo-split`
        marker, so the nearest marker at or above the line names the owner and
        the distance down to the line is the line number within that file.
        """
        lines = source.split("\n")
        if not 1 <= line_no <= len(lines):
            _debug.logic("css_error_line_out_of_range", line=line_no, lines=len(lines))
            return ""
        assets_by_id = {asset.id: asset for asset in self._bundle.stylesheets}
        for index in range(line_no - 1, -1, -1):
            if match := self.rx_css_split.search(lines[index]):  # noqa: E8507  a regex, not the ORM
                asset = assets_by_id.get(match.group(1))
                url = (asset.url or "<inline sass>") if asset else "<unknown asset>"
                _debug.logic(
                    "css_error_located",
                    url=url,
                    line=line_no - index - 1,
                    known=asset is not None,
                )
                return (
                    f"\nThe failing line is {url} line {line_no - index - 1}:"
                    f"\n    {lines[line_no - 1].strip()}\n"
                )
        return ""

    def _format_compiler_error(self, stderr: str, source: str = "") -> str:
        bundle = self._bundle
        error = stderr.split("Load paths", maxsplit=1)[0].replace(
            "  Use --trace for backtrace.", ""
        )
        if source and (
            match := self._RX_ERROR_TRACE.search(stderr)
            or self._RX_ERROR_GUTTER.search(stderr)
        ):
            error += self._locate_source_line(source, int(match.group("line")))
        _debug.logic(
            "css_compiler_error_formatted",
            bundle=self._bundle.name,
            located=bool(source and match),
        )
        error += f"This error occurred while compiling the bundle {bundle.name!r} containing:"
        for asset in bundle.stylesheets:
            if isinstance(asset, PreprocessedCSS):
                error += f"\n    - {asset.url or '<inline sass>'}"
        return error

    @classmethod
    def _render_css_error_banner(
        cls, css_errors: Sequence[str], previous_css: str
    ) -> str:
        error_message = (
            "\n".join(css_errors)
            .replace("\\", "\\\\")
            .replace('"', r"\"")
            .replace("\n", r"\A")
            .replace("*", r"\*")
        )
        _logger.debug(
            "Serving the previous stylesheet behind a CSS error banner (%s error(s), "
            "%s chars carried over)",
            len(css_errors),
            len(previous_css),
        )
        carried_over = previous_css.split(cls._CSS_ERROR_HEADER, maxsplit=1)[0]
        _debug.logic(
            "css_error_banner_rendered",
            errors=len(css_errors),
            carried=len(carried_over),
        )
        banner = f"""

body::before {{
  font-weight: bold;
  content: "A css error occurred, using an old style to render this page";
  position: fixed;
  left: 0;
  bottom: 0;
  z-index: 100000000000;
  background-color: #C00;
  color: #DDD;
}}

css_error_message {{
  content: "{error_message}";
}}
"""
        return cls._CSS_ERROR_HEADER.join([carried_over, banner])
