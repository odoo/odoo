import os
from collections.abc import Callable, Sequence
from glob import glob, has_magic
from logging import getLogger
from stat import S_ISLNK
from typing import Any, NamedTuple
from urllib.parse import urlsplit

from odoo.libs.debug_log import DebugLog
from odoo.tools.assets.constants import ASSET_EXTENSIONS, EXTERNAL_ASSET, ExternalAsset

_logger = getLogger(__name__)
_debug = DebugLog(__name__)

DEFAULT_SEQUENCE = 16

APPEND_DIRECTIVE = "append"
PREPEND_DIRECTIVE = "prepend"
AFTER_DIRECTIVE = "after"
BEFORE_DIRECTIVE = "before"
REMOVE_DIRECTIVE = "remove"
REPLACE_DIRECTIVE = "replace"
INCLUDE_DIRECTIVE = "include"
DIRECTIVES_WITH_TARGET = {AFTER_DIRECTIVE, BEFORE_DIRECTIVE, REPLACE_DIRECTIVE}

FullPath = str | ExternalAsset | None


class AssetDirectiveError(ValueError):
    pass


class ResolvedPath(NamedTuple):
    path: str
    full_path: FullPath
    last_modified: float | None

    @property
    def is_external(self) -> bool:
        return self.full_path is EXTERNAL_ASSET


class AssetEntry(NamedTuple):
    path: str
    full_path: FullPath
    bundle: str
    last_modified: float | None

    @property
    def is_external(self) -> bool:
        return self.full_path is EXTERNAL_ASSET


def fs_to_web(path: str) -> str:
    if os.sep == "/":
        return path
    return "/".join(path.split(os.sep))


def can_aggregate(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        not parsed.scheme and not parsed.netloc and not url.startswith("/web/content")
    )


def is_wildcard_glob(path: str) -> bool:
    return has_magic(path)


def _is_symlink(path: str) -> bool:
    try:
        return S_ISLNK(os.lstat(path).st_mode)
    except OSError:
        return False


def _is_reachable_without_symlink(
    directory: str, root: str, memo: dict[tuple[str, str], bool]
) -> bool:
    cached = memo.get((root, directory))
    if cached is not None:
        return cached
    if directory == root:
        memo[root, directory] = True
        return True
    parent = directory.rpartition(os.sep)[0]
    if not parent or not directory.startswith(root + os.sep):
        memo[root, directory] = False
        _debug.logic("directory_outside_root", directory=directory, root=root)
        return False
    result = not _is_symlink(directory) and _is_reachable_without_symlink(
        parent, root, memo
    )
    memo[root, directory] = result
    return result


def _get_static_files(
    pattern: str,
    static_dir: str,
    symlink_memo: dict[tuple[str, str], bool] | None = None,
) -> list[tuple[str, float]]:
    result: set[tuple[str, float]] = set()
    if symlink_memo is None:
        symlink_memo = {}
    skipped_ext = 0  # debuglog
    skipped_stat = 0  # debuglog
    for file in glob(pattern, recursive=True):
        if file.rsplit(".", 1)[-1] not in ASSET_EXTENSIONS:
            skipped_ext += 1  # debuglog
            continue
        try:
            status = os.lstat(file)
        except OSError:
            skipped_stat += 1  # debuglog
            continue
        directory = file.rpartition(os.sep)[0]
        if S_ISLNK(status.st_mode) or not _is_reachable_without_symlink(
            directory, static_dir, symlink_memo
        ):
            real = os.path.realpath(file)
            if real != static_dir and not real.startswith(static_dir + os.sep):
                _logger.warning(
                    "IrAsset: %r matched %r, which links out of the addon's "
                    "static/ directory (to %r); skipped.",
                    pattern,
                    file,
                    real,
                )
                _debug.logic("symlink_escapes_static", file=file, real=real)
                continue
            try:
                status = os.lstat(real)
            except OSError:
                skipped_stat += 1  # debuglog
                continue
            _debug.logic("symlink_followed", file=file, real=real)
            file = real
        result.add((file, status.st_mtime))
    _debug.perf.count(
        "static_files_globbed",
        pattern=pattern,
        files=len(result),
        skipped_ext=skipped_ext,
        skipped_stat=skipped_stat,
    )
    return sorted(result)


