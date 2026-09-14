from __future__ import annotations

from pathlib import Path

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def stub_layout(
    stubs: dict[str, str], alias_flags: list[str], odoo_root: Path
) -> tuple[dict[str, Path], dict[str, set[str]], set[str]]:
    addon_roots = {}
    for flag in alias_flags:
        spec, _, target = flag.removeprefix("--alias:").partition("=")
        if spec.startswith("@") and "/" not in spec:
            addon_roots[spec] = odoo_root / target.removeprefix("./")

    occupied: dict[str, set[str]] = {}
    must_be_real: set[str] = set()
    for spec in stubs:
        parent_rel, _, name = spec.lstrip("@").rpartition("/")
        occupied.setdefault(parent_rel, set()).add(f"{name}.js")
        while parent_rel:
            must_be_real.add(parent_rel)
            parent_rel = parent_rel.rpartition("/")[0]
    return addon_roots, occupied, must_be_real


def stub_sibling_dir(spec: str, addon_roots: dict[str, Path]) -> Path | None:
    addon, _, rest = spec.partition("/")
    root = addon_roots.get(addon)
    if root is None:
        return None
    candidate = root.joinpath(*rest.split("/"))
    return candidate if candidate.is_dir() else None


def check_inside_mirror(path: Path, stub_root: Path) -> None:
    resolved = path.parent.resolve()
    if not resolved.is_relative_to(stub_root.resolve()):
        raise RuntimeError(
            f"refusing to write the ESM shim {path.name!r} outside the stub "
            f"mirror: {resolved} is not under {stub_root}"
        )


def mirror_dir(
    mirror: Path,
    real_dir: Path,
    rel: str,
    occupied: dict[str, set[str]],
    must_be_real: set[str],
) -> None:
    mirror.mkdir(parents=True, exist_ok=True)
    taken: frozenset[str] | set[str] = occupied.get(rel, frozenset())
    for entry in real_dir.iterdir():
        if entry.name in taken:
            continue
        entry_rel = f"{rel}/{entry.name}"
        target = mirror / entry.name
        if entry_rel in must_be_real and entry.is_dir():
            mirror_dir(target, entry, entry_rel, occupied, must_be_real)
        elif not target.is_symlink() and not target.exists():
            target.symlink_to(entry)


def write_stubs(
    stub_root: Path,
    stubs: dict[str, str],
    addon_roots: dict[str, Path],
    occupied: dict[str, set[str]],
    must_be_real: set[str],
) -> list[tuple[str, Path]]:
    written = []
    for spec in sorted(stubs):
        rel = spec.lstrip("@")
        stub_path = stub_root / rel
        check_inside_mirror(stub_path, stub_root)
        stub_path.parent.mkdir(parents=True, exist_ok=True)
        real_dir = stub_sibling_dir(spec, addon_roots)
        if real_dir is not None and not stub_path.exists():
            if rel in must_be_real:
                mirror_dir(stub_path, real_dir, rel, occupied, must_be_real)
            else:
                stub_path.symlink_to(real_dir, target_is_directory=True)
        shim_path = stub_root / f"{rel}.js"
        check_inside_mirror(shim_path, stub_root)
        shim_path.write_text(stubs[spec], encoding="utf-8")
        written.append((spec, stub_path))
    _debug.pipeline(
        "esbuild_stubs.written",
        root=str(stub_root),
        stubs=len(written),
        addon_roots=len(addon_roots),
        mirrored_dirs=len(must_be_real),
    )
    return written


def write_stub_mirror(
    stub_root: Path,
    stubs: dict[str, str],
    alias_flags: list[str],
    odoo_root: Path,
) -> list[str]:
    addon_roots, occupied, must_be_real = stub_layout(stubs, alias_flags, odoo_root)
    return [
        f"--alias:{spec}={stub_path}"
        for spec, stub_path in write_stubs(
            stub_root, stubs, addon_roots, occupied, must_be_real
        )
    ]


def mirror_aliases(
    native_modules: list,
    alias_flags: list[str],
    stubs: dict[str, str],
    tmp_dir: str,
    odoo_root: Path,
) -> tuple[list[str], dict[str, Path]]:
    addons = {
        (asset.url or "").lstrip("/").partition("/static/src/")[0]
        for asset in native_modules
        if "/static/src/" in (asset.url or "")
    }
    addons |= {spec.lstrip("@").partition("/")[0] for spec in stubs}
    if not addons:
        _debug.logic("esbuild_stubs.mirror_skipped", modules=len(native_modules))
        return alias_flags, {}
    stub_root = Path(tmp_dir) / "mirror"
    addon_roots, occupied, must_be_real = stub_layout(stubs, alias_flags, odoo_root)
    write_stubs(stub_root, stubs, addon_roots, occupied, must_be_real)
    mirrored: dict[str, Path] = {}
    for addon in sorted(addons):
        real_dir = addon_roots.get(f"@{addon}")
        if real_dir is None or not real_dir.is_dir():
            continue
        mirror = stub_root / addon
        mirror_dir(mirror, real_dir, addon, occupied, must_be_real)
        # Keep each addon's static siblings separate: @addon/../tests and
        # relative ../lib imports must not resolve into another addon's tree.
        static_root = Path(tmp_dir) / "layout" / addon / "static"
        static_root.mkdir(parents=True, exist_ok=True)
        source_root = static_root / "src"
        mirror.rename(source_root)
        for sibling in real_dir.parent.iterdir():
            if sibling != real_dir:
                (static_root / sibling.name).symlink_to(
                    sibling, target_is_directory=sibling.is_dir()
                )
        mirrored[addon] = source_root
    kept = [
        flag
        for flag in alias_flags
        if flag.removeprefix("--alias:").partition("=")[0].lstrip("@") not in mirrored
    ]
    _debug.pipeline(
        "esbuild_stubs.mirrored",
        addons=sorted(addons),
        mirrored=len(mirrored),
        aliases_kept=len(kept),
        stubs=len(stubs),
    )
    return kept + [f"--alias:@{addon}={path}" for addon, path in mirrored.items()], (
        mirrored
    )


def stub_aliases(
    alias_flags: list[str],
    secondary_parent_stubs: dict[str, str] | None,
    tmp_dir: str,
    odoo_root: Path,
) -> list[str]:
    if not secondary_parent_stubs:
        return alias_flags
    stub_flags = write_stub_mirror(
        Path(tmp_dir) / "stubs", secondary_parent_stubs, alias_flags, odoo_root
    )
    if not stub_flags:
        return alias_flags
    stubbed = {flag.removeprefix("--alias:").partition("=")[0] for flag in stub_flags}
    return [
        flag
        for flag in alias_flags
        if flag.removeprefix("--alias:").partition("=")[0] not in stubbed
    ] + stub_flags
