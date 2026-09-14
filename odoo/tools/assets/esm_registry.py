import logging
import threading
from collections import Counter
from collections.abc import Collection, Mapping
from types import MappingProxyType
from typing import NamedTuple

from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog

__all__ = [
    "EsmRegistry",
    "check_esm_config",
    "esm_registry",
    "external_bare_specifiers",
    "external_lib_aliases",
    "external_libs",
    "invalidate_esm_registry",
]

_registry_log = get_asset_logger("bundle")
_debug = DebugLog(__name__)

_ESM_MANIFEST_KEYS = frozenset(
    {
        "bundles",
        "dynamic_children",
        "dynamic_children_from",
        "exports",
        "external_libs",
        "import_map_includes",
        "runtime_bundles",
        "secondary_import_map_includes",
        "standalone_bundles",
    }
)


class EsmRegistry(NamedTuple):
    bundles: frozenset
    dynamic_children: Mapping
    import_map_includes: Mapping
    secondary_import_map_includes: Mapping
    dynamic_bundle_names: frozenset
    import_map_included_bundles: frozenset
    secondary_parents: Mapping = MappingProxyType({})
    secondary_bundle_names: frozenset = frozenset()
    standalone_bundles: frozenset = frozenset()
    external_libs: Mapping = MappingProxyType({})
    runtime_bundle_names: frozenset = frozenset()
    exports: frozenset = frozenset()
    bundle_owners: Mapping = MappingProxyType({})

    # a bundle is named after the module that declared it, except when that
    # module was folded into another and the bundle kept its name
    # (`pos_preparation_display.assets`, declared by `pos_enterprise`)
    def bundle_addon(self, bundle: str) -> str:
        return self.bundle_owners.get(bundle) or bundle.partition(".")[0]


_lock = threading.Lock()
_cache: list = [None]


def esm_registry() -> EsmRegistry:
    if _cache[0] is None:
        with _lock:
            if _cache[0] is None:
                with _debug.perf("esm_registry.built"):
                    _cache[0] = _prepare_esm_registry()
    return _cache[0]


def invalidate_esm_registry() -> None:
    from .esm_libs import invalidate_served_libs

    with _lock:
        _debug.lifecycle("esm_registry.invalidated", cached=_cache[0] is not None)
        _cache[0] = None
    invalidate_served_libs()


def external_libs() -> Mapping:
    return esm_registry().external_libs


def external_bare_specifiers() -> frozenset:
    return frozenset(spec for spec in external_libs() if not spec.startswith("@odoo/"))


def external_lib_aliases() -> Mapping[str, str]:
    from odoo.tools.assets.esm_graph import url_to_module_path

    aliases = {}
    for spec, url in external_libs().items():
        try:
            aliases[spec] = url_to_module_path(url)
        except ValueError:
            _debug.logic("esm_registry.external_lib_unaliased", spec=spec, url=url)
            continue
    return MappingProxyType(aliases)


def _merge_mapping(target: dict, declared: Mapping, *, module: str, key: str) -> None:
    if not isinstance(declared, Mapping):
        raise TypeError(
            f"Module {module!r}: manifest 'esm.{key}' must be a dict "
            f"(parent bundle -> list of children), got {type(declared).__name__}"
        )
    for parent, children in declared.items():
        if isinstance(children, str) or not isinstance(children, (list, tuple)):
            raise TypeError(
                f"Module {module!r}: 'esm.{key}[{parent!r}]' must be a "
                f"list of bundle names"
            )
        target.setdefault(parent, []).extend(children)


def _merge_children_from(target: dict, declared: Mapping, *, module: str) -> None:
    if not isinstance(declared, Mapping):
        raise TypeError(
            f"Module {module!r}: manifest 'esm.dynamic_children_from' must be a "
            f"dict (page bundle -> page whose dynamic children it takes), "
            f"got {type(declared).__name__}"
        )
    for page, base in declared.items():
        if not isinstance(base, str):
            raise TypeError(
                f"Module {module!r}: 'esm.dynamic_children_from[{page!r}]' must "
                f"be one bundle name"
            )
        known = target.setdefault(page, base)
        if known != base:
            raise ValueError(
                f"esm.dynamic_children_from[{page!r}] names both {known!r} and {base!r}"
            )


def _inherit_dynamic_children(
    bundles: set, dynamic_children: dict, children_from: Mapping
) -> None:
    for page, base in children_from.items():
        for name in (page, base):
            if name not in bundles:
                raise ValueError(
                    f"esm.dynamic_children_from names {name!r}, which is not a "
                    f"registered ESM bundle"
                )
        if base in children_from:
            raise ValueError(
                f"esm.dynamic_children_from[{page!r}] names {base!r}, which "
                f"takes its own dynamic children from {children_from[base]!r}"
            )
        inherited = dynamic_children.get(base, ())
        own = dynamic_children.setdefault(page, [])
        restated = sorted(set(own) & set(inherited))
        if restated:
            raise ValueError(
                f"esm.dynamic_children[{page!r}] restates {restated}, which "
                f"{page!r} already takes from {base!r}"
            )
        own.extend(inherited)
        _debug.pipeline(
            "esm_registry.children_inherited",
            page=page,
            base=base,
            children=len(inherited),
        )