class Anchor:
    __slots__ = ("index",)

    def __init__(self, index: int) -> None:
        self.index = index

    def __repr__(self) -> str:
        return f"Anchor({self.index})"


class AssetPaths:
    def __init__(self) -> None:
        self.list: list[AssetEntry] = []
        self.memo: set[str] = set()
        self.anchors: list[Anchor] = []

    def add_anchor(self) -> Anchor:
        anchor = Anchor(len(self.list))
        self.anchors.append(anchor)
        return anchor

    def remove_anchor(self, anchor: Anchor) -> None:
        self.anchors.remove(anchor)

    def get_index_of_first(self, paths: Sequence[str], bundle: str) -> int:
        for path in paths:
            if path in self.memo:
                for index, asset in enumerate(self.list):
                    if asset.path == path:
                        return index
                _debug.logic("asset_state_inconsistent", bundle=bundle, path=path)
                raise RuntimeError(
                    f"Inconsistent asset state: {path!r} in memo but not in list"
                )
        _debug.logic("target_not_found", bundle=bundle, candidates=len(paths))
        raise self._prepare_not_found_error(
            paths[0] if len(paths) == 1 else list(paths), bundle
        )

    def append_paths(self, paths: Sequence[ResolvedPath], bundle: str) -> None:
        self.insert_paths(paths, bundle, len(self.list))

    def insert_paths(
        self, paths: Sequence[ResolvedPath], bundle: str, index: int
    ) -> None:
        to_insert = []
        for path, full_path, last_modified in paths:
            if path not in self.memo:
                to_insert.append(AssetEntry(path, full_path, bundle, last_modified))
                self.memo.add(path)
        if not to_insert:
            _debug.logic("insert_paths_all_present", bundle=bundle, paths=len(paths))
            return
        self.list[index:index] = to_insert
        for anchor in self.anchors:
            if anchor.index > index:
                anchor.index += len(to_insert)
        _debug.pipeline(
            "paths_inserted",
            bundle=bundle,
            index=index,
            inserted=len(to_insert),
            duplicates=len(paths) - len(to_insert),
            total=len(self.list),
        )

    def remove_paths(
        self, paths_to_remove: Sequence[ResolvedPath], bundle: str, strict: bool = True
    ) -> None:
        requested = [path for path, _full_path, _last_modified in paths_to_remove]
        present = {path for path in requested if path in self.memo}
        if not present:
            if requested and strict:
                _debug.logic(
                    "remove_paths_missing", bundle=bundle, requested=len(requested)
                )
                raise self._prepare_not_found_error(requested, bundle)
            return

        absent = [path for path in requested if path not in self.memo]
        if absent and strict:
            _logger.warning(
                "REMOVE in bundle %r ignored path(s) %s not present in the "
                "bundle (removed %s). The ignored paths are likely stale "
                "(renamed/deleted) or an over-matching glob.",
                bundle,
                absent,
                sorted(present),
            )
        kept = []
        dropped_indexes = []
        for index, asset in enumerate(self.list):
            if asset.path in present:
                dropped_indexes.append(index)
            else:
                kept.append(asset)
        self.list[:] = kept
        self.memo.difference_update(present)
        for anchor in self.anchors:
            anchor.index -= sum(1 for index in dropped_indexes if index < anchor.index)
        _debug.pipeline(
            "paths_removed",
            bundle=bundle,
            removed=len(dropped_indexes),
            absent=len(absent),
            strict=strict,
            total=len(self.list),
        )

    def _prepare_not_found_error(
        self, path: str | list[str], bundle: str
    ) -> ValueError:
        return ValueError(f"File(s) {path} not found in bundle {bundle}")


class BundleFrame(NamedTuple):
    bundle: str
    anchor: Anchor
    seen: tuple[str, ...]


