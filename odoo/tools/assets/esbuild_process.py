from __future__ import annotations

import contextlib
import glob
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import odoo
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.libs.hashing import cache_hash

_esbuild_log = get_asset_logger("esbuild")
_debug = DebugLog(__name__)

_CHUNK_NAME = re.compile(r"chunk-[A-Z0-9]{8}\.esm\.js")


def canonicalize_chunk_names(files: dict[str, str]) -> dict[str, str]:
    chunks = {name for name in files if _CHUNK_NAME.fullmatch(name)}
    if not chunks:
        return {}
    imports = {
        name: {dep for dep in _CHUNK_NAME.findall(files[name]) if dep in chunks}
        - {name}
        for name in chunks
    }
    renamed: dict[str, str] = {}
    pending = set(chunks)
    while pending:
        ready = sorted(name for name in pending if imports[name] <= set(renamed))
        if not ready:
            break
        for name in ready:
            content = files[name]
            for old, new in renamed.items():
                content = content.replace(old, new)
            fresh = f"chunk-{cache_hash(content.encode('utf-8'))[:8].upper()}.esm.js"
            renamed[name] = fresh
            files[fresh] = content
            if fresh != name:
                del files[name]
            pending.discard(name)
    for name in list(files):
        if name in renamed.values():
            continue
        content = files[name]
        for old, new in renamed.items():
            content = content.replace(old, new)
        files[name] = content
    _debug.logic(
        "esbuild.chunks_canonicalized",
        chunks=len(chunks),
        renamed=sum(old != new for old, new in renamed.items()),
        cycle=len(pending),
    )
    return renamed


def log_invoke(
    name: str,
    entry_lines: list[str],
    entry_bytes: int,
    alias_flags: list[str],
    external_flags: list[str],
    tmp_dir: str,
) -> None:
    log_event(
        _esbuild_log,
        logging.DEBUG,
        "invoke",
        bundle=name,
        entries=len(entry_lines),
        entry_bytes=entry_bytes,
        aliases=len(alias_flags),
        externals=len(external_flags) + 1,
        tmp=tmp_dir,
    )


def remove_stale_fail_dumps(name: str) -> None:
    pattern = "esbuild_fail_" + glob.escape(name) + "_*.js"
    removed = 0  # debuglog
    with contextlib.suppress(OSError):
        for stale in Path(tempfile.gettempdir()).glob(pattern):
            with contextlib.suppress(OSError):
                stale.unlink()
                removed += 1  # debuglog
    _debug.lifecycle("esbuild.fail_dumps_removed", bundle=name, removed=removed)


def _dump_failed_entry(name: str, entry_text: str) -> str:
    remove_stale_fail_dumps(name)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix=f"esbuild_fail_{name}_",
            suffix=".js",
            delete=False,
            encoding="utf-8",
        ) as debug_file:
            debug_file.write(entry_text)
            _debug.lifecycle(
                "esbuild.fail_dump_written",
                bundle=name,
                path=debug_file.name,
                size=len(entry_text),
            )
            return debug_file.name
    except OSError:
        _debug.logic("esbuild.fail_dump_unwritable", bundle=name)
        return "(write failed)"


def run_esbuild(
    name: str,
    argv: list[str],
    timeout_s: int,
    entry_text: str,
    _t0: float,
    node_path: str | None = None,
) -> None:
    env = os.environ.copy()
    if node_path:
        env["NODE_PATH"] = node_path
    try:
        result = subprocess.run(
            argv,
            input=entry_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_s,
            cwd=str(Path(odoo.__path__[0]).parent),
            env=env,
            check=False,
        )
        if result.returncode != 0:
            debug_path = _dump_failed_entry(name, entry_text)
            log_event(
                _esbuild_log,
                logging.WARNING,
                "failed",
                bundle=name,
                exit=result.returncode,
                entry=debug_path,
                elapsed=f"{time.monotonic() - _t0:.3f}",
            )
            _esbuild_log.warning(
                "esbuild stderr for %s:\n%s",
                name,
                result.stderr,
            )
            raise RuntimeError(
                f"esbuild failed (exit {result.returncode}): {result.stderr[:500]}"
            )
    except subprocess.TimeoutExpired:
        log_event(
            _esbuild_log,
            logging.ERROR,
            "timeout",
            bundle=name,
            timeout_s=timeout_s,
        )
        raise RuntimeError(f"esbuild timed out after {timeout_s}s") from None


def _read_metafile(name: str, metafile_path: str) -> str | None:
    try:
        return Path(metafile_path).read_text(encoding="utf-8")
    except OSError as mf_err:
        log_event(
            _esbuild_log,
            logging.DEBUG,
            "metafile_unavailable",
            bundle=name,
            err=type(mf_err).__name__,
        )
        return None


def _read_sourcemap(name: str, sourcemap_path: str, source_maps: str) -> str | None:
    if source_maps not in ("linked", "external"):
        return None
    try:
        return Path(sourcemap_path).read_text(encoding="utf-8")
    except OSError as sm_err:
        log_event(
            _esbuild_log,
            logging.DEBUG,
            "sourcemap_unavailable",
            bundle=name,
            err=type(sm_err).__name__,
        )
        return None


def postprocess_output(
    name: str,
    module_count: int,
    out_path: str,
    metafile_path: str,
    sourcemap_path: str,
    source_maps: str,
    entry_bytes: int,
    _t0: float,
) -> tuple[str, str | None, str | None]:
    try:
        bundle_text = Path(out_path).read_text(encoding="utf-8")
    except OSError as out_err:
        raise RuntimeError(
            f"esbuild exited 0 but output file missing: {out_err}"
        ) from out_err

    metafile = _read_metafile(name, metafile_path)
    sourcemap = _read_sourcemap(name, sourcemap_path, source_maps)

    if source_maps == "linked":
        expected_name = f"{name}.esm.js.map"
        bundle_text = re.sub(
            r"//# sourceMappingURL=\S+(?=\s*\Z)",
            f"//# sourceMappingURL={expected_name}",
            bundle_text,
        )
        _debug.logic("esbuild.sourcemap_relinked", bundle=name, name=expected_name)

    elapsed = time.monotonic() - _t0
    output_bytes = len(bundle_text)
    log_event(
        _esbuild_log,
        logging.INFO,
        "bundled",
        bundle=name,
        modules=module_count,
        input_bytes=entry_bytes,
        output_bytes=output_bytes,
        ratio=f"{output_bytes / entry_bytes:.2f}" if entry_bytes else "n/a",
        elapsed=f"{elapsed:.3f}",
    )
    return bundle_text, metafile, sourcemap


def get_group_output(
    name: str,
    out_dir: Path,
    metafile_path: str,
    entry_count: int,
    module_count: int,
    _t0: float,
) -> tuple[dict[str, str], str | None]:
    files = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(out_dir.iterdir())
        if path.is_file()
    }
    renamed = canonicalize_chunk_names(files)
    try:
        metafile = Path(metafile_path).read_text(encoding="utf-8")
    except OSError:
        metafile = None
    for old, new in renamed.items():
        if metafile and old != new:
            metafile = metafile.replace(old, new)
    log_event(
        _esbuild_log,
        logging.INFO,
        "bundled_group",
        bundle=name,
        entries=entry_count,
        modules=module_count,
        files=len(files),
        output_bytes=sum(len(code) for code in files.values()),
        elapsed=f"{time.monotonic() - _t0:.3f}",
    )
    return files, metafile