def _merge_external_libs(
    target: dict, declared: Mapping, owner_by_spec: dict, *, module: str
) -> None:
    if not isinstance(declared, Mapping):
        raise TypeError(
            f"Module {module!r}: manifest 'esm.external_libs' must be a dict "
            f"(bare specifier -> URL), got {type(declared).__name__}"
        )
    for spec, url in declared.items():
        if not isinstance(url, str) or not url.startswith("/"):
            raise TypeError(
                f"Module {module!r}: 'esm.external_libs[{spec!r}]' must be a "
                f"root-relative URL string, got {url!r}"
            )
        owner = owner_by_spec.get(spec)
        if owner is not None and target[spec] != url:
            raise ValueError(
                f"External lib specifier {spec!r} is declared by {owner!r} as "
                f"{target[spec]!r} and by {module!r} as {url!r}. One specifier "
                f"resolves to one URL; the owning module declares it."
            )
        target[spec] = url
        owner_by_spec[spec] = module


def _validated_esm_section(manifest) -> Mapping | None:
    esm = manifest.get("esm")
    if not esm:
        return None
    if not isinstance(esm, Mapping):
        raise TypeError(
            f"Module {manifest.name!r}: manifest 'esm' must be a dict, "
            f"got {type(esm).__name__}"
        )
    unknown = set(esm) - _ESM_MANIFEST_KEYS
    if unknown:
        raise ValueError(
            f"Module {manifest.name!r}: unknown 'esm' manifest keys "
            f"{sorted(unknown)}; expected a subset of {sorted(_ESM_MANIFEST_KEYS)}"
        )
    return esm


def _bundle_name_list(esm: Mapping, key: str, module: str):
    declared = esm.get(key, ())
    if isinstance(declared, str):
        raise TypeError(
            f"Module {module!r}: 'esm.{key}' must be a list, not a bare string"
        )
    return declared


def _freeze_registry(
    bundles: set,
    dynamic_children: dict,
    import_map_includes: dict,
    secondary_includes: dict,
    standalone_bundles: set,
    runtime_bundles: set,
    external_libs: dict,
    exports: set | None = None,
    bundle_owners: dict | None = None,
) -> EsmRegistry:
    return EsmRegistry(
        bundles=frozenset(bundles),
        dynamic_children=MappingProxyType(
            {p: tuple(c) for p, c in dynamic_children.items()}
        ),
        import_map_includes=MappingProxyType(
            {p: tuple(c) for p, c in import_map_includes.items()}
        ),
        secondary_import_map_includes=MappingProxyType(
            {p: tuple(c) for p, c in secondary_includes.items()}
        ),
        dynamic_bundle_names=frozenset(
            child for children in dynamic_children.values() for child in children
        ),
        import_map_included_bundles=frozenset(
            child for children in import_map_includes.values() for child in children
        ),
        secondary_parents=MappingProxyType(
            {
                child: tuple(
                    parent
                    for parent, children in secondary_includes.items()
                    if child in children
                )
                for child in {
                    c for children in secondary_includes.values() for c in children
                }
            }
        ),
        secondary_bundle_names=frozenset(
            child for children in secondary_includes.values() for child in children
        ),
        standalone_bundles=frozenset(standalone_bundles),
        external_libs=MappingProxyType(dict(external_libs)),
        runtime_bundle_names=frozenset(runtime_bundles)
        | frozenset(
            child for children in dynamic_children.values() for child in children
        ),
        exports=frozenset(exports or ()),
        bundle_owners=MappingProxyType(dict(bundle_owners or {})),
    )


