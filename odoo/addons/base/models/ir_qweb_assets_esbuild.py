import logging
import re
from typing import Any

from odoo import models
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.libs.lru import LRU
from odoo.tools.assets import esm_index
from odoo.tools.assets.esbuild import (
    EsbuildCompiler,
    EsbuildGroupResult,
    EsbuildResult,
    module_specifiers,
)
from odoo.tools.assets.esm_graph import (
    _TRANSITIVE_IMPORT_RE,
    _get_import_specifiers,
    get_escaping_relative_imports,
)
from odoo.tools.assets.esm_lexer import lex_module
from odoo.tools.assets.esm_registry import esm_registry, external_libs

from odoo.addons.base.models.assetsbundle import AssetsBundle

_fallback_log = get_asset_logger("fallback")
_debug = DebugLog(__name__)

# specifier literals per source, keyed by the asset's unique descriptor (url
# and mtime): the page bundles of one process share most of their sources,
# and one bundle's consumers re-list many of its own
_SPECIFIER_LITERALS_CACHE: LRU = LRU(16384)


class EsbuildBundleError(RuntimeError):
    pass


def _get_specs_imported_by_consumers(
    consumers: list[AssetsBundle], members: set[str]
) -> set[str]:
    imported: set[str] = set()
    ext_lib_names = set(external_libs())
    for consumer in consumers:
        own = [a for a in consumer.native_modules if a.module_path not in members]
        own_specs = {name for a in own for name in module_specifiers(a)}
        direct: set[str] = set()
        for asset in own:
            lexed = lex_module(asset.raw_content)
            if lexed is not None:
                direct.update(imp["n"] for imp in lexed["imports"])
            else:
                direct.update(_get_import_specifiers(asset.raw_content))
        imported.update(spec for spec in direct if spec in members)
        reached, _ext = consumer._bridges._discover_reachable_specifiers(
            own_specs, ext_lib_names, provided=members, modules=own
        )
        imported.update(spec for spec in reached if spec in members)
        imported.update(
            resolved
            for _module, _spec, resolved in get_escaping_relative_imports(
                own, own_specs
            )
            if resolved in members
        )
    _debug.perf.count(
        "consumer_imports",
        consumers=len(consumers),
        members=len(members),
        imported=len(imported),
    )
    return imported


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _check_lazy_bundle_relative_imports(
        self,
        asset_bundle: AssetsBundle,
    ) -> None:
        escapes = get_escaping_relative_imports(asset_bundle.native_modules)
        if not escapes:
            return
        _debug.logic(
            "lazy_bundle_rejected",
            bundle=asset_bundle.name,
            reason="escaping_relative_imports",
            escapes=len(escapes),
        )
        details = "; ".join(
            f"{module_path} imports {spec!r} (-> {resolved})"
            for module_path, spec, resolved in escapes
        )
        raise EsbuildBundleError(
            f"ESM bundle {asset_bundle.name!r} is served per-file but has "
            f"relative imports escaping the bundle: {details}. Use the bare "
            f"'@addon/...' specifier instead, so the import resolves through "
            f"the import map (parent-bridge shim) rather than fetching the "
            f"raw source."
        )

    def _can_compile_with_esbuild(self, bundle: str) -> bool:
        if bundle in self._get_esbuild_bundles_forced_fallback():
            _debug.logic("esbuild_declined", bundle=bundle, reason="admin_override")
            log_event(_fallback_log, logging.INFO, "admin_override", bundle=bundle)
            return False
        allow, circuit_reason = self._get_esbuild_circuit_state(bundle)
        if not allow:
            log_event(
                _fallback_log,
                logging.DEBUG,
                "circuit_blocked",
                bundle=bundle,
                reason=circuit_reason,
            )
        return allow

    def _get_esbuild_child_externals(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        assets_params: dict[str, Any] | None,
        child_bundles: list[AssetsBundle],
        page_scope: tuple[str, ...] = (),
    ) -> tuple[frozenset[str] | None, dict[str, str]]:
        parent_specs = {a.module_path for a in asset_bundle.native_modules}
        child_specs = {
            asset.module_path
            for child_ab in child_bundles
            for asset in child_ab.native_modules
        } - parent_specs
        secondary_stubs = self._get_secondary_parent_stubs(
            bundle, assets_params, page_scope
        )
        if not child_specs:
            _debug.logic(
                "child_externals",
                bundle=bundle,
                children=len(child_bundles),
                child_specs=0,
                stubs=len(secondary_stubs),
            )
            return None, secondary_stubs

        aliasable = {
            spec
            for spec in child_specs
            if "/../" not in spec and not spec.startswith("../")
        }
        if aliasable:
            child_stubs = asset_bundle._bridges.prepare_shim_sources(aliasable)
            secondary_stubs = {**child_stubs, **secondary_stubs}
        _debug.pipeline(
            "child_externals",
            bundle=bundle,
            children=len(child_bundles),
            child_specs=len(child_specs),
            aliasable=len(aliasable),
            stubs=len(secondary_stubs),
        )
        return frozenset(child_specs - aliasable) or None, secondary_stubs

    def _compile_with_esbuild(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        dynamic_child_specs: frozenset[str] | None,
        secondary_stubs: dict[str, str],
        exported_specs: frozenset[str] | None = None,
        registered_reach: dict[str, str] | None = None,
    ) -> EsbuildResult:
        config = self._get_esbuild_config()
        excluded_specs = frozenset(
            asset.module_path
            for asset in asset_bundle.native_modules
            if asset.module_path in secondary_stubs
        )
        try:
            with _debug.perf(
                "esbuild",
                bundle=bundle,
                dynamic_children=len(dynamic_child_specs or ()),
                secondary_stubs=len(secondary_stubs),
                excluded=len(excluded_specs),
                exported=len(exported_specs or ()),
            ) as span:
                result = asset_bundle.esbuild_native_bundle(
                    timeout_s=config.get_param_int(
                        "web.esbuild.timeout_s", EsbuildCompiler._ESBUILD_TIMEOUT_S
                    ),
                    target=config.get_param("web.esbuild.target")
                    or EsbuildCompiler._ESBUILD_TARGET,
                    source_maps=config.get_param("web.esbuild.source_maps")
                    or EsbuildCompiler._ESBUILD_SOURCE_MAPS,
                    dynamic_child_specs=dynamic_child_specs,
                    secondary_parent_stubs=secondary_stubs or None,
                    exported_specs=exported_specs,
                    registered_reach=registered_reach,
                    excluded_specs=excluded_specs,
                )
                span.set(chars=len(result.code) if result.code else 0)
        except Exception as exc:
            log_event(
                _fallback_log,
                logging.WARNING,
                "esbuild_exception",
                bundle=bundle,
                err=type(exc).__name__,
                msg=str(exc)[:200],
            )
            _debug.logic(
                "esbuild_failed",
                bundle=bundle,
                error=type(exc).__name__,
                fail_closed=self._is_esbuild_fail_closed(),
            )
            if self._is_esbuild_fail_closed():
                raise EsbuildBundleError(
                    f"esbuild failed for bundle {bundle!r}: {exc}"
                ) from exc
            self._open_esbuild_circuit(bundle, reason=type(exc).__name__)
            return EsbuildResult("", None, None)
        self._close_esbuild_circuit(bundle)
        return result

    def _compile_with_esbuild_locked(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        assets_params: dict[str, Any] | None,
        page_scope: tuple[str, ...] = (),
        standalone: bool = False,
    ) -> tuple[EsbuildResult, list[AssetsBundle]]:
        empty = EsbuildResult("", None, None)
        child_bundles: list[AssetsBundle] = []
        if not self._can_compile_with_esbuild(bundle):
            _debug.logic("esbuild_declined", bundle=bundle, standalone=standalone)
            return empty, child_bundles
        if assets_params is None:
            assets_params = self.env["ir.asset"]._prepare_assets_params()

        with self._get_esbuild_lock_cursor(bundle) as lock_cr:
            if lock_cr is None:
                _debug.logic("esbuild_declined", bundle=bundle, reason="no_lock_cursor")
                log_event(
                    _fallback_log, logging.INFO, "lock_unavailable", bundle=bundle
                )
                return empty, child_bundles
            self._acquire_esbuild_lock(bundle, cr=lock_cr)

            child_bundles = self._get_dynamic_child_bundles(
                bundle, assets_params, debug_assets=False
            )
            _debug.pipeline(
                "esbuild_children_resolved",
                bundle=bundle,
                children=len(child_bundles),
                standalone=standalone,
                page_scope=len(page_scope),
            )
            exported_specs = None
            registered_reach = None
            if standalone:
                dynamic_child_specs, secondary_stubs = None, {}
            else:
                dynamic_child_specs, secondary_stubs = (
                    self._get_esbuild_child_externals(
                        bundle, asset_bundle, assets_params, child_bundles, page_scope
                    )
                )
                registry = esm_registry()
                if bundle in registry.secondary_bundle_names:
                    registered_reach = self._get_secondary_inlined_reach(
                        bundle, assets_params, page_scope, sec_ab=asset_bundle
                    )
                    _debug.logic(
                        "esbuild_bundle_kind",
                        bundle=bundle,
                        kind="secondary",
                        registered_reach=len(registered_reach),
                    )
                elif bundle not in registry.import_map_included_bundles:
                    exported_specs = self._get_exported_specs(
                        bundle, asset_bundle, assets_params, child_bundles
                    )
                    _debug.logic(
                        "esbuild_bundle_kind",
                        bundle=bundle,
                        kind="exporting",
                        exported=len(exported_specs),
                    )
            source_key = self._esm_source_key(
                bundle,
                asset_bundle,
                dynamic_child_specs,
                secondary_stubs,
                exported_specs,
            )
            reused = self._load_esbuild_result_by_source(bundle, source_key)
            if reused is not None:
                _debug.logic("esbuild_result", bundle=bundle, by="reused")
                return reused, child_bundles
            result = self._compile_with_esbuild(
                bundle,
                asset_bundle,
                dynamic_child_specs,
                secondary_stubs,
                exported_specs,
                registered_reach,
            )
            if result.code:
                result = result._replace(source_key=source_key)
            _debug.logic(
                "esbuild_result",
                bundle=bundle,
                by="compiled" if result.code else "fallback",
                standalone=standalone,
                exported=len(exported_specs or ()),
            )
        return result, child_bundles

    def _esm_source_key(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        dynamic_child_specs: frozenset[str] | None,
        secondary_stubs: dict[str, str],
        exported_specs: frozenset[str] | None,
    ) -> str:
        config = self._get_esbuild_config()
        return esm_index.source_key(
            bundle,
            asset_bundle.native_modules,
            dynamic_child_specs,
            secondary_stubs,
            exported_specs,
            str(
                config.get_param("web.esbuild.target")
                or EsbuildCompiler._ESBUILD_TARGET
            ),
            str(
                config.get_param("web.esbuild.source_maps")
                or EsbuildCompiler._ESBUILD_SOURCE_MAPS
            ),
        )

    def _read_generated_asset(self, url: str) -> bytes | None:
        IrAttachment = self.env["ir.attachment"].sudo()
        row = IrAttachment.search(
            IrAttachment._get_domain_generated_assets(url), limit=1
        )
        return row.raw if row else None

    def _load_esbuild_result_by_source(
        self, bundle: str, source_key: str
    ) -> EsbuildResult | None:
        found = esm_index.resolve_index(self._read_generated_asset, bundle, source_key)
        if found is None:
            _debug.perf.count("esbuild_index_miss", bundle=bundle)
            return None
        url, code, metafile, sourcemap = found
        log_event(
            _fallback_log, logging.DEBUG, "reuse_by_source", bundle=bundle, url=url
        )
        return EsbuildResult(code, metafile, sourcemap, source_key, prebuilt=True)

    _SPECIFIER_LITERAL_RE = re.compile(r"""["'](@[\w./+-]+)["']""")

    def _get_export_consumers(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        assets_params: dict[str, Any] | None,
        child_bundles: list[AssetsBundle],
    ) -> list[AssetsBundle]:
        registry = esm_registry()
        installed = self.env["ir.asset"]._get_addons_installed()
        consumers = list(child_bundles)
        consumer_names = {child.name for child in consumers}

        def add_consumer(name: str) -> None:
            if name in consumer_names or registry.bundle_addon(name) not in installed:
                return
            consumer_names.add(name)
            consumers.append(
                self._get_asset_bundle(
                    name,
                    js=True,
                    css=False,
                    debug_assets=True,
                    assets_params=assets_params,
                )
            )

        # A consumer is declared under a bundle NAME, and the name it is
        # declared under need not be the bundle that serves the page:
        # `web.assets_frontend` is a logical parent that pages load as
        # `web.assets_frontend_minimal` plus `web.assets_frontend_lazy`, and
        # survey declares its secondary bundles under the logical one. So a
        # consumer of any bundle whose modules this bundle carries is a
        # consumer of this bundle -- otherwise `@web/core/browser/cookie`, a
        # member of the minimal bundle alone, was registered by nobody and the
        # survey form's bridge read `undefined` for it.
        member_paths = {asset.module_path for asset in asset_bundle.native_modules}
        for mapping in (
            registry.secondary_import_map_includes,
            registry.import_map_includes,
            registry.dynamic_children,
        ):
            for parent, children in mapping.items():
                if registry.bundle_addon(parent) not in installed:
                    continue
                if not any(registry.bundle_addon(c) in installed for c in children):
                    continue
                if parent != bundle:
                    parent_specs = set(
                        self._get_native_module_data_cached(
                            parent, assets_params=assets_params
                        )["import_map"]
                    )
                    if not member_paths <= parent_specs:
                        continue
                for name in children:
                    add_consumer(name)
        declared_children = {
            name for children in registry.dynamic_children.values() for name in children
        }
        for name in sorted(registry.runtime_bundle_names - declared_children):
            add_consumer(name)
        _debug.pipeline(
            "export_consumers",
            bundle=bundle,
            children=len(child_bundles),
            consumers=len(consumers),
            members=len(member_paths),
        )
        return consumers

    def _get_exported_specs(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        assets_params: dict[str, Any] | None,
        child_bundles: list[AssetsBundle],
    ) -> frozenset[str]:
        members = {
            name
            for asset in asset_bundle.native_modules
            for name in module_specifiers(asset)
        }
        consumers = self._get_export_consumers(
            bundle, asset_bundle, assets_params, child_bundles
        )
        exported = {"@web/core/templates", "@web/core/assets"} & members
        exported.update(esm_registry().exports & members)
        exported.update(_get_specs_imported_by_consumers(consumers, members))
        # the page's import map bridges every specifier a dynamic child's
        # modules import that the page does not serve as a file
        # (`_get_esm_import_map_prod`): a per-file fallback of a secondary
        # resolves its imports through those bridges, so each one this bundle
        # carries, it registers
        for child in child_bundles:
            bridged, _ext = child._bridges._discover_bridge_specifiers(
                set(), set(external_libs()), modules=child.native_modules
            )
            exported.update(bridged.keys() & members)
        sources = {
            source.unique_descriptor: source
            for source in (
                *asset_bundle.native_modules,
                *(a for c in consumers for a in c.native_modules),
            )
        }
        for descriptor, source in sources.items():
            exported.update(self._get_specifier_literals(descriptor, source) & members)
        log_event(
            _fallback_log,
            logging.DEBUG,
            "exported_specs",
            bundle=bundle,
            members=len(members),
            exported=len(exported),
            consumers=len(consumers),
        )
        return frozenset(exported)

    @classmethod
    def _get_specifier_literals(cls, descriptor: str, source: Any) -> frozenset[str]:
        literals = _SPECIFIER_LITERALS_CACHE.get(descriptor)
        _debug.perf.count("specifier_literals", cached=literals is not None)
        if literals is None:
            body = _TRANSITIVE_IMPORT_RE.sub("", source.raw_content)
            literals = frozenset(cls._SPECIFIER_LITERAL_RE.findall(body))
            _SPECIFIER_LITERALS_CACHE[descriptor] = literals
        return literals

    def _get_runtime_parent_specs(
        self,
        parents: tuple[str, ...],
        assets_params: dict[str, Any] | None,
        with_test_satellites: bool = False,
    ) -> frozenset[str]:
        registry = esm_registry()
        installed = self.env["ir.asset"]._get_addons_installed()
        spec_sets = []
        for parent in parents:
            owners = [
                parent,
                *(
                    name
                    for name in registry.import_map_includes.get(parent, ())
                    if registry.bundle_addon(name) in installed
                ),
            ]
            if with_test_satellites:
                owners.extend(
                    name
                    for name in registry.secondary_import_map_includes.get(parent, ())
                    if registry.bundle_addon(name) in installed
                )
            specs: set[str] = set()
            for owner in owners:
                specs |= set(
                    self._get_asset_bundle(
                        owner,
                        js=True,
                        css=False,
                        debug_assets=False,
                        assets_params=assets_params,
                    ).get_native_module_data(with_bridges=False)["import_map"]
                )
                if owner != parent:
                    specs |= set(
                        self._get_secondary_inlined_reach(
                            owner, assets_params, page_scope=(parent,)
                        )
                    )
            if specs:
                spec_sets.append(specs)
        if not spec_sets:
            _debug.logic("runtime_parent_specs", parents=parents, counted=0)
            return frozenset()
        shared = frozenset(set.intersection(*spec_sets))
        _debug.logic(
            "runtime_parent_specs",
            parents=parents,
            counted=len(spec_sets),
            shared=len(shared),
            with_test_satellites=with_test_satellites,
        )
        return shared

    def _get_runtime_child_own_modules(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        parent_specs: frozenset[str],
    ) -> tuple[list, set[str], set[str]]:
        external_urls = set(external_libs().values())
        own_modules = [
            asset
            for asset in asset_bundle.native_modules
            if asset.module_path not in parent_specs and asset.url not in external_urls
        ]
        own_specs = {name for asset in own_modules for name in module_specifiers(asset)}
        discovered, _ext = asset_bundle._bridges._discover_reachable_specifiers(
            own_specs, set(external_libs()), provided=parent_specs, modules=own_modules
        )
        reached = set(discovered) | {
            resolved
            for _module, _spec, resolved in get_escaping_relative_imports(
                own_modules, own_specs
            )
        }
        inlined = sorted(set(discovered) - parent_specs)
        if inlined:
            log_event(
                _fallback_log,
                logging.WARNING,
                "runtime_child_inlines",
                bundle=bundle,
                count=len(inlined),
                specs=",".join(inlined[:5]),
            )
        log_event(
            _fallback_log,
            logging.DEBUG,
            "runtime_child",
            bundle=bundle,
            members=len(asset_bundle.native_modules),
            own=len(own_modules),
            stubbed_members=len(asset_bundle.native_modules) - len(own_modules),
        )
        return own_modules, own_specs, reached & parent_specs

    def _prepare_runtime_group(
        self,
        parents: tuple[str, ...],
        children: dict[str, AssetsBundle],
        assets_params: dict[str, Any] | None,
        with_test_satellites: bool = False,
    ) -> tuple[dict[str, list], dict[str, str], frozenset[str]]:
        parent_specs = self._get_runtime_parent_specs(
            parents, assets_params, with_test_satellites
        )
        entries: dict[str, list] = {}
        stubbed: set[str] = set()
        for name, child in children.items():
            own_modules, _own_specs, child_stubs = self._get_runtime_child_own_modules(
                name, child, parent_specs
            )
            entries[name] = own_modules
            stubbed |= child_stubs
        reference = next(iter(children.values()))
        with _debug.perf(
            "runtime_group_prepared",
            parents=parents,
            children=len(children),
            parent_specs=len(parent_specs),
            stubbed=len(stubbed),
        ) as span:
            stubs = reference._bridges.prepare_shim_sources(stubbed, strict=True)
            span.set(stubs=len(stubs))
        return entries, stubs, parent_specs

    def _get_runtime_group_source_key(
        self,
        group: str,
        entries: dict[str, list],
        templates: dict[str, str],
        parent_specs: frozenset[str],
        stubs: dict[str, str],
    ) -> str:
        config = self._get_esbuild_config()
        return esm_index.group_source_key(
            group,
            entries,
            templates,
            parent_specs,
            stubs,
            str(
                config.get_param("web.esbuild.target")
                or EsbuildCompiler._ESBUILD_TARGET
            ),
            str(
                config.get_param("web.esbuild.source_maps")
                or EsbuildCompiler._ESBUILD_SOURCE_MAPS
            ),
        )

    def _compile_runtime_group(
        self,
        group: str,
        children: dict[str, AssetsBundle],
        entries: dict[str, list],
        stubs: dict[str, str],
    ) -> EsbuildGroupResult:
        empty = EsbuildGroupResult({}, None)
        if not self._can_compile_with_esbuild(group):
            _debug.logic("esbuild_group_declined", group=group, reason="circuit")
            return empty
        with self._get_esbuild_lock_cursor(group) as lock_cr:
            if lock_cr is None:
                _debug.logic(
                    "esbuild_group_declined", group=group, reason="no_lock_cursor"
                )
                log_event(_fallback_log, logging.INFO, "lock_unavailable", bundle=group)
                return empty
            self._acquire_esbuild_lock(group, cr=lock_cr)
            reference = next(iter(children.values()))
            compiler = EsbuildCompiler(
                group,
                [module for modules in entries.values() for module in modules],
                addon_flags_provider=reference._get_esbuild_addon_flags,
            )
            config = self._get_esbuild_config()
            try:
                with _debug.perf(
                    "esbuild_group",
                    group=group,
                    children=len(children),
                    modules=sum(len(modules) for modules in entries.values()),
                    stubs=len(stubs),
                ):
                    result = compiler.compile_group(
                        entries,
                        timeout_s=config.get_param_int(
                            "web.esbuild.timeout_s", EsbuildCompiler._ESBUILD_TIMEOUT_S
                        ),
                        target=config.get_param("web.esbuild.target")
                        or EsbuildCompiler._ESBUILD_TARGET,
                        source_maps=config.get_param("web.esbuild.source_maps")
                        or EsbuildCompiler._ESBUILD_SOURCE_MAPS,
                        secondary_parent_stubs=stubs or None,
                    )
            except Exception as exc:
                log_event(
                    _fallback_log,
                    logging.WARNING,
                    "esbuild_exception",
                    bundle=group,
                    err=type(exc).__name__,
                    msg=str(exc)[:200],
                )
                _debug.logic(
                    "esbuild_group_failed", group=group, error=type(exc).__name__
                )
                if self._is_esbuild_fail_closed():
                    raise EsbuildBundleError(
                        f"esbuild failed for runtime group {group!r}: {exc}"
                    ) from exc
                self._open_esbuild_circuit(group, reason=type(exc).__name__)
                return empty
            self._close_esbuild_circuit(group)
            _debug.lifecycle(
                "esbuild_group_compiled",
                group=group,
                outputs=len(getattr(result, "outputs", None) or ()),
            )
            return result
