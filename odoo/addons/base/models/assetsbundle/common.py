import functools
import hashlib
import importlib.metadata
import json
import logging
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Literal, NotRequired, TypedDict

from lxml import etree

import odoo.tools
from odoo.libs.asset_log import get_asset_logger
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger("odoo.addons.base.models.assetsbundle")
_debug = DebugLog(__name__)

_bundle_log = get_asset_logger("bundle")


def _tools_dir() -> Path | None:
    tools_file = getattr(odoo.tools, "__file__", None)
    if not tools_file:
        return None
    return Path(tools_file).resolve().parent


def _pipeline_sources() -> tuple[Path, ...]:
    tools_dir = _tools_dir()
    if tools_dir is None or not __file__:
        _debug.logic("pipeline_sources_unknown", reason="no_file")
        return ()
    package_dir = Path(__file__).resolve().parent
    return (
        package_dir,
        tools_dir / "assets",
        tools_dir / "sass_embedded.py",
        tools_dir.parent / "libs" / "profiling" / "sourcemap_generator.py",
        package_dir.parent.parent / "data" / "rtlcss.json",
    )


_OUTPUT_AFFECTING_NPM_TOOLS = ("sass-embedded", "rtlcss", "esbuild")
_OUTPUT_AFFECTING_PY_TOOLS = ("rjsmin",)


@functools.cache
def _toolchain_versions() -> str:
    root = _repo_root()
    if root is None:
        _debug.logic("toolchain_versions_unknown", reason="no_root")
        return "unknown"
    lock_versions: dict[str, str] = {}
    try:
        packages = json.loads((root / "package-lock.json").read_text())["packages"]
    except OSError, ValueError, KeyError, TypeError:
        packages = {}
        _debug.logic("toolchain_lock_unreadable")
    for name in _OUTPUT_AFFECTING_NPM_TOOLS:
        entry = packages.get(f"node_modules/{name}")
        if isinstance(entry, dict) and entry.get("version"):
            lock_versions[name] = entry["version"]

    parts = []
    for name in _OUTPUT_AFFECTING_NPM_TOOLS:
        version = None
        try:
            installed = json.loads(
                (root / "node_modules" / name / "package.json").read_text()
            )
            version = installed.get("version")
        except OSError, ValueError, AttributeError:
            version = None
        parts.append(f"{name}@{version or lock_versions.get(name) or 'absent'}")
    for name in _OUTPUT_AFFECTING_PY_TOOLS:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = None
        parts.append(f"{name}@{version or 'absent'}")
    _debug.logic("toolchain_versions", versions=";".join(parts))
    return ";".join(parts)


def _repo_root() -> Path | None:
    tools_dir = _tools_dir()
    return None if tools_dir is None else tools_dir.parent.parent


@functools.cache
def _pipeline_fingerprint() -> str:
    with _debug.perf("pipeline_fingerprint") as span:
        digest = hashlib.sha256()
        digest.update(_toolchain_versions().encode())
        digest.update(b"\x00")
        files: list[Path] = []
        for source in _pipeline_sources():
            if source.is_dir():
                files.extend(source.glob("*.py"))
                files.extend(source.glob("js/*.mjs"))
            elif source.is_file():
                files.append(source)
            else:
                _logger.warning(
                    "Asset pipeline source %s does not exist; changes to it will "
                    "not invalidate cached bundles.",
                    source,
                )
                _debug.logic("pipeline_source_missing", source=source.name)
        try:
            for path in sorted(files):
                digest.update(path.name.encode())
                digest.update(path.read_bytes())
        except OSError:
            from odoo import release

            _logger.warning(
                "Could not read the asset pipeline sources to fingerprint them; "
                "falling back to the release version. A pipeline change that does "
                "not touch any asset file will not invalidate cached bundles."
            )
            _debug.logic("pipeline_fingerprint_fallback", reason="unreadable_source")
            return release.version
        if not files:
            from odoo import release

            _debug.logic("pipeline_fingerprint_fallback", reason="no_sources")
            return release.version
        span.set(files=len(files))
        return digest.hexdigest()


def _sourcemap_source_root(asset_url: str) -> str:
    return "/".join(".." for _ in range(len(asset_url.split("/")) - 2)) + "/"


class BundleFileSpec(TypedDict):
    url: str
    filename: str | None
    content: str
    last_modified: NotRequired[float | None]


class NativeModuleData(TypedDict):
    import_map: dict[str, str]
    preload_urls: list[str]
    bridge_import_map: dict[str, str]


class TemplatesBlock(TypedDict):
    type: Literal["templates"]
    templates: list[tuple[etree._Element, str | None, str | None]]


class ExtensionsBlock(TypedDict):
    type: Literal["extensions"]
    extensions: dict[str, list[tuple[etree._Element, str | None]]]


XMLBlock = TemplatesBlock | ExtensionsBlock


class CompileError(RuntimeError):
    pass


class AssetError(Exception):
    pass


class AssetNotFoundError(AssetError):
    pass


class XMLAssetError(AssetError):
    pass


def _run_cli_pipe(argv: Sequence[str], source: str, timeout_s: int) -> str:
    with _debug.perf("cli_pipe", tool=argv[0], source_len=len(source)) as span:
        try:
            proc = Popen(
                argv,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            _debug.logic("cli_pipe_failed", tool=argv[0], reason="not_executable")
            raise CompileError(f"Could not execute command {argv[0]!r}") from None
        try:
            out, err = proc.communicate(input=source, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            _debug.logic(
                "cli_pipe_failed", tool=argv[0], reason="timeout", timeout_s=timeout_s
            )
            raise CompileError(f"{argv[0]!r} timed out after {timeout_s}s") from None
        if proc.returncode:
            cmd_output = out + err
            if not cmd_output:
                cmd_output = f"Process exited with return code {proc.returncode}\n"
            _debug.logic(
                "cli_pipe_failed",
                tool=argv[0],
                reason="returncode",
                returncode=proc.returncode,
                stderr_len=len(err),
            )
            raise CompileError(f"{argv[0]!r}: {cmd_output}")

        span.set(returncode=proc.returncode, out_len=len(out))
        return out


_CSS_STRING_OR_COMMENT = re.compile(
    r"""/\*.*?\*/|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'""",
    re.DOTALL,
)

_SCSS_STRING_OR_COMMENT = re.compile(
    rf"""(?:(?<=\s)|\A)//[^\n]*|{_CSS_STRING_OR_COMMENT.pattern}""",
    re.DOTALL,
)

_URL_FUNCTION = r"""url\(\s*(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^)'"\n]*)\)"""

_SCSS_STATEMENT_SPANS = re.compile(
    rf"""{_URL_FUNCTION}|{_SCSS_STRING_OR_COMMENT.pattern}""",
    re.DOTALL,
)

_PROTECTED_SPAN = "_odoo_protected_span"


def _rewrite_css_outside_strings(
    target: re.Pattern,
    repl: Callable[[re.Match], str],
    text: str,
    tokens: re.Pattern = _CSS_STRING_OR_COMMENT,
) -> str:
    scanner = re.compile(
        f"(?P<{_PROTECTED_SPAN}>(?s:{tokens.pattern}))|{target.pattern}",
        target.flags,
    )

    def _dispatch(match: re.Match) -> str:
        span = match.group(_PROTECTED_SPAN)
        return span if span is not None else repl(match)

    return scanner.sub(_dispatch, text)