class AssetDirective(NamedTuple):
    directive: str
    target: str | None
    path: str
    origin: str


class BundleWalk:
    def __init__(
        self,
        resolve: Callable[[str], Sequence[ResolvedPath]],
        prepare_directives: Callable[[str], Sequence[AssetDirective]],
    ) -> None:
        self.resolve = resolve
        self.prepare_directives = prepare_directives
        self.paths = AssetPaths()
        self.walked: set[str] = set()

    def walk(self, bundle: str, seen: tuple[str, ...] = ()) -> None:
        if bundle in seen:
            _debug.logic("bundle_circular", bundle=bundle, depth=len(seen))
            raise ValueError(
                f"Circular assets bundle declaration: {' > '.join([*seen, bundle])}"
            )
        if bundle in self.walked:
            _logger.debug(
                "Bundle %r already walked in this traversal; skipping re-include.",
                bundle,
            )
            _debug.logic("bundle_already_walked", bundle=bundle, depth=len(seen))
            return
        self.walked.add(bundle)

        frame = BundleFrame(bundle, self.paths.add_anchor(), seen)
        directives = 0  # debuglog
        for directive in self.prepare_directives(bundle):
            directives += 1  # debuglog
            self.apply_directive(frame, directive)
        self.paths.remove_anchor(frame.anchor)
        _debug.pipeline(
            "bundle_walked", bundle=bundle, depth=len(seen), directives=directives
        )

    def apply_directive(self, frame: BundleFrame, entry: AssetDirective) -> None:
        try:
            self._apply_directive(frame, entry)
        except AssetDirectiveError:
            raise
        except ValueError as exc:
            _debug.logic(
                "directive_failed",
                bundle=frame.bundle,
                directive=entry.directive,
                error=type(exc).__name__,
            )
            raise AssetDirectiveError(
                f"{exc} — raised by {entry.origin}, declared for bundle "
                f"{frame.bundle!r}"
            ) from exc

    def _apply_directive(self, frame: BundleFrame, entry: AssetDirective) -> None:
        directive, target, path_def = entry.directive, entry.target, entry.path
        bundle = frame.bundle
        if directive == INCLUDE_DIRECTIVE:
            _debug.pipeline("bundle_included", bundle=bundle, included=path_def)
            self.walk(path_def, (*frame.seen, bundle))
            return

        asset_paths = self.paths
        paths = self.resolve(path_def)

        targets: list[str] = []
        if directive in DIRECTIVES_WITH_TARGET:
            targets = self._get_target_paths(directive, target, path_def, bundle)
            if not targets:
                return

        _debug.logic(
            "directive_applied",
            bundle=bundle,
            directive=directive,
            path=path_def,
            resolved=len(paths),
            targets=len(targets),
        )
        if directive == APPEND_DIRECTIVE:
            asset_paths.append_paths(paths, bundle)
        elif directive == PREPEND_DIRECTIVE:
            self._warn_stranded_sources(
                directive, paths, targets, bundle, target, frame.anchor.index, 0
            )
            asset_paths.insert_paths(paths, bundle, frame.anchor.index)
        elif directive in (AFTER_DIRECTIVE, BEFORE_DIRECTIVE):
            offset = 1 if directive == AFTER_DIRECTIVE else 0
            target_index = asset_paths.get_index_of_first(targets, bundle)
            self._warn_stranded_sources(
                directive, paths, targets, bundle, target, target_index, offset
            )
            asset_paths.insert_paths(paths, bundle, target_index + offset)
        elif directive == REMOVE_DIRECTIVE:
            if not paths:
                _logger.warning(
                    "REMOVE directive in bundle %r had no effect: path %r "
                    "resolved to nothing. Either the path is stale (file "
                    "renamed / deleted) and the directive can be dropped, "
                    "or the glob is wrong.",
                    bundle,
                    path_def,
                )
                _debug.logic("remove_no_effect", bundle=bundle, path=path_def)
                return
            asset_paths.remove_paths(
                paths, bundle, strict=not is_wildcard_glob(path_def)
            )
        elif directive == REPLACE_DIRECTIVE:
            self._replace_paths(
                paths, targets, bundle, strict=not is_wildcard_glob(target or "")
            )
        else:
            msg = f"Unexpected directive: {directive!r}"
            _debug.logic("directive_unknown", bundle=bundle, directive=directive)
            raise ValueError(msg)

    def _get_target_paths(
        self, directive: str, target: str | None, path_def: str, bundle: str
    ) -> list[str]:
        if not target:
            _logger.warning(
                "Asset directive %r in bundle %r has no target — "
                "directive skipped. Path was %r.",
                directive,
                bundle,
                path_def,
            )
            _debug.logic(
                "target_skipped", bundle=bundle, directive=directive, reason="no_target"
            )
            return []
        target_paths = self.resolve(target)
        if not target_paths:
            _logger.warning(
                "Asset directive %r in bundle %r references target %r "
                "that resolved to nothing — directive skipped. Path was %r.",
                directive,
                bundle,
                target,
                path_def,
            )
            _debug.logic(
                "target_skipped",
                bundle=bundle,
                directive=directive,
                target=target,
                reason="unresolved",
            )
            return []
        return [resolved[0] for resolved in target_paths]

    def _warn_stranded_sources(
        self,
        directive: str,
        paths: Sequence[ResolvedPath],
        targets: Sequence[str],
        bundle: str,
        target: str | None,
        pivot: int,
        offset: int,
    ) -> None:
        # a source already on the side of the pivot the directive asks for
        # is not stranded: the ordering it states already holds
        present = {
            path
            for path, _full_path, _last_modified in paths
            if path in self.paths.memo and path not in targets
        }
        if not present:
            return
        positions = {
            asset.path: index
            for index, asset in enumerate(self.paths.list)
            if asset.path in present
        }
        stranded = sorted(
            path
            for path in present
            if (positions[path] < pivot if offset else positions[path] > pivot)
        )
        if stranded:
            _logger.warning(
                "Asset directive %r in bundle %r: source(s) %s are already "
                "present and were NOT repositioned (%s only places new files; "
                "use 'replace' to move an existing one). Target was %r.",
                directive,
                bundle,
                stranded,
                directive,
                target,
            )
            _debug.logic(
                "stranded_sources",
                bundle=bundle,
                directive=directive,
                stranded=len(stranded),
            )

    def _replace_paths(
        self,
        paths: Sequence[ResolvedPath],
        targets: list[str],
        bundle: str,
        strict: bool = True,
    ) -> None:
        asset_paths = self.paths
        target_set = set(targets)
        if not paths:
            _logger.debug(
                "REPLACE source resolved to nothing in bundle %s, "
                "target(s) %s removed without replacement",
                bundle,
                targets,
            )
            _debug.logic("replace_without_source", bundle=bundle, targets=len(targets))

        surviving = {entry[0] for entry in paths if entry[0] in target_set}
        sources = [entry for entry in paths if entry[0] not in target_set]
        present = [entry for entry in sources if entry[0] in asset_paths.memo]
        if present:
            asset_paths.remove_paths(present, bundle)
        target_index = asset_paths.get_index_of_first(targets, bundle)
        asset_paths.insert_paths(sources, bundle, target_index)
        doomed = [
            ResolvedPath(path, None, None) for path in targets if path not in surviving
        ]
        _debug.pipeline(
            "replace_paths",
            bundle=bundle,
            sources=len(sources),
            moved=len(present),
            surviving=len(surviving),
            removed=len(doomed),
        )
        if doomed:
            asset_paths.remove_paths(doomed, bundle, strict=strict)


def _prepare_origin_manifest(command: Any, addon: str) -> str:
    return f"{command!r} in the manifest of addon {addon!r}"


def _prepare_origin_record(name: str, record_id: Any, directive: str, path: str) -> str:
    return (
        f"ir.asset record {name!r} (id {record_id}, directive {directive!r}, "
        f"path {path!r})"
    )
