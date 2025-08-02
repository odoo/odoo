""":module: watchdog.utils.patterns
:synopsis: Common wildcard searching/filtering functionality for files.
:author: boris.staletic@gmail.com (Boris Staletic)
:author: yesudeep@gmail.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)
"""

from __future__ import annotations

# Non-pure path objects are only allowed on their respective OS's.
# Thus, these utilities require "pure" path objects that don't access the filesystem.
# Since pathlib doesn't have a `case_sensitive` parameter, we have to approximate it
# by converting input paths to `PureWindowsPath` and `PurePosixPath` where:
#   - `PureWindowsPath` is always case-insensitive.
#   - `PurePosixPath` is always case-sensitive.
# Reference: https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match
from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


def _match_path(
    raw_path: str,
    included_patterns: set[str],
    excluded_patterns: set[str],
    *,
    case_sensitive: bool,
) -> bool:
    """Internal function same as :func:`match_path` but does not check arguments."""
    path: PurePosixPath | PureWindowsPath
    if case_sensitive:
        path = PurePosixPath(raw_path)
    else:
        included_patterns = {pattern.lower() for pattern in included_patterns}
        excluded_patterns = {pattern.lower() for pattern in excluded_patterns}
        path = PureWindowsPath(raw_path)

    common_patterns = included_patterns & excluded_patterns
    if common_patterns:
        error = f"conflicting patterns `{common_patterns}` included and excluded"
        raise ValueError(error)

    return any(path.match(p) for p in included_patterns) and not any(path.match(p) for p in excluded_patterns)


def filter_paths(
    paths: list[str],
    *,
    included_patterns: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
    case_sensitive: bool = True,
) -> Iterator[str]:
    """Filters from a set of paths based on acceptable patterns and
    ignorable patterns.
    :param paths:
        A list of path names that will be filtered based on matching and
        ignored patterns.
    :param included_patterns:
        Allow filenames matching wildcard patterns specified in this list.
        If no pattern list is specified, ["*"] is used as the default pattern,
        which matches all files.
    :param excluded_patterns:
        Ignores filenames matching wildcard patterns specified in this list.
        If no pattern list is specified, no files are ignored.
    :param case_sensitive:
        ``True`` if matching should be case-sensitive; ``False`` otherwise.
    :returns:
        A list of pathnames that matched the allowable patterns and passed
        through the ignored patterns.
    """
    included = set(["*"] if included_patterns is None else included_patterns)
    excluded = set([] if excluded_patterns is None else excluded_patterns)

    for path in paths:
        if _match_path(path, included, excluded, case_sensitive=case_sensitive):
            yield path


def match_any_paths(
    paths: list[str],
    *,
    included_patterns: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
    case_sensitive: bool = True,
) -> bool:
    """Matches from a set of paths based on acceptable patterns and
    ignorable patterns.
    See ``filter_paths()`` for signature details.
    """
    return any(
        filter_paths(
            paths,
            included_patterns=included_patterns,
            excluded_patterns=excluded_patterns,
            case_sensitive=case_sensitive,
        ),
    )
