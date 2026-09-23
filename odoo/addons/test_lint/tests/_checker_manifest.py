import ast
import re
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path

from lxml import etree

if __package__:
    from . import _sort_manifests
else:
    import _sort_manifests

KNOWN_KEYS = frozenset(_sort_manifests.MANIFEST_KEY_ORDER)

KNOWN_LICENSES = frozenset(
    {
        "GPL-2",
        "GPL-2 or any later version",
        "GPL-3",
        "GPL-3 or any later version",
        "AGPL-3",
        "LGPL-3",
        "Other OSI approved licence",
        "OEEL-1",
        "OPL-1",
        "Other proprietary",
    }
)

STRING_KEYS = frozenset(
    {
        "name",
        "category",
        "summary",
        "description",
        "author",
        "maintainer",
        "website",
        "url",
        "support",
        "live_test_url",
        "currency",
        "icon",
        "license",
        "post_load",
        "pre_init_hook",
        "post_init_hook",
        "uninstall_hook",
    }
)

STRING_LIST_KEYS = frozenset(
    {
        "contributors",
        "maintainers",
        "depends",
        "countries",
        "data",
        "demo",
        "oca_data_manual",
        "images",
        "cloc_exclude",
    }
)

HOOK_KEYS = ("post_load", "pre_init_hook", "post_init_hook", "uninstall_hook")

EXTERNAL_DEPENDENCY_KINDS = frozenset({"python", "bin", "apt"})

ASSET_DIRECTIVES_WITH_TARGET = frozenset({"after", "before", "replace"})
ASSET_DIRECTIVES = ASSET_DIRECTIVES_WITH_TARGET | {
    "append",
    "prepend",
    "remove",
    "include",
}

_COUNTRY_CODE_RE = re.compile(r"^[a-zA-Z]{2}$")
_REQUIREMENT_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def requirement_name(spec: str) -> str:
    match = _REQUIREMENT_NAME_RE.match(spec)
    return match[1].lower().replace("_", "-") if match else spec


CATEGORY_DATA_FILE = "ir_module_category_data.xml"


def category_roots(addon_dirs: Mapping[str, Path]) -> frozenset[str]:
    roots = set()
    for addon in addon_dirs.values():
        data = addon / "data" / CATEGORY_DATA_FILE
        if not data.is_file():
            continue
        for record in etree.parse(str(data)).getroot().iter("record"):
            if record.get("model") != "ir.module.category":
                continue
            if record.find("field[@name='parent_id']") is not None:
                continue
            xml_id = (record.get("id") or "").removeprefix("base.")
            if xml_id.startswith("module_category_"):
                roots.add(xml_id)
    return frozenset(roots)


def _bound_names(init: Path) -> set[str] | None:
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))
    except OSError, SyntaxError:
        return set()
    names: set[str] = set()
    for node in tree.body:
        match node:
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                names.add(node.name)
            case ast.Assign(targets=targets):
                names.update(t.id for t in targets if isinstance(t, ast.Name))
            case ast.AnnAssign(target=ast.Name(id=name)):
                names.add(name)
            case ast.Import(names=aliases):
                names.update((a.asname or a.name).split(".")[0] for a in aliases)
            case ast.ImportFrom(names=aliases):
                if any(a.name == "*" for a in aliases):
                    return None
                names.update(a.asname or a.name for a in aliases)
    return names


