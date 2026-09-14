import hashlib
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import odoo
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.tools.assets import esbuild_process, esbuild_stubs
from odoo.tools.json import scriptsafe as json

_esbuild_log = get_asset_logger("esbuild")
_debug = DebugLog(__name__)

EXTERNAL_SPECIFIER_PREFIX = "@odoo/"


def module_specifiers(asset) -> tuple[str, ...]:
    names = [asset.module_path]
    if (asset.url or "").endswith("/index.js"):
        names.append(asset.module_path + "/index")
    header = getattr(asset, "parsed_header", None)
    if header and header["alias"]:
        names.append(header["alias"])
    return tuple(names)


class EsbuildResult(NamedTuple):
    code: str
    metafile: str | None
    sourcemap: str | None
    # a digest of what esbuild was given; the attachment index keyed on it
    # lets the next process serve this result without running esbuild
    source_key: str | None = None
    # served from the index: the code already carries the bundle's templates
    prebuilt: bool = False


class EsbuildGroupResult(NamedTuple):
    files: dict[str, str]
    metafile: str | None


def _esbuild_argv(
    esbuild: str,
    *,
    target: str,
    out_path: str | None,
    metafile_path: str,
    external_specifier_flags: list[str],
    external_flags: list[str],
    sourcemap_flags: list[str],
    alias_flags: list[str],
    extra_flags: Sequence[str] = (),
    entry_points: Sequence[str] = (),
    out_dir: str | None = None,
) -> list[str]:
    output_flags = (
        [f"--outfile={out_path}"]
        if out_path
        else [
            f"--outdir={out_dir}",
            "--splitting",
            "--entry-names=[name].esm",
            "--chunk-names=chunk-[hash].esm",
        ]
    )
    return [
        esbuild,
        "--bundle",
        "--format=esm",
        "--minify",
        "--keep-names",
        *external_specifier_flags,
        *external_flags,
        f"--target={target}",
        "--resolve-extensions=.js,.mjs,.json",
        # Every addons repo carries a tsconfig.json whose `paths` point "@web/*"
        # and kin at the checkout BESIDE it, for tsc. esbuild honours the
        # nearest tsconfig.json per source file, so a sibling repo's modules
        # would resolve core through that mapping instead of the aliases
        # above -- a second copy of every core module whenever the served
        # tree is not that sibling (a worktree), and a split singleton.
        "--tsconfig-raw={}",
        *output_flags,
        f"--metafile={metafile_path}",
        *sourcemap_flags,
        *alias_flags,
        *extra_flags,
        *entry_points,
    ]


_ESBUILD_PATH: str | None = None


def _get_esbuild_path() -> str | None:
    global _ESBUILD_PATH  # noqa: PLW0603  process-wide memo of a filesystem lookup
    if _ESBUILD_PATH is not None:
        return _ESBUILD_PATH
    odoo_root = Path(odoo.__path__[0]).parent
    _ESBUILD_PATH = shutil.which("esbuild") or shutil.which(
        "esbuild",
        path=str(odoo_root / "node_modules" / ".bin"),
    )
    return _ESBUILD_PATH


_TEMPLATE_LITERAL_TOKENS = re.compile(r"\\.|`|\$\{|\{|\}", re.DOTALL)


def has_nested_template_literal(source: str) -> bool:
    if "`" not in source or "${" not in source:
        return False
    stack: list[str | int] = []
    for match in _TEMPLATE_LITERAL_TOKENS.finditer(source):
        token = match.group()
        if token[0] == "\\":
            continue
        if token == "`":
            if stack and stack[-1] == "tpl":
                stack.pop()
            elif any(entry != "tpl" for entry in stack):
                return True
            else:
                stack.append("tpl")
        elif token == "${":
            if stack and stack[-1] == "tpl":
                stack.append(0)
        elif token == "{":
            if stack and stack[-1] != "tpl":
                stack[-1] = int(stack[-1]) + 1
        elif stack and stack[-1] != "tpl":
            depth = int(stack[-1])
            if depth:
                stack[-1] = depth - 1
            else:
                stack.pop()
    return False


