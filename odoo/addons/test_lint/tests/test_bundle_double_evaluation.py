import logging

from odoo.modules import Manifest
from odoo.tests import tagged
from odoo.tools.assets.esm_graph import (
    discover_transitive_import_specifiers,
    url_to_module_path,
)
from odoo.tools.assets.esm_registry import esm_registry, external_libs

from . import lint_case

_logger = logging.getLogger(__name__)


def _js_specs(ir_asset, bundle, params):
    specs = set()
    for entry in ir_asset._get_asset_paths(bundle, params):
        url = entry[0] if isinstance(entry, (list, tuple)) else entry
        if isinstance(url, str) and url.endswith(".js"):
            if spec := url_to_module_path(url):
                specs.add(spec)
    return specs


def _includes_by_bundle(installed):
    includes = {}
    for name in installed:
        manifest = Manifest.for_addon(name, display_warning=False)
        if not manifest:
            continue
        for bundle, entries in (manifest.get("assets") or {}).items():
            for entry in entries:
                if (
                    isinstance(entry, (list, tuple))
                    and len(entry) == 2
                    and entry[0] == "include"
                ):
                    includes.setdefault(bundle, set()).add(entry[1])
    return includes


def _included_closure(bundle, includes):
    seen = set()
    stack = list(includes.get(bundle, ()))
    while stack:
        current = stack.pop()
        if current not in seen:
            seen.add(current)
            stack.extend(includes.get(current, ()))
    return seen


def _removed_paths_by_bundle(installed):
    removed = {}
    for name in installed:
        manifest = Manifest.for_addon(name, display_warning=False)
        if not manifest:
            continue
        for bundle, entries in (manifest.get("assets") or {}).items():
            for entry in entries:
                if (
                    isinstance(entry, (list, tuple))
                    and len(entry) == 2
                    and entry[0] == "remove"
                    and isinstance(entry[1], str)
                    and entry[1].endswith(".js")
                ):
                    removed.setdefault(bundle, set()).add(entry[1])
    return removed


@tagged("post_install", "-at_install")
class TestBundleDoubleEvaluation(lint_case.LintCase):
    def test_a_removed_file_does_not_come_back_as_an_import(self):
        findings = []
        with self.superuser_env() as env:
            installed = (
                env["ir.module.module"]
                .search([("state", "=", "installed")])
                .mapped("name")
            )
            removed_by_bundle = _removed_paths_by_bundle(installed)
            if not removed_by_bundle:
                self.skipTest("no bundle declares a remove directive")

            ir_asset = env["ir.asset"]
            qweb = env["ir.qweb"]
            params = ir_asset._prepare_assets_params()
            ext = external_libs()

            for bundle, removed_paths in sorted(removed_by_bundle.items()):
                try:
                    paths = ir_asset._get_asset_paths(bundle, params)
                except Exception:
                    _logger.debug("bundle %s does not assemble", bundle, exc_info=True)
                    continue
                seeds = set()
                for entry in paths:
                    url = entry[0] if isinstance(entry, (list, tuple)) else entry
                    if isinstance(url, str) and url.endswith(".js"):
                        if spec := url_to_module_path(url):
                            seeds.add(spec)
                closure = seeds | set(
                    discover_transitive_import_specifiers(seeds, seeds, ext, bundle)
                )
                stubbed = set(qweb._get_secondary_shared_specs(bundle, params))
                for path in sorted(removed_paths):
                    spec = url_to_module_path("/" + path.lstrip("/"))
                    if spec and spec in closure and spec not in stubbed:
                        findings.append(f"{bundle}: {spec} (removed, still inlined)")

        self.assert_ratchet(
            findings,
            "bundle_double_eval",
            "module(s) removed from a bundle and re-inlined by an import",
            "Declare the providing bundle a secondary parent of this one under "
            "`esm.secondary_import_map_includes`, so the import is stubbed to "
            "the shared loader instead of inlined; or give the module a "
            "specifier esbuild leaves external. Detail: agromarin-knowledge/"
            "research/2026-08-27-frontend-bundle-double-evaluation.md.",
            exact=False,
        )
        _logger.info(
            "%s removed-but-reinlined module(s) across %s bundle(s) with removes",
            len(findings),
            len(removed_by_bundle),
        )

    def test_a_secondary_child_reaches_a_split_parent_s_removed_half(self):
        # A bundle that removes files from the one it includes (web.assets_
        # frontend_lazy is web.assets_frontend minus web.assets_frontend_minimal)
        # is rendered beside the bundle holding those files. A secondary child
        # of it that imports one of them must also name that bundle as a
        # parent; naming the full bundle does not count, because it is never on
        # the page beside the split one. Unnamed, the child inlines its own
        # copy and the page runs two (a "singleton split" on the loader).
        findings = []
        with self.superuser_env() as env:
            installed = (
                env["ir.module.module"]
                .search([("state", "=", "installed")])
                .mapped("name")
            )
            removed_by_bundle = _removed_paths_by_bundle(installed)
            includes = _includes_by_bundle(installed)
            ir_asset = env["ir.asset"]
            params = ir_asset._prepare_assets_params()
            ext = external_libs()
            specs_cache = {}

            def specs_of(bundle):
                if bundle not in specs_cache:
                    try:
                        specs_cache[bundle] = _js_specs(ir_asset, bundle, params)
                    except Exception:
                        _logger.debug("bundle %s does not assemble", bundle)
                        specs_cache[bundle] = set()
                return specs_cache[bundle]

            for child, parents in sorted(esm_registry().secondary_parents.items()):
                for parent in parents:
                    removed = removed_by_bundle.get(parent)
                    if not removed:
                        continue
                    seeds = specs_of(child)
                    closure = seeds | set(
                        discover_transitive_import_specifiers(seeds, seeds, ext, child)
                    )
                    # the halves it was cut from: what it includes, minus the
                    # bundle it includes whole (which also holds its own files)
                    parent_specs = specs_of(parent)
                    halves = {
                        half
                        for half in _included_closure(parent, includes)
                        if not parent_specs <= specs_of(half)
                    }
                    for path in sorted(removed):
                        spec = url_to_module_path("/" + path.lstrip("/"))
                        if not spec or spec not in closure or spec in seeds:
                            continue
                        holders = {half for half in halves if spec in specs_of(half)}
                        if holders and not holders & set(parents):
                            findings.append(
                                f"{child} under {parent}: {spec} lives in "
                                f"{', '.join(sorted(holders))}, not a parent"
                            )

        self.assert_ratchet(
            findings,
            "bundle_split_parent",
            "secondary child(ren) importing what a split parent removed",
            "Name the bundle that holds the removed files (for web.assets_frontend_"
            "lazy, web.assets_frontend_minimal) as a parent of the child under "
            "`esm.secondary_import_map_includes`, beside the split one.",
        )
