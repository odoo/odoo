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


def _rewrite_chunk_references(content: str, names: dict[str, str]) -> str:
    return _CHUNK_NAME.sub(lambda match: names.get(match[0], match[0]), content)


def _chunk_name(digest: str) -> str:
    return f"chunk-{digest[:8].upper()}.esm.js"


_SELF = "chunk-SELF0000.esm.js"


def _is_code(name: str) -> bool:
    # a sourcemap names its chunk by the name esbuild chose; only code files
    # say something about which chunk is which
    return not name.endswith(".map")


def _name_chunk_cycles(
    members: list[str], files: dict[str, str], named: dict[str, str]
) -> dict[str, str]:
    # A chunk in an import cycle cannot be named after its dependencies' final
    # names, so its name is a colour refined over the cycle: its own text with
    # the cycle's references masked, then, member by member, the colours of the
    # chunks it references and of the files that reference it (an entry by its
    # own, stable name). Members left with one colour are indistinguishable by
    # everything the build says about them, and are ordered by it alone.
    cyclic = set(members)
    references = {
        name: [dep for dep in _CHUNK_NAME.findall(files[name]) if dep in cyclic]
        for name in members
    }
    # who references a member, and where in its text: an entry that imports two
    # members of identical text still imports one of them first
    referrers: dict[str, list[tuple[str, int]]] = {name: [] for name in members}
    for source, content in files.items():
        if not _is_code(source):
            continue
        for position, dep in enumerate(_CHUNK_NAME.findall(content)):
            if dep in cyclic and dep != source:
                referrers[dep].append((source, position))
    colour = {
        name: cache_hash(
            _CHUNK_NAME.sub(
                lambda match: (
                    named.get(match[0])
                    or ("chunk-" if match[0] in cyclic else match[0])
                ),
                files[name],
            ).encode("utf-8")
        )
        for name in members
    }
    for _ in members:
        colour = {
            name: cache_hash(
                "\0".join(
                    [
                        colour[name],
                        *(colour[dep] for dep in references[name]),
                        "|",
                        *sorted(
                            (colour[source] if source in cyclic else "entry:" + source)
                            + f"@{position}"
                            for source, position in referrers[name]
                        ),
                    ]
                ).encode("utf-8")
            )
            for name in members
        }
    taken = set(named.values())
    names: dict[str, str] = {}
    for name in sorted(members, key=lambda member: (colour[member], member)):
        digest = colour[name]
        while (fresh := _chunk_name(digest)) in taken:
            digest = cache_hash(digest.encode("utf-8"))
        taken.add(fresh)
        names[name] = fresh
    return names


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
    while ready := sorted(name for name in pending if imports[name] <= renamed.keys()):
        for name in ready:
            # the chunk's own name (in its sourceMappingURL) is esbuild's
            # choice, so it is masked out of what names it
            own = _rewrite_chunk_references(files[name], {**renamed, name: _SELF})
            renamed[name] = _chunk_name(cache_hash(own.encode("utf-8")))
            pending.discard(name)
    cyclic = len(pending)
    if pending:
        renamed |= _name_chunk_cycles(sorted(pending), files, renamed)
    maps = {old + ".map": new + ".map" for old, new in renamed.items()}
    rewritten = {
        renamed.get(name) or maps.get(name, name): _rewrite_chunk_references(
            content, renamed
        )
        for name, content in files.items()
    }
    files.clear()
    files.update(rewritten)
    _debug.logic(
        "esbuild.chunks_canonicalized",
        chunks=len(chunks),
        renamed=sum(old != new for old, new in renamed.items()),
        cycle=cyclic,
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
    if metafile:
        metafile = _rewrite_chunk_references(metafile, renamed)
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
