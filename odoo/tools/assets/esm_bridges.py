import logging
import posixpath
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import quote

from odoo import modules
from odoo.api import SUPERUSER_ID, Environment
from odoo.fields import Domain
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.libs.hashing import cache_hash
from odoo.tools import config
from odoo.tools.assets.constants import ESM_BRIDGE_REFRESH_DAYS
from odoo.tools.assets.esm_graph import (
    _IMPORT_ANY_RE,
    _JS_OPAQUE_RE,
    _bridge_shim_source,
    _BridgeExportResolver,
    _extract_esm_exports,
    _resolve_export_specifier,
    _strict_stub_source,
)
from odoo.tools.assets.esm_lexer import lex_module
from odoo.tools.assets.esm_registry import esm_registry, external_libs

__all__ = ["BridgeShimManager", "NativeModuleLike"]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_bridge_log = get_asset_logger("bridge")


def _rw_escalation_expected() -> bool:
    return bool(modules.module.current_test) or config["test_enable"]


class NativeModuleLike(Protocol):
    @property
    def module_path(self) -> str:
        pass

    @property
    def raw_content(self) -> str:
        pass


class BridgeShimManager:
    def __init__(
        self,
        env: Environment,
        bundle_name: str,
        native_modules: Sequence[NativeModuleLike],
    ) -> None:
        self.env = env
        self.bundle_name = bundle_name
        self.native_modules = native_modules

    def _update_reused_shim_dates(self, existing) -> None:
        if not existing:
            return
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            days=ESM_BRIDGE_REFRESH_DAYS
        )
        stale = [
            row.id for row in existing if row.write_date and row.write_date < cutoff
        ]
        if not stale:
            return
        cr: Any = self.env.cr
        if cr.readonly:
            log_event(
                _bridge_log,
                logging.DEBUG,
                "bridges_refresh_skipped_readonly",
                bundle=self.bundle_name,
                rows=len(stale),
            )
            return
        cr.execute(
            "UPDATE ir_attachment SET write_date = now() at time zone 'UTC'"
            " WHERE id = ANY(%s)",
            (stale,),
        )
        self.env["ir.attachment"].browse(stale).invalidate_recordset(["write_date"])
        log_event(
            _bridge_log,
            logging.DEBUG,
            "bridges_refreshed",
            bundle=self.bundle_name,
            rows=len(stale),
        )

    def _persist_bridge_shims(
        self,
        shims_by_spec: dict[str, str],
    ) -> dict[str, str]:
        if not shims_by_spec:
            return {}
        url_by_spec: dict[str, str] = {}
        content_by_url: dict[str, str] = {}
        for spec, content in shims_by_spec.items():
            content_hash = cache_hash(content.encode("utf-8"))[:32]
            url = f"/web/assets/esm/bridges/{content_hash}.js"
            url_by_spec[spec] = url
            content_by_url[url] = content
        Attachment = self.env["ir.attachment"].sudo()
        existing = Attachment.search_fetch(
            Attachment._get_domain_generated_assets()
            & Domain("url", "in", list(content_by_url)),
            ["url", "write_date"],
        )
        existing_urls = set(existing.mapped("url"))
        _debug.logic(
            "esm_bridges.shims_persisting",
            bundle=self.bundle_name,
            shims=len(shims_by_spec),
            urls=len(content_by_url),
            reused=len(existing_urls),
        )
        self._update_reused_shim_dates(existing)
        to_create = [
            Attachment._prepare_generated_asset_vals(
                name=url.rsplit("/", 1)[-1],
                mimetype="text/javascript",
                raw=content.encode("utf-8"),
                url=url,
            )
            for url, content in content_by_url.items()
            if url not in existing_urls
        ]
        if not to_create:
            return url_by_spec

        from odoo.http import request

        outside_request = not request
        if outside_request:
            self.env["ir.attachment"].with_user(SUPERUSER_ID).create(to_create)
        if outside_request or self._persist_bridges_via_rw_cursor(to_create):
            log_event(
                _bridge_log,
                logging.INFO,
                "bridges_persisted",
                bundle=self.bundle_name,
                new=len(to_create),
                reused=len(content_by_url) - len(to_create),
                total=len(url_by_spec),
            )
            return url_by_spec

        missing_urls = {item["url"] for item in to_create}
        log_event(
            _bridge_log,
            logging.DEBUG if _rw_escalation_expected() else logging.WARNING,
            "bridges_inlined_no_rw_cursor",
            bundle=self.bundle_name,
            inline=len(missing_urls),
            reused=len(content_by_url) - len(missing_urls),
            total=len(url_by_spec),
        )
        return {
            spec: (
                url
                if url not in missing_urls
                else f"data:text/javascript;charset=utf-8,{quote(content_by_url[url])}"
            )
            for spec, url in url_by_spec.items()
        }

    def _persist_bridges_via_rw_cursor(self, to_create: list[dict]) -> bool:
        try:
            with self.env.registry.cursor(readonly=False) as rw_cr:
                rw_env = Environment(rw_cr, SUPERUSER_ID, {})
                rw_env["ir.attachment"].create(to_create)
        except Exception:
            expected = _rw_escalation_expected()
            _logger.log(
                logging.DEBUG if expected else logging.WARNING,
                "Bridge attachment escalation to a read-write cursor "
                "failed; falling back to data: URIs",
                exc_info=not expected,
            )
            return False
        return True

    def _prepare_parent_self_bridge(self) -> dict[str, str]:
        source_map: dict[str, str] = {
            a.module_path: a.raw_content for a in self.native_modules
        }
        exports_cache: dict[str, set[str]] = {}

        shims_by_spec: dict[str, str] = {}
        skip_legacy_tests = self.bundle_name in esm_registry().import_map_includes
        skipped_tests = 0  # debuglog
        for asset in self.native_modules:
            specifier = asset.module_path
            if not specifier.startswith("@"):
                continue
            if skip_legacy_tests and "/static/tests/" in (
                getattr(asset, "url", None) or ""
            ):
                skipped_tests += 1  # debuglog
                continue
            src = asset.raw_content
            names, _ = _extract_esm_exports(
                src,
                source_map=source_map,
                importing_specifier=specifier,
                importing_url=getattr(asset, "url", None) or None,
                _exports_cache=exports_cache,
            )
            shim, _star = _bridge_shim_source(
                specifier, {"__default__"}, names, has_default=False
            )
            shims_by_spec[specifier] = shim

        bridges = self._persist_bridge_shims(shims_by_spec)
        log_event(
            _bridge_log,
            logging.DEBUG,
            "parent_self_bridge",
            bundle=self.bundle_name,
            shims=len(bridges),
        )
        _debug.pipeline(
            "esm_bridges.parent_self_bridge",
            bundle=self.bundle_name,
            modules=len(self.native_modules),
            shims=len(bridges),
            skipped_tests=skipped_tests,
            skip_legacy_tests=skip_legacy_tests,
        )
        return bridges

    def _discover_bridge_specifiers(
        self,
        native_specifiers: set[str],
        ext_lib_names: set[str],
        modules: Sequence[NativeModuleLike] | None = None,
    ) -> tuple[dict[str, set[str]], set[str]]:
        if modules is None:
            modules = self.native_modules
        discovered: dict[str, set[str]] = {}
        ignored = native_specifiers | {"@odoo/owl"} | ext_lib_names
        ext_seen: set[str] = set()

        def record(specifier: str, kind: str | None) -> None:
            if specifier in ext_lib_names:
                ext_seen.add(specifier)
                return
            if specifier in ignored:
                return
            if kind:
                discovered.setdefault(specifier, set()).add(kind)
            else:
                discovered.setdefault(specifier, set())

        for asset in modules:
            for specifier, kind in _static_edges(asset.raw_content):
                if specifier.startswith("@"):
                    record(specifier, kind)
        _debug.pipeline(
            "esm_bridges.static_edges",
            bundle=self.bundle_name,
            modules=len(modules),
            discovered=len(discovered),
            ext_libs=len(ext_seen),
        )
        return discovered, ext_seen

    def _discover_reachable_specifiers(
        self,
        native_specifiers: set[str],
        ext_lib_names: set[str],
        provided: frozenset[str] | set[str],
        modules: Sequence[NativeModuleLike] | None = None,
    ) -> tuple[dict[str, set[str]], set[str]]:
        # esbuild follows an alias into the source file of any specifier we do
        # not stub, so a helper the page does not provide is inlined with its
        # whole import tree -- and a page module reached only through that
        # tree, unstubbed, is evaluated a second time (registries report it as
        # a duplicate). The reach therefore has to be transitive: every
        # discovered specifier the page does not provide is lexed in turn.
        discovered, ext_seen = self._discover_bridge_specifiers(
            native_specifiers, ext_lib_names, modules
        )
        resolver = _BridgeExportResolver(external_libs(), self.bundle_name)
        ignored = native_specifiers | {"@odoo/owl"} | ext_lib_names
        queue = [spec for spec in discovered if spec not in provided]
        visited: set[str] = set()
        while queue:
            spec = queue.pop()
            if spec in visited:
                continue
            visited.add(spec)
            src = resolver.read_source(spec)
            if src is None:
                continue
            for specifier, kind in _lexed_imports(
                src, base_spec=spec, base_url=resolver.effective_url(spec)
            ):
                if specifier in ext_lib_names:
                    ext_seen.add(specifier)
                    continue
                if specifier in ignored:
                    continue
                kinds = discovered.setdefault(specifier, set())
                if kind:
                    kinds.add(kind)
                if specifier not in provided and specifier not in visited:
                    queue.append(specifier)
        _debug.pipeline(
            "esm_bridges.reachable",
            bundle=self.bundle_name,
            provided=len(provided),
            visited=len(visited),
            discovered=len(discovered),
            ext_libs=len(ext_seen),
        )
        return discovered, ext_seen

    def prepare_shim_sources(
        self, specifiers: set[str], *, strict: bool = False, wait: bool = False
    ) -> dict[str, str]:
        if not specifiers:
            return {}
        resolver = _BridgeExportResolver(external_libs(), self.bundle_name)
        shims: dict[str, str] = {}
        with _debug.perf(
            "esm_bridges.shim_sources",
            bundle=self.bundle_name,
            specifiers=len(specifiers),
            strict=strict,
            wait=wait,
        ):
            for spec in sorted(specifiers):
                src_names, has_default = resolver.source_exports(spec)
                if strict:
                    shims[spec] = _strict_stub_source(spec, src_names)
                    continue
                shim, _star = _bridge_shim_source(
                    spec, {"__default__"}, src_names, has_default, wait=wait
                )
                shims[spec] = shim
        return shims

    def _prepare_native_to_legacy_bridge(
        self,
        native_specifiers: set[str],
        modules: Sequence[NativeModuleLike] | None = None,
    ) -> dict[str, str]:
        if modules is None:
            modules = self.native_modules
        discovered, ext_seen = self._discover_bridge_specifiers(
            native_specifiers, set(external_libs()), modules=modules
        )
        bridge_map, star_fallback = self._prepare_bridge_map(discovered)
        log_event(
            _bridge_log,
            logging.DEBUG,
            "build",
            bundle=self.bundle_name,
            shims=len(bridge_map),
            discovered=len(discovered),
            native_files=len(modules),
            star_fallback=star_fallback,
            ext_libs_skipped=len(ext_seen),
            ext_libs=",".join(sorted(ext_seen)) or "-",
        )
        return bridge_map

    def _prepare_bridge_map(
        self, discovered: Mapping[str, set[str]]
    ) -> tuple[dict[str, str], int]:
        resolver = _BridgeExportResolver(external_libs(), self.bundle_name)
        shims_by_spec: dict[str, str] = {}
        star_fallback = 0
        for specifier, kinds in sorted(discovered.items()):
            src_names, has_default = resolver.source_exports(specifier)
            shim, is_star_fallback = _bridge_shim_source(
                specifier, kinds, src_names, has_default
            )
            shims_by_spec[specifier] = shim
            if is_star_fallback:
                star_fallback += 1
                _debug.logic(
                    "esm_bridges.star_fallback",
                    bundle=self.bundle_name,
                    spec=specifier,
                    kinds=sorted(kinds),
                    names=len(src_names),
                )
        return self._persist_bridge_shims(shims_by_spec), star_fallback

    def prepare_page_provided_bridges(
        self,
        native_specifiers: set[str],
        provided: frozenset[str] | set[str],
        modules: Sequence[NativeModuleLike] | None = None,
    ) -> tuple[dict[str, str], set[str]]:
        # a bundle served per file on a page that already carries some of
        # what it reaches: the page's copy answers through a bridge, the rest
        # resolves per file -- a second per-file copy of a page module is a
        # second registry registration and a second class
        if modules is None:
            modules = self.native_modules
        discovered, _ext = self._discover_reachable_specifiers(
            native_specifiers, set(external_libs()), provided, modules=modules
        )
        bridged = {
            spec: kinds for spec, kinds in discovered.items() if spec in provided
        }
        bridge_map, star_fallback = self._prepare_bridge_map(bridged)
        per_file = set(discovered) - set(bridged)
        log_event(
            _bridge_log,
            logging.DEBUG,
            "page_provided",
            bundle=self.bundle_name,
            bridged=len(bridge_map),
            per_file=len(per_file),
            star_fallback=star_fallback,
        )
        return bridge_map, per_file


