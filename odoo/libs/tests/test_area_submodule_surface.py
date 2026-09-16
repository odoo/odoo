import ast
import functools
import json
import pathlib
import subprocess
import sys
import textwrap
import types

import pytest

_LIBS = pathlib.Path(__file__).resolve().parents[1]
_REPO = _LIBS.parents[1]


DECLARED_SUBMODULE_EXPORTS: dict[str, set[str]] = {
    "documents": {
        "coerce",
        "document",
        "format",
        "formats",
        "guess",
        "layout",
        "readers",
        "representations",
        "writers",
    },
    "filesystem": {"appdirs", "mimetypes", "osutil"},
    "web": {"urls"},
}

KNOWN_ACCIDENTAL_LEAF_IMPORTS: dict[str, str] = {
    "datetime.tz": "safe_eval and others take the tz module wholesale",
    "numbers.float_utils": "float helpers imported as a module rather than by name",
    "_field_access._fallback": (
        "the pure-Python twins the field-access facade resolves to when odoo_rust "
        "is absent (odoo/libs/accel.py is the seam)"
    ),
    "profiling.nplusone": "profiler wiring",
    "profiling.orm_profiler": "profiler wiring",
}


def _areas() -> list[str]:
    return sorted(
        p.name
        for p in _LIBS.iterdir()
        if p.is_dir() and (p / "__init__.py").is_file() and p.name != "tests"
    )


