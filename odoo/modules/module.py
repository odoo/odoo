import ast
import copy
import functools
import importlib
import importlib.abc
import importlib.machinery
import importlib.metadata
import logging
import os
import re
import sys
import traceback
import types
import typing
from collections.abc import Collection, Mapping
from pathlib import Path

import odoo.upgrade
from odoo import release, tools
from odoo.libs.debug_log import DebugLog
from odoo.libs.hashing import ALGO_TAG, prepare_cache_hasher, update_from_file

import odoo.addons

if typing.TYPE_CHECKING:
    from packaging.requirements import InvalidRequirement, Requirement
else:
    try:
        from packaging.requirements import InvalidRequirement, Requirement
    except ImportError:

        class InvalidRequirement(Exception): ...

        class Requirement:
            def __init__(self, pydep):
                if not re.fullmatch(r"[\w\-]+", pydep):
                    msg = f"Package `packaging` is required to parse `{pydep}` external dependency and is not installed"
                    raise ImportError(msg)
                self.marker = None
                self.specifier = None
                self.name = pydep


__all__ = [
    "Manifest",
    "ResourceLocation",
    "adapt_version",
    "get_manifest",
    "get_module_content_checksum",
    "get_module_names",
    "get_module_path",
    "get_resource_from_path",
    "initialize_sys_path",
    "load_odoo_module",
    "load_script",
]

MODULE_NAME_RE = re.compile(r"^\w{1,256}$", re.ASCII)
MANIFEST_NAMES = ["__manifest__.py"]
README = ["README.rst", "README.md", "README.txt", "README"]

_DEFAULT_MANIFEST = {
    "application": False,
    "bootstrap": False,
    "assets": {},
    "auto_install": False,
    "category": "Uncategorized",
    "cloc_exclude": [],
    "configurator_snippets": {},
    "configurator_snippets_addons": {},
    "countries": [],
    "data": [],
    "demo": [],
    "demo_xml": [],
    "depends": [],
    "description": "",
    "esm": {},
    "external_dependencies": {},
    "init_xml": [],
    "installable": True,
    "iot_handlers_in_image": False,
    "images": [],
    "images_preview_theme": {},
    "live_test_url": "",
    "new_page_templates": {},
    "post_init_hook": "",
    "post_load": "",
    "pre_init_hook": "",
    "sequence": 100,
    "summary": "",
    "test": [],
    "theme_customizations": {},
    "update_xml": [],
    "uninstall_hook": "",
    "version": "1.0",
    "web": False,
    "website": "",
}

