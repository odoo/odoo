from __future__ import annotations

from pathlib import Path

ODOO_MARKER = "odoo-bin"

SIBLING_REPOS: tuple[str, ...] = ("enterprise", "agromarin", "design-themes")


def find_odoo_root(start: Path, *, tool: str = "tooling") -> Path:

    for candidate in (start, *start.parents):
        if (candidate / ODOO_MARKER).is_file():
            return candidate
    raise SystemExit(
        f"{tool}: no `{ODOO_MARKER}` in any parent of {start} — cannot locate "
        f"the odoo checkout root. Refusing to run against a guessed tree."
    )


def _supplies_workspace_resources(path: Path) -> bool:

    try:
        if any(path.glob("*.conf")):
            return True
        return any(
            (child / "bin" / "python").is_file()
            for child in path.iterdir()
            if child.is_dir()
        )
    except OSError:
        return False


def in_workspace(odoo_root: Path) -> bool:

    if odoo_root.parent.name == "addons":
        return True
    return _supplies_workspace_resources(odoo_root.parent)


def find_workspace(odoo_root: Path) -> Path | None:

    if not in_workspace(odoo_root):
        return None
    return (
        odoo_root.parents[1] if odoo_root.parent.name == "addons" else odoo_root.parent
    )


def in_full_workspace(odoo_root: Path) -> bool:
    workspace = find_workspace(odoo_root)
    return workspace is not None and all(
        (workspace / name).is_dir() for name in SIBLING_REPOS
    )


def sibling_repos_root(odoo_root: Path) -> Path:

    return odoo_root.parent


def sibling_repo_paths(odoo_root: Path) -> list[Path]:
    workspace = find_workspace(odoo_root)
    if workspace is None:
        return []
    return [
        path for path in (workspace / name for name in SIBLING_REPOS) if path.is_dir()
    ]