class ManifestChecker:
    def __init__(self, *, addon_dirs: Mapping[str, Path], series: str) -> None:
        self.addon_dirs = addon_dirs
        self.category_roots = category_roots(addon_dirs)
        self.series = series

    def addon_dir(self, name: str) -> Path | None:
        return self.addon_dirs.get(name)

    def findings(self, module: str, data: Mapping, module_dir: Path) -> list[str]:
        return [f"{module}: {text}" for text in self._iter(module, data, module_dir)]

    def _iter(self, module: str, data: Mapping, module_dir: Path) -> Iterator[str]:
        yield from self._keys(data)
        yield from self._types(data)
        yield from self._name(data)
        yield from self._version(data)
        yield from self._license(data)
        yield from self._category(data)
        yield from self._website(data)
        yield from self._depends(module, data)
        yield from self._auto_install(data)
        yield from self._external_dependencies(data)
        yield from self._countries(module, data)
        yield from self._files(data, module_dir)
        yield from self._icon(data)
        yield from self._hooks(data, module_dir)
        yield from self._assets(data)

    def _keys(self, data: Mapping) -> Iterator[str]:
        for key in data:
            if key in _sort_manifests.DEPRECATED_KEYS:
                replacement = _sort_manifests.DEPRECATED_KEYS[key]
                hint = f"; use `{replacement}`" if replacement else ""
                yield f"key `{key}` is deprecated and read by nothing{hint}"
            elif key not in KNOWN_KEYS:
                yield f"unknown key `{key}`"

    def _types(self, data: Mapping) -> Iterator[str]:
        from odoo.modules.module import _DEFAULT_MANIFEST

        for key, value in data.items():
            if key in STRING_KEYS:
                if not isinstance(value, str):
                    yield f"`{key}` is {type(value).__name__}, expected str"
            elif key in STRING_LIST_KEYS:
                if not isinstance(value, list) or not all(
                    isinstance(v, str) for v in value
                ):
                    yield f"`{key}` is not a list of str"
            elif key == "auto_install":
                if not isinstance(value, (bool, list, tuple, set, frozenset)):
                    yield f"`auto_install` is {type(value).__name__}, expected bool or list"
            elif key in _DEFAULT_MANIFEST:
                expected = type(_DEFAULT_MANIFEST[key])
                if type(value) is not expected and not (
                    expected is int and type(value) is int
                ):
                    yield f"`{key}` is {type(value).__name__}, expected {expected.__name__}"

    def _name(self, data: Mapping) -> Iterator[str]:
        name = data.get("name")
        if isinstance(name, str) and not name.strip():
            yield "`name` is empty"

    def _version(self, data: Mapping) -> Iterator[str]:
        version = data.get("version")
        if version is None or not isinstance(version, str):
            return
        parts = version.split(".")
        if not (2 <= len(parts) <= 5) or not all(p.isdigit() for p in parts):
            yield f"`version` {version!r} does not parse; the loader marks the module uninstallable"
        elif len(parts) > 3 and not version.startswith(self.series + "."):
            yield (
                f"`version` {version!r} belongs to another series; "
                f"the loader marks the module uninstallable"
            )

    def _license(self, data: Mapping) -> Iterator[str]:
        license_ = data.get("license")
        if isinstance(license_, str) and license_.strip() not in KNOWN_LICENSES:
            yield f"`license` {license_!r} is not one `ir.module.module` offers"

    def _category(self, data: Mapping) -> Iterator[str]:
        category = data.get("category")
        if not isinstance(category, str):
            return
        from odoo.modules.db import category_xml_id

        segments = category.split("/")
        if any(not s.strip() for s in segments):
            yield f"`category` {category!r} has an empty segment"
        elif category_xml_id(segments[:1]) not in self.category_roots:
            yield (
                f"`category` {category!r} starts a root no `{CATEGORY_DATA_FILE}` "
                f"declares"
            )

    def _website(self, data: Mapping) -> Iterator[str]:
        for key in ("website", "url", "support", "live_test_url"):
            value = data.get(key)
            if (
                isinstance(value, str)
                and value.strip()
                and not value.startswith(("http://", "https://"))
                and key != "support"
            ):
                yield f"`{key}` {value!r} is not an http(s) URL"

    def _depends(self, module: str, data: Mapping) -> Iterator[str]:
        depends = data.get("depends")
        if not isinstance(depends, list):
            return
        seen = set()
        for dep in depends:
            if not isinstance(dep, str):
                continue
            if dep == module:
                yield "`depends` names the module itself"
            elif dep in seen:
                yield f"`depends` lists {dep!r} twice"
            elif self.addon_dir(dep) is None:
                yield f"`depends` names {dep!r}, which is on no addons path"
            seen.add(dep)

    def _auto_install(self, data: Mapping) -> Iterator[str]:
        auto_install = data.get("auto_install", False)
        if isinstance(auto_install, bool):
            return
        if not isinstance(auto_install, (list, tuple, set, frozenset)):
            return
        depends = data.get("depends") if isinstance(data.get("depends"), list) else []
        for trigger in auto_install:
            if trigger not in depends:
                yield f"`auto_install` trigger {trigger!r} is not in `depends`"

    def _external_dependencies(self, data: Mapping) -> Iterator[str]:
        deps = data.get("external_dependencies")
        if deps is None:
            return
        if not isinstance(deps, dict):
            yield "`external_dependencies` is not a dict"
            return
        for kind, value in deps.items():
            if kind not in EXTERNAL_DEPENDENCY_KINDS:
                yield (
                    f"`external_dependencies` kind {kind!r} is read by nothing; "
                    f"the kinds are python, bin and apt"
                )
            elif kind == "apt":
                if not isinstance(value, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in value.items()
                ):
                    yield "`external_dependencies.apt` is not a dict of str to str"
            elif not isinstance(value, list) or not all(
                isinstance(v, str) for v in value
            ):
                yield f"`external_dependencies.{kind}` is not a list of str"
        apt = deps.get("apt")
        python = deps.get("python")
        if isinstance(apt, dict) and isinstance(python, list):
            declared = {requirement_name(p) for p in python if isinstance(p, str)}
            for dep in apt:
                if isinstance(dep, str) and requirement_name(dep) not in declared:
                    yield (
                        f"`external_dependencies.apt` names {dep!r}, which "
                        f"`external_dependencies.python` does not declare"
                    )

    def _countries(self, module: str, data: Mapping) -> Iterator[str]:
        countries = data.get("countries")
        if not isinstance(countries, list):
            return
        for code in countries:
            if isinstance(code, str) and not _COUNTRY_CODE_RE.match(code):
                yield f"`countries` entry {code!r} is not a two-letter code"
        if len(countries) == 1 and "l10n" not in module:
            yield (
                f"specific to the single country {countries[0]!r} "
                f"but has no `l10n` in its name"
            )

    def _files(self, data: Mapping, module_dir: Path) -> Iterator[str]:
        seen: dict[str, str] = {}
        for key in ("data", "demo"):
            entries = data.get(key)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, str):
                    continue
                if entry in seen:
                    yield f"`{key}` lists {entry!r} already listed under `{seen[entry]}`"
                    continue
                seen[entry] = key
                if entry.startswith(("/", "./", "../")) or "\\" in entry:
                    yield f"`{key}` entry {entry!r} is not a plain relative path"
                elif not (module_dir / entry).is_file():
                    yield f"`{key}` entry {entry!r} matches no file"
                if key == "demo" and not entry.startswith("demo/"):
                    yield f"`demo` entry {entry!r} does not live in `demo/`"
                if key == "data" and (
                    entry.startswith("demo/") or Path(entry).stem.endswith("_demo")
                ):
                    yield f"`data` entry {entry!r} is a demo file listed as data"

    def _icon(self, data: Mapping) -> Iterator[str]:
        icon = data.get("icon")
        if not isinstance(icon, str):
            return
        if not icon.strip():
            yield "`icon` is empty; drop the key"
            return
        addon, _, relative = icon.lstrip("/").partition("/")
        root = self.addon_dir(addon)
        if root is None or not relative or not (root / relative).is_file():
            yield f"`icon` {icon!r} matches no file"

    def _hooks(self, data: Mapping, module_dir: Path) -> Iterator[str]:
        hooks = [
            (key, data[key]) for key in HOOK_KEYS if isinstance(data.get(key), str)
        ]
        if not hooks:
            return
        bound = _bound_names(module_dir / "__init__.py")
        if bound is None:
            return
        for key, name in hooks:
            if not name.strip():
                yield f"`{key}` is empty; drop the key"
            elif name not in bound:
                yield f"`{key}` names {name!r}, which `__init__.py` does not bind"

    def _assets(self, data: Mapping) -> Iterator[str]:
        assets = data.get("assets")
        if assets is None:
            return
        if not isinstance(assets, dict):
            yield "`assets` is not a dict"
            return
        for bundle, entries in assets.items():
            if not isinstance(bundle, str) or "." not in bundle:
                yield f"`assets` bundle {bundle!r} is not `<module>.<bundle>`"
            if not isinstance(entries, (list, tuple, set, frozenset)):
                yield f"`assets` bundle {bundle!r} is not a list"
                continue
            for entry in entries:
                yield from self._asset_entry(bundle, entry)

    @staticmethod
    def _asset_entry(bundle: str, entry: object) -> Iterator[str]:
        if isinstance(entry, str):
            return
        if not isinstance(entry, (list, tuple)) or not entry:
            yield f"`assets` bundle {bundle!r} entry {entry!r} is neither a path nor a directive"
            return
        directive, *operands = entry
        if directive not in ASSET_DIRECTIVES:
            yield f"`assets` bundle {bundle!r} directive {directive!r} is unknown"
            return
        arity = 2 if directive in ASSET_DIRECTIVES_WITH_TARGET else 1
        if len(operands) != arity or not all(isinstance(o, str) for o in operands):
            yield (
                f"`assets` bundle {bundle!r} directive {directive!r} takes "
                f"{arity} path(s), got {entry!r}"
            )