@functools.cache
def _runtime_surface() -> dict[str, dict[str, list[str]]]:
    program = textwrap.dedent(
        """
        import importlib, json, pathlib, sys, types
        libs = pathlib.Path(sys.argv[1])
        out = {}
        for p in sorted(libs.iterdir()):
            if not (p.is_dir() and (p / "__init__.py").is_file()) or p.name == "tests":
                continue
            try:
                mod = importlib.import_module("odoo.libs." + p.name)
            except Exception:
                continue
            for f in sorted(p.glob("*.py")):
                if f.stem != "__init__":
                    try:
                        importlib.import_module("odoo.libs.%s.%s" % (p.name, f.stem))
                    except Exception:
                        pass
            exported = set(getattr(mod, "__all__", []))
            declared, accidental = [], []
            prefix = "odoo.libs.%s." % p.name
            for name, value in vars(mod).items():
                if not isinstance(value, types.ModuleType):
                    continue
                if not getattr(value, "__name__", "").startswith(prefix):
                    continue
                (declared if name in exported else accidental).append(name)
            out[p.name] = {
                "declared": sorted(declared),
                "accidental": sorted(accidental),
                "exported": sorted(exported),
            }
        json.dump(out, sys.stdout)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program, str(_LIBS)],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=_REPO,
        check=True,
    )
    return json.loads(result.stdout)


def _submodule_attributes(area: str) -> tuple[set[str], set[str]]:
    entry = _runtime_surface().get(area, {"declared": [], "accidental": []})
    return set(entry["declared"]), set(entry["accidental"])


def _leaf_imports_via_area() -> dict[str, int]:
    is_module: set[str] = set()
    for area in _areas():
        declared, accidental = _submodule_attributes(area)
        is_module |= {f"{area}.{n}" for n in declared | accidental}

    counts: dict[str, int] = {}
    for root in (_REPO / "odoo", _REPO / "addons"):
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError, UnicodeDecodeError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level or not node.module:
                    continue
                if (
                    not node.module.startswith("odoo.libs.")
                    or node.module.count(".") != 2
                ):
                    continue
                area = node.module.split(".")[2]
                for alias in node.names:
                    key = f"{area}.{alias.name}"
                    if key in is_module:
                        counts[key] = counts.get(key, 0) + 1
    return counts


def test_declared_submodule_exports_are_pinned():
    actual = {a: _submodule_attributes(a)[0] for a in _areas()}
    actual = {a: names for a, names in actual.items() if names}
    assert actual == DECLARED_SUBMODULE_EXPORTS, (
        f"an area changed which submodules it publishes in __all__: {actual}. "
        f"Publishing a submodule is a real interface decision -- it makes the "
        f"implementation module part of the area's contract, which is the "
        f"opposite of what ARCHITECTURE.md says the libs boundary is."
    )


def _accidental_from_disk(area: str) -> set[str]:
    entry = _runtime_surface().get(area, {})
    exported = set(entry.get("exported", ()))
    on_disk = {p.stem for p in (_LIBS / area).glob("*.py") if p.stem != "__init__"}
    return on_disk - exported


def test_accidental_submodule_surface_is_bounded():
    total = sum(len(_accidental_from_disk(a)) for a in _areas())
    assert total <= 41, (
        f"accidental submodule surface grew to {total} (was 41). Each one is a "
        f"leaf module importable as `from odoo.libs.<area> import <name>`, "
        f"which libs_facade_check cannot see."
    )


def test_leaf_imports_through_accidental_surface_are_pinned():
    counts = _leaf_imports_via_area()
    declared_keys = {
        f"{area}.{name}"
        for area, names in DECLARED_SUBMODULE_EXPORTS.items()
        for name in names
    }
    accidental_hits = {k: v for k, v in counts.items() if k not in declared_keys}
    assert set(accidental_hits) == set(KNOWN_ACCIDENTAL_LEAF_IMPORTS), (
        f"leaf-module imports through ACCIDENTAL area surface changed: "
        f"{sorted(accidental_hits)} vs pinned "
        f"{sorted(KNOWN_ACCIDENTAL_LEAF_IMPORTS)}. These are exactly the "
        f"imports libs_facade_check is blind to; import the area and use the "
        f"symbol, or promote the submodule into __all__ deliberately."
    )


def _loose_modules() -> list[pathlib.Path]:
    return sorted(
        p
        for p in _LIBS.glob("*.py")
        if p.stem != "__init__" and not p.stem.startswith("_")
    )


VENDORED = "_vendor"
"""Third-party code, kept as it was received; its surface is not ours to declare."""


def _area_submodules() -> list[pathlib.Path]:
    return sorted(
        p
        for p in _LIBS.glob("*/*.py")
        if p.stem != "__init__" and "tests" not in p.parts and VENDORED not in p.parts
    )


def _declares_all(path: pathlib.Path) -> bool:
    return "__all__" in {
        t.id
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    }


def test_every_loose_top_level_module_declares_all():
    missing = [p.name for p in _loose_modules() if not _declares_all(p)]
    assert missing == [], (
        f"loose top-level modules in libs/ with no __all__: {missing}. "
        f"Every area package declares one; a module that does not publishes its "
        f"entire namespace by accident, including its imports."
    )


def test_every_area_submodule_declares_all():
    missing = [
        str(p.relative_to(_LIBS)) for p in _area_submodules() if not _declares_all(p)
    ]
    assert missing == [], (
        f"area submodules with no __all__: {missing}. Declare the names the "
        f"module means to publish; imports are not part of them."
    )


UNPROMOTED_SUBMODULE_EXPORTS: dict[str, set[str]] = {
    "_field_access/_fallback.py": {
        "batch_cache_fill",
        "batch_cache_filter",
        "batch_cache_get",
        "batch_group_ids",
        "sort_ids_by_cache",
        "to_prefetch_ids",
    },
    "filesystem/appdirs.py": {
        "AppDirs",
        "site_config_dir",
        "site_data_dir",
        "user_cache_dir",
        "user_config_dir",
        "user_data_dir",
        "user_log_dir",
    },
    "filesystem/osutil.py": {
        "WINDOWS_RESERVED",
        "clean_filename",
        "is_running_as_nt_service",
        "zip_dir",
    },
    "filesystem/which.py": {"which_files"},
}


def _all_of(path: pathlib.Path) -> set[str] | None:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            try:
                return set(ast.literal_eval(node.value))
            except ValueError:
                return None
    return None


def test_every_submodule_export_is_reachable_from_its_area():
    drifted: dict[str, list[str]] = {}
    for path in _area_submodules():
        rel = str(path.relative_to(_LIBS))
        names = _all_of(path)
        if names is None:
            continue
        area_names = _all_of(_LIBS / path.parent.name / "__init__.py") or set()
        extra = names - area_names - UNPROMOTED_SUBMODULE_EXPORTS.get(rel, set())
        if extra:
            drifted[rel] = sorted(extra)
    assert drifted == {}, (
        f"submodules publishing names their area does not re-export: {drifted}. "
        f"Either promote the name into the area's __all__ -- which is what makes "
        f"it public -- or take it out of the submodule's, which is not a surface "
        f"anyone imports through. Pin it in UNPROMOTED_SUBMODULE_EXPORTS only "
        f"when it is deliberately reachable by its full path and no other way."
    )


def test_the_unpromoted_pin_is_not_stale():
    stale: dict[str, list[str]] = {}
    for rel, pinned in UNPROMOTED_SUBMODULE_EXPORTS.items():
        names = _all_of(_LIBS / rel) or set()
        if gone := sorted(pinned - names):
            stale[rel] = gone
    assert stale == {}, f"pinned names that are no longer published: {stale}"


def test_the_loose_module_scan_is_not_vacuous():
    names = {p.name for p in _loose_modules()}
    assert len(names) >= 10, f"only found {len(names)} loose modules: {names}"
    assert "lru.py" in names and "facade.py" in names


def test_the_area_submodule_scan_is_not_vacuous():
    names = {str(p.relative_to(_LIBS)) for p in _area_submodules()}
    assert len(names) >= 30, f"only found {len(names)} area submodules: {names}"
    assert "sql/builder.py" in names and "email/parsing.py" in names
    assert not any(p.startswith(f"{VENDORED}/") for p in names), (
        "vendored modules are exempt and must not be scanned"
    )


def test_the_scan_is_not_vacuous():
    assert len(_areas()) >= 15
    assert _leaf_imports_via_area(), "found no leaf-via-area imports at all"


def test_disk_presence_alone_would_misclassify():
    assert (_LIBS / "json" / "fast_clone.py").is_file()
    from odoo.libs import json as json_area

    assert not isinstance(json_area.fast_clone, types.ModuleType), (
        "odoo.libs.json.fast_clone is now a module; the shadowing that makes a "
        "disk-presence rule unsafe may be gone, in which case libs_facade_check "
        "could grow a static version of this check."
    )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