def _prepare_esm_registry() -> EsmRegistry:
    from odoo.modules import Manifest

    bundles: set = set()
    dynamic_children: dict = {}
    import_map_includes: dict = {}
    secondary_includes: dict = {}
    standalone_bundles: set = set()
    runtime_bundles: set = set()
    external_libs: dict = {}
    # Modules reached by NAME from outside the bundle graph -- a test's
    # browser_js code, a tour started from Python -- which no scan of JavaScript
    # sources can discover. Declared by the module that owns them.
    exports: set = set()
    external_lib_owner: dict = {}
    bundle_owners: dict = {}
    children_from: dict = {}
    declaring_modules = 0
    for manifest in Manifest.get_all_addon_manifests():
        esm = _validated_esm_section(manifest)
        if esm is None:
            continue
        declaring_modules += 1
        _debug.pipeline(
            "esm_registry.manifest_read",
            module=manifest.name,
            keys=sorted(esm),
        )
        for key in ("bundles", "standalone_bundles", "runtime_bundles"):
            for name in _bundle_name_list(esm, key, manifest.name):
                if name.partition(".")[0] != manifest.name:
                    bundle_owners.setdefault(name, manifest.name)
        bundles.update(_bundle_name_list(esm, "bundles", manifest.name))
        standalone_bundles.update(
            _bundle_name_list(esm, "standalone_bundles", manifest.name)
        )
        runtime_bundles.update(_bundle_name_list(esm, "runtime_bundles", manifest.name))
        for spec in _bundle_name_list(esm, "exports", manifest.name):
            if not isinstance(spec, str) or not spec.startswith("@"):
                raise ValueError(
                    f"Module {manifest.name!r}: 'esm.exports' names module "
                    f"specifiers such as '@web/core/registry', got {spec!r}"
                )
            exports.add(spec)
        if "external_libs" in esm:
            _merge_external_libs(
                external_libs,
                esm["external_libs"],
                external_lib_owner,
                module=manifest.name,
            )
        for target, key in (
            (dynamic_children, "dynamic_children"),
            (import_map_includes, "import_map_includes"),
            (secondary_includes, "secondary_import_map_includes"),
        ):
            if key in esm:
                _merge_mapping(target, esm[key], module=manifest.name, key=key)
        if "dynamic_children_from" in esm:
            _merge_children_from(
                children_from, esm["dynamic_children_from"], module=manifest.name
            )

    _inherit_dynamic_children(bundles, dynamic_children, children_from)
    check_esm_config(
        bundles,
        dynamic_children,
        import_map_includes,
        secondary_includes,
        standalone_bundles=standalone_bundles,
        runtime_bundles=runtime_bundles,
    )
    registry = _freeze_registry(
        bundles,
        dynamic_children,
        import_map_includes,
        secondary_includes,
        standalone_bundles,
        runtime_bundles,
        external_libs,
        exports,
        bundle_owners,
    )
    log_event(
        _registry_log,
        logging.INFO,
        "esm_registry_built",
        modules=declaring_modules,
        bundles=len(registry.bundles),
        dynamic=len(registry.dynamic_bundle_names),
        includes=len(registry.import_map_included_bundles),
        external_libs=len(registry.external_libs),
    )
    return registry


def check_esm_config(
    bundles: set,
    dynamic_children: Mapping,
    import_map_includes: Mapping,
    secondary_import_map_includes: Mapping,
    *,
    standalone_bundles: Collection[str] = frozenset(),
    runtime_bundles: Collection[str] = frozenset(),
) -> None:
    for mapping_name, mapping in (
        ("dynamic_children", dynamic_children),
        ("import_map_includes", import_map_includes),
        ("secondary_import_map_includes", secondary_import_map_includes),
    ):
        for parent, children in mapping.items():
            if parent not in bundles:
                raise ValueError(
                    f"esm.{mapping_name} parent {parent!r} is not a "
                    f"registered ESM bundle (add it to some module's "
                    f"'esm.bundles')"
                )
            duplicated = [
                name for name, count in Counter(children).items() if count > 1
            ]
            if duplicated:
                raise ValueError(
                    f"Duplicate children in esm.{mapping_name}[{parent!r}]: "
                    f"{duplicated} (declared by more than one module?)"
                )
            for child in children:
                if child not in bundles:
                    raise ValueError(
                        f"esm.{mapping_name}[{parent!r}] child {child!r} "
                        "is not a registered ESM bundle"
                    )

    for parent in set(dynamic_children) & set(import_map_includes):
        shared = set(dynamic_children[parent]) & set(import_map_includes[parent])
        if shared:
            raise ValueError(
                f"Bundles declared both as dynamic children and import-map "
                f"includes of parent {parent!r}: {sorted(shared)}"
            )

    related_children = {
        child
        for mapping in (
            dynamic_children,
            import_map_includes,
            secondary_import_map_includes,
        )
        for children in mapping.values()
        for child in children
    }
    for name in runtime_bundles:
        if name not in bundles:
            raise ValueError(
                f"esm.runtime_bundles entry {name!r} is not a registered ESM "
                f"bundle (add it to the same module's 'esm.bundles')"
            )

    for name in standalone_bundles:
        if name not in bundles:
            raise ValueError(
                f"esm.standalone_bundles entry {name!r} is not a registered "
                f"ESM bundle (add it to the same module's 'esm.bundles')"
            )
        if name in related_children:
            raise ValueError(
                f"esm.standalone_bundles entry {name!r} cannot participate in "
                f"page import-map relationships: a standalone bundle has no "
                f"import map or odoo.loader at runtime"
            )