def minify_js(
    source: str,
    *,
    label: str = "<asset>",
    timeout_s: int = 60,
    keep_names: bool = False,
) -> str | None:
    esbuild_bin = _get_esbuild_path()
    if not esbuild_bin:
        log_event(_esbuild_log, logging.WARNING, "minify_no_binary", asset=label)
        return None
    argv = [
        esbuild_bin,
        "--minify",
        *(["--keep-names"] if keep_names else []),
        "--loader=js",
        f"--target={EsbuildCompiler._ESBUILD_TARGET}",
        "--charset=utf8",
        "--legal-comments=inline",
        "--log-level=error",
    ]
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            input=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log_event(
            _esbuild_log,
            logging.WARNING,
            "minify_timeout",
            asset=label,
            timeout_s=timeout_s,
        )
        return None
    if result.returncode != 0:
        log_event(
            _esbuild_log,
            logging.WARNING,
            "minify_failed",
            asset=label,
            exit=result.returncode,
        )
        _esbuild_log.warning("esbuild minify stderr for %s:\n%s", label, result.stderr)
        return None
    log_event(
        _esbuild_log,
        logging.DEBUG,
        "minify",
        asset=label,
        in_kb=f"{len(source) / 1024:.0f}",
        out_kb=f"{len(result.stdout) / 1024:.0f}",
        elapsed=f"{time.monotonic() - t0:.3f}",
    )
    return result.stdout.strip()