_EDGE_KINDS = {"default": "__default__", "star": "__star__"}

_REEXPORT_ANY_RE = re.compile(
    r"(?<![\w$.])export\s*(?P<star>\*(?:\s*as\s+[\w$]+)?|\{(?P<names>[^}]*)\})\s*"
    r"""from\s*["'](?P<spec>[^"'\n]+)["']"""
)


def _static_edges(src: str) -> list[tuple[str, str | None]]:
    # every specifier esbuild follows at bundle time: import bindings, side
    # imports, and `export ... from`, which the lexer keeps out of `imports`
    lexed = lex_module(src)
    if lexed is not None:
        return [
            (record["n"], _EDGE_KINDS.get(record["kind"]))
            for record in (*lexed["imports"], *lexed.get("reexports", ()))
            if record["n"]
        ]
    edges: list[tuple[str, str | None]] = []
    src = _JS_OPAQUE_RE.sub("", src)
    for match in _IMPORT_ANY_RE.finditer(src):
        specifier = match.group("spec") or match.group("side")
        if match.group("default") is not None or match.group("mixed") is not None:
            edges.append((specifier, "__default__"))
        elif match.group("star") is not None:
            edges.append((specifier, "__star__"))
        else:
            edges.append((specifier, None))
    for match in _REEXPORT_ANY_RE.finditer(src):
        names = match.group("names")
        if names is None:
            kind = "__star__"
        elif re.search(r"\bdefault\b", names):
            kind = "__default__"
        else:
            kind = None
        edges.append((match.group("spec"), kind))
    return edges


def _lexed_imports(
    src: str, *, base_spec: str, base_url: str | None = None
) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for specifier, kind in _static_edges(src):
        if specifier.startswith("."):
            resolved = _relative_to_specifier(base_spec, specifier, base_url)
            if resolved is None:
                continue
            specifier = resolved
        elif not specifier.startswith("@"):
            continue
        out.append((specifier, kind))
    return out


def _relative_to_specifier(
    base_spec: str, relative: str, base_url: str | None = None
) -> str | None:
    # a specifier is not a directory: "@x/models/related_models" names
    # related_models/index.js, whose siblings live under related_models/,
    # so a relative import resolves against the file's url when it is known
    if base_url:
        resolved = _resolve_export_specifier(base_spec, relative, base_url)
        if resolved is not None:
            return resolved
    if not base_spec.startswith("@"):
        return None
    base_dir = posixpath.dirname(base_spec)
    joined = posixpath.normpath(posixpath.join(base_dir, relative))
    if not joined.startswith("@"):
        return None
    return joined.removesuffix(".js").removesuffix("/index")
