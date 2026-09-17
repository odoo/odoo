import functools
import os
import sys
import tempfile
import typing
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import IO, Any

from odoo.libs.debug_log import DebugLog

import odoo.addons
from .config import config

_debug = DebugLog(__name__)

_temporary_paths: ContextVar[tuple[str, ...]] = ContextVar(
    "file_open_temporary_paths", default=()
)


@functools.lru_cache(maxsize=512)
def _addons_dir_paths(addons_dir: str) -> tuple[Path, Path]:
    parent_path = Path(os.path.normcase(os.path.normpath(addons_dir)))
    return parent_path, parent_path.resolve()


@functools.lru_cache(maxsize=1)
def _root_path(root: str) -> str:
    return str(Path(root).resolve())


if typing.TYPE_CHECKING:
    from odoo.api import Environment
else:
    Environment = typing.Any


def file_open_temporary_paths() -> tuple[str, ...]:
    return _temporary_paths.get()


def file_path(
    file_path: str,
    filter_ext: tuple[str, ...] = ("",),
    env: Environment | None = None,
    *,
    check_exists: bool = True,
) -> str:
    if _temporary_paths.get():
        return _file_path_uncached(file_path, filter_ext, check_exists)
    return _file_path_resolved(file_path, filter_ext, check_exists)


@functools.lru_cache(maxsize=8192)
def _file_path_resolved(
    file_path: str, filter_ext: tuple[str, ...], check_exists: bool
) -> str:
    return _file_path_uncached(file_path, filter_ext, check_exists)


def clear_caches() -> None:
    _debug.lifecycle(
        "files.caches_cleared",
        paths=_file_path_resolved.cache_info().currsize,
        addons_dirs=_addons_dir_paths.cache_info().currsize,
    )
    _file_path_resolved.cache_clear()
    _addons_dir_paths.cache_clear()
    _root_path.cache_clear()


def _file_path_uncached(
    file_path: str,
    filter_ext: tuple[str, ...],
    check_exists: bool,
) -> str:
    fp = Path(file_path)
    is_abs = fp.is_absolute()
    normalized = (
        Path(os.path.normcase(str(fp))).resolve()
        if is_abs
        else Path(os.path.normcase(os.path.normpath(file_path)))
    )

    normalized_str = str(normalized)
    if filter_ext and not normalized_str.lower().endswith(filter_ext):
        raise ValueError("Unsupported file: " + file_path)

    normalized_str = normalized_str.removeprefix("addons" + os.sep)
    normalized = Path(normalized_str)

    parts = normalized.parts
    if not parts:
        raise FileNotFoundError("File not found: " + file_path)
    if not is_abs and (module := sys.modules.get(f"odoo.addons.{parts[0]}")):
        addons_paths = [str(Path(p).parent) for p in module.__path__]
    else:
        addons_paths = [
            *odoo.addons.__path__,
            _root_path(config.root_path),
            *_temporary_paths.get(),
        ]

    skip_exists_check = not check_exists and (is_abs or len(addons_paths) == 1)

    if is_abs:
        if not (skip_exists_check or normalized.exists()):
            _debug.logic("files.not_found", path=file_path, absolute=True)
            raise FileNotFoundError("File not found: " + file_path)
        for addons_dir in addons_paths:
            parent = str(_addons_dir_paths(addons_dir)[1])
            if normalized_str == parent or normalized_str.startswith(parent + os.sep):
                _debug.perf.count(
                    "files.resolved", path=file_path, addons_dir=addons_dir
                )
                return normalized_str
        _debug.logic(
            "files.escapes_addons_dir", path=file_path, resolved=normalized_str
        )
        raise FileNotFoundError("File not found: " + file_path)

    for addons_dir in addons_paths:
        parent_path, resolved_parent = _addons_dir_paths(addons_dir)
        fpath = parent_path / normalized
        if not (skip_exists_check or fpath.exists()):
            continue
        resolved = os.path.realpath(fpath)
        parent = str(resolved_parent)
        if resolved == parent or resolved.startswith(parent + os.sep):
            _debug.perf.count(
                "files.resolved",
                path=file_path,
                addons_dir=addons_dir,
                candidates=len(addons_paths),
                exists_checked=not skip_exists_check,
            )
            return str(fpath)
        if _debug.logic.enabled and not is_abs:
            _debug.logic(
                "files.escapes_addons_dir",
                path=file_path,
                resolved=resolved,
                root=parent,
            )

    _debug.logic(
        "files.not_found",
        path=file_path,
        absolute=is_abs,
        candidates=len(addons_paths),
        temporary=len(_temporary_paths.get()),
    )
    raise FileNotFoundError("File not found: " + file_path)


def file_open(
    name: str,
    mode: str = "r",
    filter_ext: tuple[str, ...] = (),
    env: Environment | None = None,
) -> IO[Any]:
    writing = any(m in mode for m in ("w", "x", "a"))
    try:
        path = file_path(name, filter_ext=filter_ext, env=env, check_exists=False)
    except FileNotFoundError:
        if not writing:
            raise
        raise FileNotFoundError(
            f"Cannot create {name!r}: file_open() opens files that already exist. "
            f"Create the file first, then reopen it in {mode!r}."
        ) from None
    if writing and not Path(path).is_file():
        raise FileNotFoundError(
            f"Cannot create {path!r}: file_open() opens files that already exist."
        )
    encoding = None if "b" in mode else "utf-8"
    return open(path, mode, encoding=encoding)


@contextmanager
def file_open_temporary_directory(env: object = None) -> Generator[str]:
    with tempfile.TemporaryDirectory() as module_dir:
        token = _temporary_paths.set((*_temporary_paths.get(), module_dir))
        _debug.lifecycle(
            "files.temporary_dir_entered",
            path=module_dir,
            depth=len(_temporary_paths.get()),
        )
        try:
            yield module_dir
        finally:
            _temporary_paths.reset(token)
            _debug.lifecycle("files.temporary_dir_exited", path=module_dir)