def workspace_checker(roots: list[str], excluded: set[str]) -> ManifestChecker:
    from odoo import release

    dirs = {
        manifest.parent.name: manifest.parent
        for manifest in _sort_manifests.iter_manifests(roots, excluded)
    }
    return ManifestChecker(addon_dirs=dirs, series=release.major_version)


def main(argv: list[str] | None = None) -> int:
    parser = _sort_manifests.build_parser()
    parser.description = (
        "Report every __manifest__.py the fixer would rewrite, and every value "
        "the fixer cannot decide for you."
    )
    args = parser.parse_args(argv)
    _sort_manifests.ensure_odoo_importable()
    excluded = set(args.exclude)
    checker = workspace_checker(args.roots, excluded)

    shape = []
    value = []
    checked = 0
    for manifest in _sort_manifests.iter_manifests(args.roots, excluded):
        checked += 1
        outcome = _sort_manifests.sort_manifest(manifest, dry_run=True)
        if outcome is None:
            shape.append(f"{manifest}: the fixer declines it")
        elif outcome:
            shape.append(f"{manifest}: the fixer would rewrite it")
        data = _sort_manifests.read_manifest(manifest)
        if data is not None:
            value.extend(
                f"{manifest.parent}: {text.partition(': ')[2]}"
                for text in checker.findings(
                    manifest.parent.name, data, manifest.parent
                )
            )

    for line in [*shape, *value]:
        print(line)  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
    print(  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
        f"\nDone: {checked} manifests, {len(shape)} to rewrite, "
        f"{len(value)} value finding(s)"
    )
    return 1 if shape or value else 0


if __name__ == "__main__":
    sys.exit(main())