TYPED_FIELD_DEFINITION_RE = re.compile(
    r"""
    \b (?P<field_name>\w+) \s*
    (:\s*(?P<field_type>[^ ]*))? \s*
    = \s*
    fields\.(?P<field_class>Many2one|One2many|Many2many)
    (\[(?P<type_param>[^\]]+)\])?
""",
    re.VERBOSE,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_ManifestStat = tuple[int, int] | None
"""``(st_mtime_ns, st_size)`` of a module's manifest, or None when it has none."""


def _get_manifest_stat(path: str) -> _ManifestStat:
    for manifest_name in MANIFEST_NAMES:
        try:
            st = Path(path, manifest_name).stat()
        except OSError:
            continue
        return (st.st_mtime_ns, st.st_size)
    return None


if typing.TYPE_CHECKING:
    from odoo.tests.case import TestCase

current_test: TestCase | bool = False


class UpgradeHook(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(
        self,
        fullname: str,
        path: typing.Any = None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if re.match(r"^odoo\.addons\.base\.maintenance\.migrations\b", fullname):
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(
        self, spec: importlib.machinery.ModuleSpec
    ) -> types.ModuleType | None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        canonical_name = module.__name__.replace(
            "odoo.addons.base.maintenance.migrations", "odoo.upgrade"
        )
        cached = canonical_name in sys.modules
        if cached:
            canonical = sys.modules[canonical_name]
        else:
            canonical = importlib.import_module(canonical_name)

        sys.modules[module.__name__] = canonical
        _debug.logic(
            "module.upgrade_hook.aliased",
            name=module.__name__,
            canonical=canonical_name,
            cached=cached,
        )


class _SysPathState:
    addons_path: tuple[str, ...] | None = None
    hooks_installed: bool = False


def _freeze_namespace_path(namespace_path: Collection[str]) -> None:
    typing.cast("typing.Any", namespace_path)._path_finder = lambda *a: None


def initialize_sys_path() -> None:
    for path in (
        tools.config.addons_data_dir,
        *tools.config["addons_path"],
        tools.config.addons_community_dir,
    ):
        if os.access(path, os.R_OK) and path not in odoo.addons.__path__:
            odoo.addons.__path__.append(path)

    legacy_upgrade_path = str(
        Path(tools.config.addons_base_dir, "base/maintenance/migrations")
    )
    for up in tools.config["upgrade_path"] or [legacy_upgrade_path]:
        if up not in odoo.upgrade.__path__:
            odoo.upgrade.__path__.append(up)

    spec = importlib.machinery.ModuleSpec(
        "odoo.addons.base.maintenance", None, is_package=True
    )
    maintenance_pkg: typing.Any = importlib.util.module_from_spec(spec)
    maintenance_pkg.migrations = odoo.upgrade
    sys.modules["odoo.addons.base.maintenance"] = maintenance_pkg
    sys.modules["odoo.addons.base.maintenance.migrations"] = odoo.upgrade

    current_addons_path = tuple(odoo.addons.__path__)
    path_changed = _SysPathState.addons_path != current_addons_path
    if path_changed:
        Manifest.clear_caches()
        tools.files.clear_caches()
        _SysPathState.addons_path = current_addons_path

    if not _SysPathState.hooks_installed:
        _freeze_namespace_path(odoo.addons.__path__)
        _freeze_namespace_path(odoo.upgrade.__path__)
        sys.meta_path.insert(0, UpgradeHook())
        _SysPathState.hooks_installed = True
        _debug.lifecycle("module.sys_path.hooks_installed")
    _debug.logic(
        "module.sys_path",
        addons_paths=len(current_addons_path),
        upgrade_paths=len(odoo.upgrade.__path__),
        caches_cleared=path_changed,
    )


@typing.final
class Manifest(Mapping[str, typing.Any]):
    _COMPUTED_KEYS = (
        "description",
        "icon",
        "addons_path",
        "version",
        "static_path",
    )

    def __init__(self, *, path: str, manifest_content: dict):
        if not Path(path).is_absolute():
            raise ValueError("path of module must be absolute")
        self.path = path
        self.name = Path(path).name
        if not MODULE_NAME_RE.match(self.name):
            raise ValueError(f"Invalid module name: {self.name}")
        self.__manifest_content = manifest_content

    @property
    def declared(self) -> types.MappingProxyType:
        return types.MappingProxyType(self.__manifest_content)

    @property
    def addons_path(self) -> str:
        p = Path(self.path)
        if p.name != self.name:
            raise RuntimeError(
                f"module path {self.path!r} does not end in {self.name!r}"
            )
        return str(p.parent)

    @functools.cached_property
    def __manifest_cached(self) -> dict[str, typing.Any]:
        return _normalize_manifest(self.name, self.__manifest_content)

    @functools.cached_property
    def description(self) -> str:
        if desc := self.__manifest_cached.get("description"):
            return desc
        for file_name in README:
            try:
                with tools.file_open(str(Path(self.path, file_name))) as f:
                    return f.read()
            except OSError:
                pass
        return ""

    @functools.cached_property
    def version(self) -> str:
        return self.__manifest_cached["version"]

    @functools.cached_property
    def icon(self) -> str:
        return _get_module_icon_path(self.name, self.get_raw_value("icon"))

    @functools.cached_property
    def static_path(self) -> str | None:
        static = Path(self.path, "static")
        manifest = self.__manifest_cached
        if (manifest["installable"] or manifest["assets"]) and static.is_dir():
            return str(static)
        return None

    def __getitem__(self, key: str) -> typing.Any:
        if key in self._COMPUTED_KEYS:
            return getattr(self, key)
        val = self.__manifest_cached[key]
        if isinstance(val, (str, int, bool, float)):
            return val
        return copy.deepcopy(val)

    def get_raw_value(self, key: str) -> typing.Any:
        return copy.deepcopy(self.__manifest_cached.get(key))

    def _force_parse(self) -> None:
        _ = self.__manifest_cached

    def __iter__(self) -> typing.Iterator[str]:
        manifest = self.__manifest_cached
        yield from manifest
        for key in self._COMPUTED_KEYS:
            if key not in manifest:
                yield key

    def check_manifest_dependencies(self) -> None:
        depends = self.get("external_dependencies")
        if not depends:
            return
        _debug.pipeline(
            "module.external_dependencies",
            module=self.name,
            python=len(depends.get("python", [])),
            bin=len(depends.get("bin", [])),
        )
        for pydep in depends.get("python", []):
            check_python_external_dependency(pydep)

        for binary in depends.get("bin", []):
            try:
                tools.get_executable_path(binary)
            except OSError as e:
                _debug.logic(
                    "module.dependency_missing",
                    module=self.name,
                    kind="bin",
                    dependency=binary,
                )
                msg = f"Unable to find {binary!r} in path"
                raise MissingDependencyError(msg, binary) from e

    def __bool__(self) -> bool:
        return True

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __repr__(self) -> str:
        return f"Manifest({self.name})"

    _parse_cache: dict[str, tuple[_ManifestStat, Manifest | None]] = {}

    _resolution_cache: dict[str, str] = {}

    @staticmethod
    def _get_manifest_from_addons(module: str) -> Manifest | None:
        if (known := Manifest._resolution_cache.get(module)) is not None:
            if manifest := Manifest._from_path(known):
                return manifest
            del Manifest._resolution_cache[module]
            _debug.logic("module.manifest.resolution_stale", module=module, path=known)
        for scanned, adp in enumerate(odoo.addons.__path__, 1):  # debuglog
            path = str(Path(adp, module))
            if manifest := Manifest._from_path(path):
                Manifest._resolution_cache[module] = path
                _debug.perf.count(
                    "module.manifest.resolved", module=module, scanned=scanned
                )
                return manifest
        return None

    @staticmethod
    def clear_caches() -> None:
        _debug.lifecycle(
            "module.manifest.caches_cleared",
            parsed=len(Manifest._parse_cache),
            resolved=len(Manifest._resolution_cache),
        )
        Manifest._parse_cache.clear()
        Manifest._resolution_cache.clear()

    @staticmethod
    def for_addon(module_name: str, *, display_warning: bool = True) -> Manifest | None:
        if not MODULE_NAME_RE.match(module_name):
            _debug.logic("module.manifest.invalid_name", module=module_name)
            return None
        if mod := Manifest._get_manifest_from_addons(module_name):
            return mod
        _debug.logic(
            "module.manifest.missing", module=module_name, warned=display_warning
        )
        if display_warning:
            _logger.warning("module %s: manifest not found", module_name)
        return None

    @staticmethod
    def _from_path(path: str, env: typing.Any = None) -> Manifest | None:
        if env is not None:
            return Manifest._parse_from_path(path, env)
        signature = _get_manifest_stat(path)
        cached = Manifest._parse_cache.get(path)
        if cached is not None and cached[0] == signature:
            return cached[1]
        manifest = Manifest._parse_from_path(path, None)
        Manifest._parse_cache[path] = (signature, manifest)
        if signature is not None:
            _debug.perf.count(
                "module.manifest.parsed",
                path=path,
                stale=cached is not None,
                valid=manifest is not None,
            )
        return manifest

    @staticmethod
    def _parse_from_path(path: str, env: typing.Any) -> Manifest | None:
        for manifest_name in MANIFEST_NAMES:
            try:
                with tools.file_open(str(Path(path, manifest_name)), env=env) as f:
                    manifest_content = ast.literal_eval(f.read())
            except OSError:
                pass
            except (SyntaxError, ValueError) as e:
                _debug.logic(
                    "module.manifest.parse_failed", path=path, error=type(e).__name__
                )
                _logger.warning(
                    "Failed to parse the manifest file at %r: %s",
                    path,
                    e,
                )
            else:
                try:
                    return Manifest(path=path, manifest_content=manifest_content)
                except ValueError:
                    _debug.logic("module.manifest.invalid_name", path=path)
                    _logger.debug(
                        "Manifest at %r has invalid module name, skipped",
                        path,
                    )
        return None

    @staticmethod
    def get_all_addon_manifests() -> list[Manifest]:
        modules: dict[str, Manifest] = {}
        with _debug.perf(
            "module.manifests.scan", paths=len(odoo.addons.__path__)
        ) as span:
            entries = shadowed = 0  # debuglog
            for adp in odoo.addons.__path__:
                if not Path(adp).is_dir():
                    _logger.warning("addons path is not a directory: %s", adp)
                    continue
                for entry in Path(adp).iterdir():
                    entries += 1  # debuglog
                    if entry.name in modules:
                        shadowed += 1  # debuglog
                        _debug.logic(
                            "module.manifest.shadowed",
                            module=entry.name,
                            by=modules[entry.name].addons_path,
                            path=adp,
                        )
                        continue
                    if mod := Manifest._from_path(str(entry)):
                        if entry.name != mod.name:
                            raise RuntimeError(
                                f"manifest at {entry} resolved to module {mod.name!r}"
                            )
                        modules[entry.name] = mod
            span.set(entries=entries, modules=len(modules), shadowed=shadowed)
        return sorted(modules.values(), key=lambda m: m.name)


def get_module_path(module: str, display_warning: bool = True) -> str | None:
    mod = Manifest.for_addon(module, display_warning=display_warning)
    return mod.path if mod else None


_CHECKSUM_IGNORE_DIRS = frozenset({"__pycache__", ".git"})
_CHECKSUM_IGNORE_SUFFIXES = (".pyc", ".pyo", ".swp", "~")


def get_module_content_checksum(module: str) -> str | None:
    path = get_module_path(module, display_warning=False)
    if not path:
        return None
    digest = prepare_cache_hasher()
    root = Path(path)
    with _debug.perf("module.content_checksum", module=module) as span:
        files = sorted(
            p
            for p in root.rglob("*")
            if not _CHECKSUM_IGNORE_DIRS.intersection(p.parts)
            and not p.name.endswith(_CHECKSUM_IGNORE_SUFFIXES)
            and p.is_file()
        )
        span.set(files=len(files))
        for p in files:
            digest.update(str(p.relative_to(root)).encode())
            digest.update(b"\0")
            update_from_file(digest, p)
            digest.update(b"\0")
    return f"{ALGO_TAG}:{digest.hexdigest()}"


class ResourceLocation(typing.NamedTuple):
    module: str
    relative_path: str

    @property
    def addons_path(self) -> str:
        return f"{self.module}/{self.relative_path}"


def get_resource_from_path(path: str) -> ResourceLocation | None:
    p = Path(path)
    sorted_paths = sorted(odoo.addons.__path__, key=len, reverse=True)
    for adpath in sorted_paths:
        try:
            rel = p.relative_to(adpath)
        except ValueError:
            continue
        parts = rel.parts
        if not parts:
            continue
        return ResourceLocation(parts[0], "/".join(parts[1:]))
    _debug.logic("module.resource_unresolved", path=path, paths=len(sorted_paths))
    return None


def _get_module_icon_path(module: str, declared: typing.Any) -> str:
    fpath = (declared or "").lstrip("/")
    if not fpath:
        fpath = f"{module}/static/description/icon.png"
    try:
        tools.file_path(fpath)
        return "/" + fpath
    except FileNotFoundError:
        _debug.logic("module.icon_fallback", module=module, declared=bool(declared))
        return "/base/static/description/icon.png"


def get_module_icon_path(module: str) -> str:
    manifest = Manifest.for_addon(module, display_warning=False)
    declared = manifest.get_raw_value("icon") if manifest else None
    return _get_module_icon_path(module, declared)


def _normalize_auto_install(module: str, manifest: dict, depends: Collection) -> None:
    auto_install = manifest["auto_install"]
    if isinstance(auto_install, str):
        raise TypeError(
            f"module {module}: 'auto_install' must be a bool or a list/tuple/set"
            f" of dependency names; got string {auto_install!r} (did you forget"
            f" the brackets, e.g. ['{auto_install}']?)"
        )
    if isinstance(auto_install, (list, tuple, set, frozenset)):
        manifest["auto_install"] = auto_install_set = set(auto_install)
        non_dependencies = auto_install_set.difference(depends)
        if non_dependencies:
            raise ValueError(
                f"module {module}: auto_install triggers must be dependencies,"
                f" found non-dependencies [{', '.join(non_dependencies)}]"
            )
    elif auto_install is True:
        manifest["auto_install"] = set(depends)
    elif auto_install is not False:
        raise TypeError(
            f"module {module}: 'auto_install' must be a bool or a"
            f" list/tuple/set of dependency names; got"
            f" {type(auto_install).__name__}: {auto_install!r}"
        )


def _normalize_version(module: str, manifest: dict) -> None:
    try:
        manifest["version"] = adapt_version(str(manifest["version"]))
    except ValueError:
        _debug.logic(
            "module.manifest.version_invalid",
            module=module,
            version=str(manifest["version"]),
            installable=manifest["installable"],
        )
        if manifest["installable"]:
            _logger.warning(
                "The module %s has an invalid version %r, setting installable=False",
                module,
                manifest["version"],
            )
            manifest["installable"] = False
        manifest["version"] = str(manifest["version"])
    if manifest["installable"] and not check_version(
        str(manifest["version"]), should_raise=False
    ):
        _debug.logic(
            "module.manifest.version_incompatible",
            module=module,
            version=str(manifest["version"]),
        )
        _logger.warning(
            "The module %s has an incompatible version, setting installable=False",
            module,
        )
        manifest["installable"] = False


def _normalize_manifest(module: str, manifest_content: dict) -> dict:

    manifest: dict[str, typing.Any] = {
        k: (v.copy() if isinstance(v, (list, dict)) else v)
        for k, v in _DEFAULT_MANIFEST.items()
    }
    manifest.update(manifest_content)

    if not manifest.get("author"):
        author = manifest.get("contributors") or manifest.get("maintainer") or ""
        if isinstance(author, (list, tuple)):
            author = ", ".join(str(a) for a in author)
        else:
            author = str(author)
        manifest["author"] = author
        _logger.warning(
            "Missing `author` key in manifest for %r, defaulting to %r",
            module,
            author,
        )

    if not manifest.get("license"):
        manifest["license"] = "LGPL-3"
        _logger.warning(
            "Missing `license` key in manifest for %r, defaulting to LGPL-3",
            module,
        )

    if not manifest.get("name"):
        manifest["name"] = module
        _logger.warning(
            "Missing `name` key in manifest for %r, defaulting to the technical name",
            module,
        )

    if module == "base":
        manifest["depends"] = []
    elif not manifest["depends"]:
        manifest["depends"] = ["base"]

    depends = manifest["depends"]
    if isinstance(depends, str):
        raise TypeError(
            f"module {module}: 'depends' must be a list of module names; got"
            f" string {depends!r} (did you forget the brackets, e.g."
            f" ['{depends}']?)"
        )
    if not isinstance(depends, Collection):
        raise TypeError(
            f"module {module}: 'depends' must be a collection of module names;"
            f" got {type(depends).__name__}: {depends!r}"
        )

    _normalize_auto_install(module, manifest, depends)
    _normalize_version(module, manifest)
    _debug.lifecycle(
        "module.manifest.normalized",
        module=module,
        depends=len(depends),
        auto_install=len(manifest["auto_install"])
        if isinstance(manifest["auto_install"], set)
        else False,
        installable=manifest["installable"],
        author_defaulted="author" not in manifest_content,
        license_defaulted="license" not in manifest_content,
        data=len(manifest["data"]),
        demo=len(manifest["demo"]),
    )

    return manifest


def get_manifest(module: str, mod_path: str | None = None) -> Mapping[str, typing.Any]:
    if mod_path:
        mod = Manifest._from_path(mod_path)
        if mod and mod.name != module:
            raise ValueError(f"Invalid path for module {module}: {mod_path}")
    else:
        mod = Manifest.for_addon(module, display_warning=False)
    return mod if mod is not None else {}


def load_odoo_module(module_name: str) -> None:

    qualname = f"odoo.addons.{module_name}"
    if qualname in sys.modules:
        _debug.logic("module.import.cached", module=module_name)
        return

    try:
        with _debug.perf("module.import", module=module_name) as span:
            __import__(qualname)

            manifest = Manifest.for_addon(module_name)
            post_load = manifest.get("post_load") if manifest else None
            span.set(post_load=post_load)
            if post_load:
                with _debug.perf(
                    "module.post_load", module=module_name, hook=post_load
                ):
                    getattr(sys.modules[qualname], post_load)()

    except AttributeError as err:
        _logger.critical("Couldn't load module %s", module_name)
        trace = traceback.format_exc()
        match = TYPED_FIELD_DEFINITION_RE.search(trace)
        _debug.logic(
            "module.import.failed",
            module=module_name,
            error="AttributeError",
            circular_field=bool(
                match and "most likely due to a circular import" in trace
            ),
        )
        if match and "most likely due to a circular import" in trace:
            field_name = match["field_name"]
            field_class = match["field_class"]
            field_type = match["field_type"] or match["type_param"]
            if "." not in field_type:
                field_type = f"{module_name}.{field_type}"
            raise AttributeError(
                f"{err}\n"
                "To avoid circular import for the comodel, use the annotation syntax:\n"
                f"    {field_name}: {field_type} = fields.{field_class}(...)\n"
                "Annotations are lazily evaluated (PEP 649), so the comodel\n"
                "class does not need to be importable at field definition time."
            ).with_traceback(err.__traceback__) from None
        raise
    except Exception as err:  # debuglog
        _debug.logic(
            "module.import.failed", module=module_name, error=type(err).__name__
        )
        _logger.critical("Couldn't load module %s", module_name)
        raise


def get_module_names() -> list[str]:
    return [m.name for m in Manifest.get_all_addon_manifests()]


def adapt_version(version: str) -> str:
    parts = version.split(".")
    if not (2 <= len(parts) <= 5):
        raise ValueError(
            f"Invalid version {version!r}, must have between 2 and 5 parts"
        )
    try:
        for part in parts:
            int(part)
    except ValueError as e:
        raise ValueError(f"Invalid version {version!r}") from e
    serie = release.major_version
    if len(parts) <= 3 and version != serie and not version.startswith(serie + "."):
        return f"{serie}.{version}"
    return version


def check_version(version: str, should_raise: bool = True) -> bool:
    try:
        version = adapt_version(version)
    except ValueError:
        if should_raise:
            raise
        return False
    serie = release.major_version
    if version == serie or version.startswith(serie + "."):
        return True
    if should_raise:
        raise ValueError(
            f"Invalid version {version!r}. Modules should have a version in format"
            f" `x.y`, `x.y.z`, `{serie}.x.y` or `{serie}.x.y.z`."
        )
    return False


class MissingDependencyError(Exception):
    def __init__(self, message: str, dependency: str) -> None:
        self.dependency = dependency
        super().__init__(message)


def check_python_external_dependency(pydep: str) -> None:
    try:
        requirement = Requirement(pydep)
    except InvalidRequirement as e:
        msg = f"{pydep} is an invalid external dependency specification: {e}"
        raise ValueError(msg) from e
    if requirement.marker and not requirement.marker.evaluate():
        _debug.logic(
            "module.dependency_marker_skipped",
            dependency=pydep,
            marker=str(requirement.marker),
        )
        _logger.debug(
            "Ignored external dependency %s because environment markers do not match",
            pydep,
        )
        return
    try:
        version = importlib.metadata.version(requirement.name)
    except importlib.metadata.PackageNotFoundError as e:
        try:
            importlib.import_module(requirement.name)
            _debug.logic(
                "module.dependency_not_a_distribution",
                dependency=pydep,
                importable=requirement.name,
            )
            _logger.warning(
                "python external dependency on '%s' does not appear to be a valid PyPI package. Using a PyPI package name is recommended.",
                requirement.name,
            )
            return
        except ImportError:
            pass
        _debug.logic("module.dependency_missing", kind="python", dependency=pydep)
        msg = f"External dependency {pydep!r} not installed: {e}"
        raise MissingDependencyError(msg, pydep) from e
    if requirement.specifier and not requirement.specifier.contains(version):
        _debug.logic(
            "module.dependency_version_mismatch",
            dependency=pydep,
            installed=version,
            specifier=str(requirement.specifier),
        )
        msg = f"External dependency version mismatch: {pydep} (installed: {version})"
        raise MissingDependencyError(msg, pydep)
    _debug.logic("module.dependency_satisfied", dependency=pydep, installed=version)


def load_script(path: str, module_name: str) -> types.ModuleType:
    full_path = tools.file_path(path) if not Path(path).is_absolute() else path
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    if not (spec and spec.loader):
        raise ImportError(f"spec not found for {module_name}")
    module = importlib.util.module_from_spec(spec)
    with _debug.perf("module.load_script", name=module_name, path=full_path):
        spec.loader.exec_module(module)
    return module