class EsbuildCompiler:
    def __init__(
        self,
        name: str,
        native_modules: list,
        javascripts: list | tuple = (),
        *,
        import_map_included: bool = False,
        skip_legacy_test_imports: bool = False,
        standalone: bool = False,
        addon_flags_provider: Callable[[Path], tuple[list[str], list[str]]]
        | None = None,
        exported_specs: Collection[str] | None = None,
        registered_reach: Mapping[str, str] | None = None,
    ) -> None:
        self.name = name
        self.native_modules = list(native_modules)
        self.javascripts = list(javascripts)
        self._import_map_included = import_map_included
        self._skip_legacy_test_imports = skip_legacy_test_imports
        self._standalone = standalone
        self._exported_specs = (
            None if exported_specs is None else frozenset(exported_specs)
        )
        self._registered_reach = dict(registered_reach or {})
        self._addon_flags_provider = (
            addon_flags_provider or self._get_esbuild_addon_flags
        )
        self._last_metafile: str | None = None
        self._last_sourcemap: str | None = None
        self._mirror_roots: dict[str, Path] = {}
        self._absolute_entry_paths = False

    _esbuild_addon_scan_cache: tuple | None = None

    @classmethod
    def invalidate_addon_scan_cache(cls) -> None:
        _debug.lifecycle(
            "esbuild.addon_scan_invalidated",
            cached=cls._esbuild_addon_scan_cache is not None,
        )
        cls._esbuild_addon_scan_cache = None

    @classmethod
    def resolves_specifier(cls, spec: str) -> bool:
        from odoo.tools.assets.esm_registry import external_bare_specifiers

        return spec.startswith(EXTERNAL_SPECIFIER_PREFIX) or spec in (
            external_bare_specifiers()
        )

    @classmethod
    def _get_esbuild_addon_flags(cls, odoo_root: Path) -> tuple[list[str], list[str]]:
        from odoo.addons import __path__ as _addon_paths  # type: ignore[attr-defined]

        cache_key = tuple(_addon_paths)
        cached = cls._esbuild_addon_scan_cache
        if cached and cached[0] == cache_key:
            return list(cached[1]), list(cached[2])

        alias_flags: list[str] = []
        test_external_flags: list[str] = []
        seen_addons: set[str] = set()
        for addon_dir in _addon_paths:
            addon_dir = Path(addon_dir)
            if not addon_dir.is_dir():
                continue
            for entry in addon_dir.iterdir():
                name = entry.name
                if name in seen_addons or not entry.is_dir():
                    continue
                seen_addons.add(name)
                static_src = entry / "static" / "src"
                if static_src.is_dir():
                    rel = os.path.relpath(static_src, odoo_root)
                    alias_flags.append(f"--alias:@{name}=./{rel}")
                if (entry / "static" / "tests").is_dir():
                    test_external_flags.append(f"--external:@{name}/../tests/*")
                    rel_tests = os.path.relpath(
                        entry / "static" / "tests",
                        odoo_root,
                    )
                    test_external_flags.append(f"--external:./{rel_tests}/*")

        cls._esbuild_addon_scan_cache = (cache_key, alias_flags, test_external_flags)
        log_event(
            _esbuild_log,
            logging.DEBUG,
            "addon_scan_cached",
            aliases=len(alias_flags),
            test_externals=len(test_external_flags),
        )
        return list(alias_flags), list(test_external_flags)

    _ESBUILD_TIMEOUT_S: int = 30
    _ESBUILD_TARGET: str = "es2023"
    _ESBUILD_TARGET_TOKEN_RE = re.compile(r"[a-z]+\d*(?:\.\d+)*")
    _ESBUILD_SOURCE_MAPS: str = ""
    _ESBUILD_SOURCE_MAP_MODES: frozenset = frozenset(
        {
            "",
            "linked",
            "external",
            "inline",
        }
    )

    def _esbuild_skip_reason(self) -> str | None:
        if not self.native_modules:
            return "no_native_modules"
        if self._import_map_included:
            return "import_map_included"
        return None

    def _esbuild_external_flags(
        self, odoo_root: Path, alias_flags: list[str]
    ) -> tuple[list[str], list[str]]:
        from odoo.tools.assets.esm_registry import external_bare_specifiers

        if self._standalone:
            alias_flags += self._standalone_alias_flags(
                odoo_root,
                {
                    flag.partition("=")[0].removeprefix("--alias:")
                    for flag in alias_flags
                },
            )
            return [], alias_flags
        return [
            f"--external:{EXTERNAL_SPECIFIER_PREFIX}*",
            "--external:/web/static/lib/*",
            *(f"--external:{spec}" for spec in sorted(external_bare_specifiers())),
        ], alias_flags

    def compile(
        self,
        timeout_s: int | None = None,
        target: str | None = None,
        source_maps: str | None = None,
        dynamic_child_specs: frozenset[str] | None = None,
        secondary_parent_stubs: dict[str, str] | None = None,
    ) -> EsbuildResult:
        timeout_s, target, source_maps = self._esbuild_resolve_opts(
            timeout_s, target, source_maps
        )
        if reason := self._esbuild_skip_reason():
            log_event(
                _esbuild_log, logging.DEBUG, "skip", bundle=self.name, reason=reason
            )
            return EsbuildResult("", None, None)

        _t0 = time.monotonic()

        odoo_root = Path(odoo.__path__[0]).parent
        esbuild = _get_esbuild_path()
        if not esbuild:
            raise FileNotFoundError(
                "esbuild is required for native ESM bundling. "
                "Run 'npm install' in the Odoo root directory."
            )

        with _debug.perf(
            "esbuild.compile_prepared",
            bundle=self.name,
            modules=len(self.native_modules),
            standalone=self._standalone,
            dynamic_children=len(dynamic_child_specs or ()),
            parent_stubs=len(secondary_parent_stubs or {}),
        ) as span:
            alias_flags, external_flags = self._esbuild_flags(
                odoo_root, dynamic_child_specs
            )

            tmp_dir = tempfile.mkdtemp(prefix=f"odoo-esbuild-{self.name}-")
            out_path = str(Path(tmp_dir) / "bundle.out.js")
            metafile_path = str(Path(tmp_dir) / "bundle.meta.json")

            self._mirror_roots = {}
            argv_aliases, node_path = self._addon_resolution_root(
                alias_flags, odoo_root
            )
            moved = set(alias_flags) - set(argv_aliases)
            if secondary_parent_stubs:
                alias_flags, self._mirror_roots = esbuild_stubs.mirror_aliases(
                    self.native_modules,
                    list(alias_flags),
                    secondary_parent_stubs,
                    tmp_dir,
                    odoo_root,
                )
            alias_flags = [flag for flag in alias_flags if flag not in moved]

            # Parent-owned members are supplied by the stubs when imported.
            # Registering them again as entry modules creates a second namespace.
            entry_modules = [
                asset
                for asset in self.native_modules
                if asset.module_path not in (secondary_parent_stubs or {})
            ]
            entry_lines = self._esbuild_entry_lines(odoo_root, modules=entry_modules)
            entry_text = "\n".join(entry_lines)
            entry_bytes = len(entry_text.encode("utf-8"))
            span.set(
                aliases=len(alias_flags),
                externals=len(external_flags),
                moved=len(moved),
                entries=len(entry_lines),
                node_path=node_path is not None,
            )

        esbuild_process.log_invoke(
            self.name, entry_lines, entry_bytes, alias_flags, external_flags, tmp_dir
        )
        sourcemap_flags = [f"--sourcemap={source_maps}"] if source_maps else []
        sourcemap_path = f"{out_path}.map"
        external_specifier_flags, alias_flags = self._esbuild_external_flags(
            odoo_root, alias_flags
        )
        argv = _esbuild_argv(
            esbuild,
            target=target,
            out_path=out_path,
            metafile_path=metafile_path,
            external_specifier_flags=external_specifier_flags,
            external_flags=external_flags,
            sourcemap_flags=sourcemap_flags,
            alias_flags=alias_flags,
            extra_flags=["--preserve-symlinks"] if self._mirror_roots else [],
        )
        try:
            esbuild_process.run_esbuild(
                self.name, argv, timeout_s, entry_text, _t0, node_path=node_path
            )
            code, self._last_metafile, self._last_sourcemap = (
                esbuild_process.postprocess_output(
                    self.name,
                    len(self.native_modules),
                    out_path,
                    metafile_path,
                    sourcemap_path,
                    source_maps,
                    entry_bytes,
                    _t0,
                )
            )
            return EsbuildResult(code, self._last_metafile, self._last_sourcemap)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _esbuild_entry_files(
        self, entries: dict[str, list], entry_dir: Path, odoo_root: Path
    ) -> tuple[list[str], int]:
        entry_points = []
        entry_bytes = 0
        for name, modules in entries.items():
            if not modules:
                continue
            text = "\n".join(self._esbuild_entry_lines(odoo_root, modules))
            entry_file = entry_dir / f"{name}.js"
            entry_file.write_text(text, encoding="utf-8")
            entry_points.append(str(entry_file))
            entry_bytes += len(text.encode("utf-8"))
        return entry_points, entry_bytes

    def compile_group(
        self,
        entries: dict[str, list],
        *,
        timeout_s: int | None = None,
        target: str | None = None,
        source_maps: str | None = None,
        secondary_parent_stubs: dict[str, str] | None = None,
    ) -> EsbuildGroupResult:
        timeout_s, target, source_maps = self._esbuild_resolve_opts(
            timeout_s, target, source_maps
        )
        if not any(entries.values()):
            _debug.logic("esbuild.group_empty", bundle=self.name, groups=len(entries))
            return EsbuildGroupResult({}, None)
        _t0 = time.monotonic()
        _debug.pipeline(
            "esbuild.compile_group",
            bundle=self.name,
            groups=len(entries),
            modules=sum(len(m) for m in entries.values()),
            parent_stubs=len(secondary_parent_stubs or {}),
        )
        odoo_root = Path(odoo.__path__[0]).parent
        esbuild = _get_esbuild_path()
        if not esbuild:
            raise FileNotFoundError(
                "esbuild is required for native ESM bundling. "
                "Run 'npm install' in the Odoo root directory."
            )
        alias_flags, external_flags = self._esbuild_flags(odoo_root, None)
        tmp_dir = tempfile.mkdtemp(prefix=f"odoo-esbuild-{self.name}-")
        try:
            out_dir = Path(tmp_dir) / "out"
            entry_dir = Path(tmp_dir) / "entries"
            entry_dir.mkdir()
            metafile_path = str(Path(tmp_dir) / "group.meta.json")
            self._mirror_roots = {}
            self._absolute_entry_paths = True
            argv_aliases, node_path = self._addon_resolution_root(
                alias_flags, odoo_root
            )
            moved = set(alias_flags) - set(argv_aliases)
            mirrored_flags, self._mirror_roots = esbuild_stubs.mirror_aliases(
                self.native_modules,
                list(alias_flags),
                secondary_parent_stubs or {},
                tmp_dir,
                odoo_root,
            )
            alias_flags = [flag for flag in mirrored_flags if flag not in moved]
            entry_points, entry_bytes = self._esbuild_entry_files(
                entries, entry_dir, odoo_root
            )
            external_specifier_flags, alias_flags = self._esbuild_external_flags(
                odoo_root, alias_flags
            )
            argv = _esbuild_argv(
                esbuild,
                target=target,
                out_path=None,
                metafile_path=metafile_path,
                external_specifier_flags=external_specifier_flags,
                external_flags=external_flags,
                sourcemap_flags=([f"--sourcemap={source_maps}"] if source_maps else []),
                alias_flags=alias_flags,
                extra_flags=["--preserve-symlinks"],
                entry_points=entry_points,
                out_dir=str(out_dir),
            )
            esbuild_process.log_invoke(
                self.name,
                entry_points,
                entry_bytes,
                alias_flags,
                external_flags,
                tmp_dir,
            )
            esbuild_process.run_esbuild(
                self.name, argv, timeout_s, "", _t0, node_path=node_path
            )
            files, metafile = esbuild_process.get_group_output(
                self.name,
                out_dir,
                metafile_path,
                len(entry_points),
                sum(len(m) for m in entries.values()),
                _t0,
            )
            return EsbuildGroupResult(files, metafile)
        finally:
            self._absolute_entry_paths = False
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _esbuild_resolve_opts(
        self,
        timeout_s: int | None,
        target: str | None,
        source_maps: str | None,
    ) -> tuple[int, str, str]:
        if timeout_s is None:
            timeout_s = self._ESBUILD_TIMEOUT_S
        if target is None:
            target = self._ESBUILD_TARGET
        elif not all(
            self._ESBUILD_TARGET_TOKEN_RE.fullmatch(token.strip())
            for token in target.split(",")
        ):
            log_event(
                _esbuild_log,
                logging.WARNING,
                "target_invalid",
                bundle=self.name,
                target=target,
                fallback=self._ESBUILD_TARGET,
            )
            target = self._ESBUILD_TARGET
        if source_maps is None:
            source_maps = self._ESBUILD_SOURCE_MAPS
        if source_maps not in self._ESBUILD_SOURCE_MAP_MODES:
            log_event(
                _esbuild_log,
                logging.WARNING,
                "source_maps_unknown_mode",
                bundle=self.name,
                mode=source_maps,
                valid=sorted(m for m in self._ESBUILD_SOURCE_MAP_MODES if m),
            )
            source_maps = ""
        return timeout_s, target, source_maps

    def _reached_module_path(self, url: str, odoo_root: Path) -> str | None:
        from odoo.tools.misc import file_path

        rel = url.lstrip("/")
        for candidate in (rel, rel.removesuffix(".js") + "/index.js"):
            try:
                path = file_path(candidate)
            except ValueError, FileNotFoundError:
                continue
            return self._mirrored_path(candidate) or (
                "./" + os.path.relpath(path, odoo_root)
            )
        return None

    def _mirrored_path(self, url: str) -> str | None:
        # a mirrored addon's static/src lives in the layout with its siblings
        # (tests, lib) symlinked next to it, and esbuild preserves symlinks
        # there: an entry spelled by its real path and an alias import of the
        # same file (`@website/../tests/tours/x`) are two modules to esbuild,
        # each registering its tours once
        addon, _, rest = url.lstrip("/").partition("/static/")
        mirror = self._mirror_roots.get(addon) if rest else None
        if mirror is None:
            return None
        return str(mirror.parent / rest)

    def _standalone_alias_flags(
        self, odoo_root: Path, already_aliased: set[str]
    ) -> list[str]:
        from odoo.tools.assets.esm_registry import external_libs
        from odoo.tools.misc import file_path

        flags = []
        for spec, url in sorted(external_libs().items()):
            if spec in already_aliased:
                continue
            try:
                path = file_path(url.lstrip("/"))
            except ValueError, FileNotFoundError:
                continue
            flags.append(f"--alias:{spec}=./{os.path.relpath(path, odoo_root)}")
        return flags

    def _imports_owl(self) -> bool:
        return any(
            "@odoo/owl" in (asset.raw_content or "") for asset in self.native_modules
        )

    def _entry_path(self, asset, odoo_root: Path) -> str:
        url = asset.url or ""
        mirrored = self._mirrored_path(url)
        if mirrored is not None:
            return mirrored
        if self._absolute_entry_paths:
            return str(
                Path(asset._filename) if asset._filename else odoo_root / f"addons{url}"
            )
        if asset._filename:
            return "./" + os.path.relpath(asset._filename, odoo_root)
        return f"./addons{url}"

    def _esbuild_entry_lines(
        self, odoo_root: Path, modules: list | None = None
    ) -> list[str]:
        entry_lines = []
        register_entries = []
        registered_specs: set[str] = set()
        if not self._standalone or self._imports_owl():
            registered_specs.add("@odoo/owl")
            entry_lines.append('import * as __owl from "@odoo/owl";')
            register_entries.append('  "@odoo/owl": __owl')
        _skip_legacy_test_imports = self._skip_legacy_test_imports
        modules = self.native_modules if modules is None else modules
        exported = self._exported_specs
        for i, asset in enumerate(modules):
            if _skip_legacy_test_imports and "/static/tests/" in (asset.url or ""):
                continue
            path = self._entry_path(asset, odoo_root)
            names = module_specifiers(asset)
            if exported is not None and exported.isdisjoint(names):
                entry_lines.append(f"import {json.dumps(path)};")
                continue
            entry_lines.append(f"import * as __m{i} from {json.dumps(path)};")
            for name in names:
                register_entries.append(f"  {json.dumps(name)}: __m{i}")
                registered_specs.add(name)
        for i, (spec, url) in enumerate(sorted(self._registered_reach.items())):
            if spec in registered_specs:
                continue
            reached = self._reached_module_path(url, odoo_root)
            if reached is None:
                continue
            entry_lines.append(f"import * as __r{i} from {json.dumps(reached)};")
            register_entries.append(f"  {json.dumps(spec)}: __r{i}")
            registered_specs.add(spec)

        if self._standalone:
            entry_lines.append("if (globalThis.odoo?.loader?.registerNativeModules) {")
        entry_lines.append("odoo.loader.registerNativeModules({")
        entry_lines.append(",\n".join(register_entries))
        entry_lines.append("});")
        from odoo.tools.assets.esm_registry import external_lib_aliases

        for ext_name, int_name in external_lib_aliases().items():
            if int_name in registered_specs:
                entry_lines.append(
                    f"odoo.loader.modules.set({json.dumps(ext_name)},"
                    f"odoo.loader.modules.get({json.dumps(int_name)}));"
                )
        if self._standalone:
            entry_lines.append("}")
        return entry_lines

    def _esbuild_flags(
        self,
        odoo_root: Path,
        dynamic_child_specs: frozenset[str] | None,
    ) -> tuple[list[str], list[str]]:
        alias_flags, test_external_flags = self._addon_flags_provider(odoo_root)
        bundle_test_addons: set[str] = set()
        for asset in self.native_modules:
            url = (asset.url or "").lstrip("/")
            parts = url.split("/")
            if len(parts) >= 3 and parts[1] == "static" and parts[2] == "tests":
                bundle_test_addons.add(parts[0])
        if not self._reaches_test_files(bundle_test_addons):
            test_external_flags = []
        if bundle_test_addons:
            test_external_flags = [
                flag
                for flag in test_external_flags
                if not any(
                    f"--external:@{name}/../tests/" in flag
                    or f"/{name}/static/tests/" in flag
                    for name in bundle_test_addons
                )
            ]
        dynamic_external_flags: list[str] = []
        if dynamic_child_specs:
            dynamic_external_flags.extend(
                f"--external:{spec}" for spec in sorted(dynamic_child_specs)
            )

        for js_asset in self.javascripts + self.native_modules:
            header = js_asset.parsed_header
            if header and header["alias"] and header["alias"].startswith("@odoo/"):
                if js_asset._filename:
                    alias_path = os.path.relpath(js_asset._filename, odoo_root)
                else:
                    alias_path = f"addons{js_asset.url}"
                alias_flags.append(f"--alias:{header['alias']}=./{alias_path}")
        return alias_flags, test_external_flags + dynamic_external_flags

    def _reaches_test_files(self, bundle_test_addons: set[str]) -> bool:
        if self._skip_legacy_test_imports or bundle_test_addons:
            return True
        return any(
            "/../tests/" in (asset.raw_content or "") for asset in self.native_modules
        )

    _PARENT_DIR_SPECIFIER_RE = re.compile(r'["\'](@[\w.-]+)/\.\./')

    def _addons_reached_through_parent_dirs(self) -> set[str]:
        return {
            match.group(1)
            for asset in (*self.native_modules, *self.javascripts)
            for match in self._PARENT_DIR_SPECIFIER_RE.finditer(asset.raw_content or "")
        }

    def _addon_resolution_root(
        self, alias_flags: list[str], odoo_root: Path
    ) -> tuple[list[str], str | None]:
        roots: dict[str, Path] = {}
        kept: list[str] = []
        keep_aliased = self._addons_reached_through_parent_dirs()
        for flag in alias_flags:
            spec, _, target = flag.removeprefix("--alias:").partition("=")
            if (
                spec.startswith("@")
                and "/" not in spec
                and target.startswith("./")
                and target.endswith("/static/src")
            ):
                roots[spec] = odoo_root / target.removeprefix("./")
                if spec in keep_aliased:
                    kept.append(flag)
            else:
                kept.append(flag)
        if not roots:
            return kept, None
        digest = hashlib.sha1(
            "\n".join(f"{spec}={path}" for spec, path in sorted(roots.items())).encode()
        ).hexdigest()[:12]
        root_dir = Path(tempfile.gettempdir()) / f"odoo-esbuild-roots-{digest}"
        if not root_dir.is_dir():
            staging = Path(
                tempfile.mkdtemp(prefix=f"{root_dir.name}-", dir=root_dir.parent)
            )
            for spec, path in roots.items():
                (staging / spec).symlink_to(path, target_is_directory=True)
            try:
                staging.rename(root_dir)
            except OSError:
                shutil.rmtree(staging, ignore_errors=True)
                if not root_dir.is_dir():
                    raise
        return kept, str(root_dir)
