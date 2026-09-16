import logging
from collections.abc import Iterable
from typing import Any

from odoo import models
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.tools.assets.esm_graph import (
    discover_transitive_import_specifiers,
    resolve_specifier_url,
)
from odoo.tools.assets.esm_registry import esm_registry
from odoo.tools.assets.nodes import AssetNode

from odoo.addons.base.models.assetsbundle import AssetsBundle

_esm_log = get_asset_logger("esm")
_debug = DebugLog(__name__)


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _narrow_import_map_nodes(
        self, pre_nodes: list[AssetNode], rendered: frozenset[str]
    ) -> tuple[list[AssetNode], frozenset[str]]:
        nodes: list[AssetNode] = []
        mapped = set(rendered)
        shims = dropped = narrowed_count = 0  # debuglog
        for node in pre_nodes:
            if self._is_loader_shim_node(node):
                shims += 1  # debuglog
                continue
            if not self._is_import_map_node(node):
                nodes.append(node)
                continue
            narrowed = self._narrow_import_map_node(node, mapped)
            if narrowed is None:
                dropped += 1  # debuglog
                continue
            narrowed_count += 1  # debuglog
            mapped |= self._get_import_map_specs([narrowed])
            nodes.append(narrowed)
        _debug.logic(
            "importmap.narrowed",
            nodes=len(pre_nodes),
            kept=len(nodes),
            shims=shims,
            dropped=dropped,
            narrowed=narrowed_count,
            rendered=len(rendered),
            added=len(mapped) - len(rendered),
        )
        return nodes, frozenset(mapped) - rendered

    def _log_narrowed_import_map(self, bundle: str, added: frozenset[str]) -> None:
        log_event(
            _esm_log,
            logging.DEBUG,
            "importmap_narrowed",
            bundle=bundle,
            reason="specs_already_rendered",
            added=len(added),
            specs=",".join(sorted(added)[:5]),
        )

    @staticmethod
    def _merge_child_import_maps(
        import_map: dict[str, str],
        child_bundles: list[AssetsBundle],
        *,
        map_specifiers: bool = True,
    ) -> tuple[list[AssetsBundle], set[str]]:
        dynamic_names = esm_registry().dynamic_bundle_names
        dynamic_bundles = []
        child_specifiers: set[str] = set()
        for child_ab in child_bundles:
            child_data = child_ab.get_native_module_data(with_bridges=False)
            child_specifiers.update(child_data["import_map"])
            if map_specifiers:
                import_map.update(child_data["import_map"])
            if child_ab.name in dynamic_names:
                dynamic_bundles.append(child_ab)
        _debug.pipeline(
            "importmap.children_merged",
            children=len(child_bundles),
            dynamic=len(dynamic_bundles),
            specs=len(child_specifiers),
            mapped=map_specifiers,
            import_map=len(import_map),
        )
        return dynamic_bundles, child_specifiers

    def _merge_include_import_maps(
        self,
        bundle: str,
        import_map: dict[str, str],
        assets_params: dict[str, Any] | None,
        *,
        debug_assets: bool,
        resolve_bridges: bool,
    ) -> tuple[str, ...]:
        include_names = tuple(esm_registry().import_map_includes.get(bundle, ()))
        _debug.pipeline(
            "importmap.includes",
            bundle=bundle,
            includes=len(include_names),
            resolve_bridges=resolve_bridges,
            debug_assets=debug_assets,
        )
        for include_name in include_names:
            if not resolve_bridges:
                include_data = self._get_native_module_data_cached(
                    include_name,
                    assets_params=assets_params,
                )
                import_map.update(include_data["import_map"])
                for spec, shim_url in include_data.get("bridge_import_map", {}).items():
                    import_map.setdefault(spec, shim_url)
                _debug.logic(
                    "importmap.include_merged",
                    bundle=bundle,
                    include=include_name,
                    specs=len(include_data["import_map"]),
                    bridges=len(include_data.get("bridge_import_map", {})),
                    cached=True,
                )
                continue
            include_ab = self._get_asset_bundle(
                include_name,
                js=True,
                css=False,
                debug_assets=debug_assets,
                assets_params=assets_params,
            )
            include_data = include_ab.get_native_module_data(with_bridges=False)
            import_map.update(include_data["import_map"])
            discovered, _ext_seen = include_ab._bridges._discover_bridge_specifiers(
                set(include_data["import_map"]),
                set(self._external_libs()),
            )
            _debug.logic(
                "importmap.include_merged",
                bundle=bundle,
                include=include_name,
                specs=len(include_data["import_map"]),
                bridges=len(discovered),
                cached=False,
            )
            self._add_import_map_bridge_urls(
                import_map,
                discovered,
                drop_unresolved=True,
                bundle=include_name,
            )
        return include_names

    def _get_secondary_provider_specs(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        page_scope: tuple[str, ...],
    ) -> set[str]:
        registry = esm_registry()
        providers = page_scope or registry.secondary_parents.get(bundle) or ()
        installed = self.env["ir.asset"]._get_addons_installed()
        spec_sets = []
        for provider in providers:
            specs = set(
                self._get_asset_bundle(
                    provider,
                    js=True,
                    css=False,
                    debug_assets=False,
                    assets_params=assets_params,
                ).get_native_module_data(with_bridges=False)["import_map"]
            )
            if specs or registry.bundle_addon(provider) in installed:
                spec_sets.append(specs)
        if not spec_sets:
            _debug.logic(
                "importmap.secondary_providers",
                bundle=bundle,
                providers=len(providers),
                counted=0,
                page_scoped=bool(page_scope),
            )
            return set()
        shared = (set.union if page_scope else set.intersection)(*spec_sets)
        _debug.logic(
            "importmap.secondary_providers",
            bundle=bundle,
            providers=len(providers),
            counted=len(spec_sets),
            page_scoped=bool(page_scope),
            combine="union" if page_scope else "intersection",
            shared=len(shared),
        )
        return shared

    def _get_secondary_reach(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        page_scope: tuple[str, ...] = (),
        sec_ab: AssetsBundle | None = None,
    ) -> tuple[frozenset[str], frozenset[str]]:
        if not esm_registry().secondary_parents.get(bundle):
            _debug.logic(
                "importmap.secondary_reach", bundle=bundle, reason="no_parents"
            )
            return frozenset(), frozenset()
        shared = self._get_secondary_provider_specs(bundle, assets_params, page_scope)
        if not shared:
            _debug.logic("importmap.secondary_reach", bundle=bundle, reason="no_shared")
            return frozenset(), frozenset()
        if sec_ab is None:
            sec_ab = self._get_asset_bundle(
                bundle,
                js=True,
                css=False,
                debug_assets=False,
                assets_params=assets_params,
            )
        own_specs = set(sec_ab.get_native_module_data(with_bridges=False)["import_map"])
        external_libs = self._external_libs()
        external_urls = set(external_libs.values())
        discovered, _ext = sec_ab._bridges._discover_reachable_specifiers(
            own_specs,
            set(external_libs),
            provided=shared,
        )
        reached = set(discovered) - own_specs
        # A satellite can explicitly list a module already owned by its parent
        # (for example account's tour helpers). It must reuse that module too.
        owned_modules = {
            asset.module_path
            for asset in sec_ab.native_modules
            if asset.url not in external_urls
        }
        stubbed = frozenset((reached | owned_modules) & shared)
        inlined = frozenset(reached - shared)
        _debug.logic(
            "importmap.secondary_reach",
            bundle=bundle,
            own=len(own_specs),
            shared=len(shared),
            reached=len(reached),
            stubbed=len(stubbed),
            inlined=len(inlined),
        )
        return stubbed, inlined

    def _get_secondary_shared_specs(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        page_scope: tuple[str, ...] = (),
        sec_ab: AssetsBundle | None = None,
    ) -> frozenset[str]:
        stubbed, inlined = self._get_secondary_reach(
            bundle, assets_params, page_scope, sec_ab
        )
        if page_scope and (stubbed or inlined):
            self._warn_on_late_secondary_providers(
                bundle, assets_params, stubbed | inlined, stubbed
            )
        _debug.logic(
            "importmap.secondary_shared",
            bundle=bundle,
            page_scoped=bool(page_scope),
            stubbed=len(stubbed),
            inlined=len(inlined),
        )
        return stubbed

    def _get_secondary_inlined_reach(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        page_scope: tuple[str, ...] = (),
        sec_ab: AssetsBundle | None = None,
    ) -> dict[str, str]:
        # what the satellite carries beyond its own modules: registered by the
        # satellite so a runtime child loaded after it binds to that copy
        _stubbed, inlined = self._get_secondary_reach(
            bundle, assets_params, page_scope, sec_ab
        )
        ext_libs = self._external_libs()
        urls = {spec: resolve_specifier_url(spec, ext_libs) for spec in sorted(inlined)}
        if _debug.logic.enabled and len(urls) != sum(1 for url in urls.values() if url):
            _debug.logic(
                "importmap.inlined_unresolved",
                bundle=bundle,
                inlined=len(urls),
                unresolved=sum(1 for url in urls.values() if not url),
            )
        return {spec: url for spec, url in urls.items() if url}

    def _warn_on_late_secondary_providers(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        discovered: Iterable[str],
        stubbed: frozenset[str],
    ) -> None:
        declared = self._get_secondary_provider_specs(bundle, assets_params, ())
        late = sorted((set(discovered) & declared) - stubbed)
        if not late:
            return
        _debug.logic(
            "importmap.late_providers",
            bundle=bundle,
            declared=len(declared),
            late=len(late),
        )
        log_event(
            _esm_log,
            logging.WARNING,
            "secondary_provider_renders_late",
            bundle=bundle,
            page=",".join(self._get_esm_page_scope(bundle)),
            count=len(late),
            specs=",".join(late[:5]),
        )

    def _get_secondary_parent_stubs(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        page_scope: tuple[str, ...] = (),
    ) -> dict[str, str]:
        sec_ab = self._get_asset_bundle(
            bundle,
            js=True,
            css=False,
            debug_assets=False,
            assets_params=assets_params,
        )
        shared = self._get_secondary_shared_specs(
            bundle, assets_params, page_scope, sec_ab=sec_ab
        )
        if not shared:
            _debug.logic("importmap.parent_stubs", bundle=bundle, shared=0)
            return {}
        with _debug.perf(
            "importmap.parent_stubs", bundle=bundle, shared=len(shared)
        ) as span:
            stubs = sec_ab._bridges.prepare_shim_sources(set(shared), wait=True)
            span.set(stubs=len(stubs))
        return stubs

    def _merge_secondary_import_maps(
        self,
        bundle: str,
        import_map: dict[str, str],
        assets_params: dict[str, Any] | None,
        *,
        debug_assets: bool,
    ) -> None:
        for sec_name in esm_registry().secondary_import_map_includes.get(bundle, ()):
            sec_ab = self._get_asset_bundle(
                sec_name,
                js=True,
                css=False,
                debug_assets=debug_assets,
                assets_params=assets_params,
            )
            sec_data = sec_ab.get_native_module_data(with_bridges=False)
            before = len(import_map)  # debuglog
            for spec, url in sec_data["import_map"].items():
                import_map.setdefault(spec, url)
            _debug.logic(
                "importmap.secondary_merged",
                bundle=bundle,
                secondary=sec_name,
                specs=len(sec_data["import_map"]),
                added=len(import_map) - before,
            )

    def _add_import_map_bridge_urls(
        self,
        import_map: dict[str, str],
        discovered: Iterable[str],
        *,
        drop_unresolved: bool,
        bundle: str = "",
    ) -> dict[str, str]:
        resolved_map = {}
        kept = dropped = seen = 0  # debuglog
        for spec in discovered:
            seen += 1  # debuglog
            current = import_map.get(spec)
            if current and not current.startswith(
                ("/web/assets/esm/bridges/", "data:")
            ):
                kept += 1  # debuglog
                continue
            resolved = self._resolve_specifier_url(spec)
            if resolved:
                import_map[spec] = resolved
                resolved_map[spec] = resolved
            elif current and drop_unresolved:
                dropped += 1  # debuglog
                del import_map[spec]
        transitive = 0  # debuglog
        if resolved_map:
            extra = discover_transitive_import_specifiers(
                resolved_map,
                known_specifiers=set(import_map),
                ext_libs=self._external_libs(),
                bundle_name=bundle,
            )
            for spec in sorted(extra):
                resolved = self._resolve_specifier_url(spec)
                if resolved:
                    transitive += 1  # debuglog
                    import_map[spec] = resolved
                    resolved_map[spec] = resolved
        _debug.logic(
            "importmap.bridge_urls",
            bundle=bundle or None,
            discovered=seen,
            resolved=len(resolved_map) - transitive,
            transitive=transitive,
            kept=kept,
            dropped=dropped,
            drop_unresolved=drop_unresolved,
        )
        return resolved_map
