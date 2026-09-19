import hashlib
import logging
import time
from collections.abc import Collection, Iterable, Sequence
from pathlib import Path
from typing import Any

from lxml import etree
from psycopg.errors import LockNotAvailable, ReadOnlySqlTransaction
from rjsmin import jsmin as _rjsmin

from odoo import SUPERUSER_ID, api, models, tools
from odoo.http import request
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.libs.documents import mimetype_for
from odoo.libs.hashing import cache_hash
from odoo.modules import module as _module
from odoo.tools.assets import esm_index
from odoo.tools.assets.esbuild import EsbuildResult
from odoo.tools.assets.esm_graph import (
    addon_specifier_to_url,
    resolve_specifier_url,
)
from odoo.tools.assets.esm_libs import (
    served_external_libs,
    served_lib_files,
)
from odoo.tools.assets.esm_registry import (
    esm_registry,
    external_lib_aliases,
    external_libs,
)
from odoo.tools.assets.nodes import (
    LOADER_SHIM_MARKER,
    AssetNode,
    bridge_external_specifiers,
    combine_bundle_with_templates,
    count_import_map_urls,
    has_esm_test_satellites,
    import_map_specs,
    inline_module_node,
    is_debug_assets,
    is_hoot_test_specifier,
    is_import_map_node,
    is_loader_shim_node,
    link_to_node,
    narrow_import_map_node,
    prepare_register_native_modules_js,
)
from odoo.tools.json import scriptsafe as json
from odoo.tools.misc import file_path, str2bool

from odoo.addons.base.models.assetsbundle import AssetsBundle, BundleFileSpec

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

EsmNodePair = tuple[list[AssetNode], list[AssetNode]]

_esm_log = get_asset_logger("esm")
_attach_log = get_asset_logger("attach")
_AUTONOMOUS_LOCK_TIMEOUT = "2s"
_fallback_log = get_asset_logger("fallback")
_loader_log = get_asset_logger("loader")
_pregen_log = get_asset_logger("pregen")

_ASSET_CACHE_ENABLED = "xml" not in tools.config["dev_mode"]


class _BuildDeclined(Exception):
    pass


class _EsmFallbackError(_BuildDeclined):
    pass


class _EsmReadonlyDeclined(_EsmFallbackError):
    pass


class _StandaloneBundleDeclined(_BuildDeclined):
    pass


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _render(
        self,
        template: int | str | etree._Element,
        values: dict[str, Any] | None = None,
        **options: Any,
    ):
        # The request's page state (whether an import map was written, which
        # specifiers it maps, which bundles are on the page) describes one HTML
        # document. A render not nested in another starts a document of its own:
        # a controller may render two, as Studio's report editor does for the
        # report and for the iframe that shows it, and the second one must map
        # the specifiers the first one already mapped in a different document.
        # `is True`: a request stood in for by a Mock answers any attribute with
        # another Mock, which is truthy and is not a document this render opened
        document_open = (
            getattr(request, "_esm_document_open", False) if request else False
        )
        if document_open is not True and document_open:
            _debug.logic(
                "esm_document_flag_ignored",
                template=template,
                flag=type(document_open).__name__,
            )
        if not request or document_open is True:
            return super()._render(template, values, **options)
        _debug.lifecycle("esm_document_opened", template=template)
        request._esm_import_map_rendered = False
        request._esm_import_map_specs = frozenset()
        request._esm_page_bundles = ()
        request._esm_document_open = True
        try:
            return super()._render(template, values, **options)
        finally:
            request._esm_document_open = False

    def _get_asset_nodes(
        self,
        bundle: str,
        css: bool = True,
        js: bool = True,
        debug: str = "",
        defer_load: bool = False,
        lazy_load: bool = False,
        media: str | None = None,
        autoprefix: bool = False,
        page: bool = False,
    ) -> list[AssetNode]:
        media = (css and media) or None
        links = self._get_asset_links(
            bundle, css=css, js=js, debug=debug, autoprefix=autoprefix
        )

        pre_nodes = []
        post_nodes = []
        has_native = False
        if js:
            pre_nodes, post_nodes = self._get_native_module_nodes(
                bundle,
                debug=debug,
                page=page,
            )
            has_native = bool(pre_nodes) or bool(post_nodes)

        nodes = self._links_to_nodes(
            links,
            defer_load=defer_load,
            lazy_load=lazy_load,
            media=media,
        )

        log_event(
            _esm_log,
            logging.DEBUG,
            "nodes",
            bundle=bundle,
            debug=bool(debug),
            css=css,
            js=js,
            links=len(nodes),
            pre=len(pre_nodes),
            post=len(post_nodes),
            native=has_native,
        )
        _debug.pipeline(
            "asset_nodes",
            bundle=bundle,
            debug=bool(debug),
            links=len(nodes),
            pre=len(pre_nodes),
            post=len(post_nodes),
            native=has_native,
        )
        if has_native:
            return pre_nodes + nodes + post_nodes

        return nodes

    _is_debug_assets = staticmethod(is_debug_assets)

    def _get_asset_urls(
        self,
        bundle: str,
        css: bool = True,
        js: bool = True,
        debug: str | None = None,
    ) -> list[str]:
        urls = []
        for _tag, attrs in self._get_asset_nodes(bundle, css=css, js=js, debug=debug):
            url = attrs.get("src") or attrs.get("href")
            if url and url not in urls:
                urls.append(url)
        _debug.perf.count("asset_urls", bundle=bundle, urls=len(urls))
        return urls

    def _get_asset_links(
        self,
        bundle: str,
        css: bool = True,
        js: bool = True,
        debug: str | None = None,
        autoprefix: bool = False,
    ) -> list[str]:
        rtl = css and self._is_rtl_language()
        autoprefix = css and autoprefix
        assets_params = self.env["ir.asset"]._prepare_assets_params()

        if self._is_debug_assets(debug):
            _debug.logic("asset_links_uncached_path", bundle=bundle, reason="debug")
            return self._get_asset_links_uncached(
                bundle,
                css=css,
                js=js,
                debug_assets=True,
                assets_params=assets_params,
                rtl=rtl,
                autoprefix=autoprefix,
            )
        return self._get_asset_links_cached(
            bundle,
            css=css,
            js=js,
            assets_params=assets_params,
            rtl=rtl,
            autoprefix=autoprefix,
        )

    def _is_rtl_language(self) -> bool:
        return (
            self.env["res.lang"]
            .sudo()
            ._get_data(code=(self.env.lang or self.env.user.lang))
            .direction
            == "rtl"
        )

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "bundle",
            "css",
            "js",
            "tuple(sorted(assets_params.items()))",
            "rtl",
            "autoprefix",
            cache="assets.links",
        ),
    )
    def _get_asset_links_cached(
        self,
        bundle: str,
        css: bool = True,
        js: bool = True,
        assets_params: dict[str, Any] | None = None,
        rtl: bool = False,
        autoprefix: bool = False,
    ) -> list[str]:
        return self._get_asset_links_uncached(
            bundle, css, js, False, assets_params, rtl, autoprefix=autoprefix
        )

    def _get_asset_content(
        self, bundle: str, assets_params: dict[str, Any] | None = None
    ) -> tuple[list[BundleFileSpec], list[str]]:
        if assets_params is None:
            assets_params = self.env["ir.asset"]._prepare_assets_params()
        asset_paths = self.env["ir.asset"]._get_asset_paths(
            bundle=bundle, assets_params=assets_params
        )
        files = []
        external_asset = []
        for asset in asset_paths:
            if asset.is_external:
                external_asset.append(asset.path)
            else:
                files.append(
                    {
                        "url": asset.path,
                        "filename": asset.full_path,
                        "content": "",
                        "last_modified": asset.last_modified,
                    }
                )
        _debug.pipeline(
            "asset_content",
            bundle=bundle,
            files=len(files),
            external=len(external_asset),
        )
        return (files, external_asset)

    def _get_asset_bundle(
        self,
        bundle_name: str,
        css: bool = True,
        js: bool = True,
        debug_assets: bool = False,
        rtl: bool = False,
        assets_params: dict[str, Any] | None = None,
        autoprefix: bool = False,
    ) -> AssetsBundle:
        if assets_params is None:
            assets_params = self.env["ir.asset"]._prepare_assets_params()
        files, external_assets = self._get_asset_content(bundle_name, assets_params)
        return AssetsBundle(
            bundle_name,
            files,
            external_assets,
            env=self.env,
            css=css,
            js=js,
            debug_assets=debug_assets,
            rtl=rtl,
            assets_params=assets_params,
            autoprefix=autoprefix,
        )

    def _links_to_nodes(
        self,
        paths: list[str],
        defer_load: bool = False,
        lazy_load: bool = False,
        media: str | None = None,
    ) -> list[AssetNode]:
        nodes = []
        for path in paths:
            node = self._link_to_node(
                path, defer_load=defer_load, lazy_load=lazy_load, media=media
            )
            if node is None:
                _logger.warning(
                    "Asset path %r has no renderable node (unrecognized extension); skipped.",
                    path,
                )
                _debug.logic("link_skipped", path=path, reason="no_node")
                continue
            nodes.append(node)
        return nodes

    @staticmethod
    def _link_to_node(
        path: str,
        defer_load: bool = False,
        lazy_load: bool = False,
        media: str | None = None,
    ) -> AssetNode | None:
        return link_to_node(
            path, defer_load=defer_load, lazy_load=lazy_load, media=media
        )

    def _get_asset_links_uncached(
        self,
        bundle: str,
        css: bool = True,
        js: bool = True,
        debug_assets: bool = False,
        assets_params: dict[str, Any] | None = None,
        rtl: bool = False,
        autoprefix: bool = False,
    ) -> list[str]:
        with _debug.perf(
            "asset_links_uncached",
            cr=self.env.cr,
            bundle=bundle,
            css=css,
            js=js,
            debug=debug_assets,
            rtl=rtl,
        ) as span:
            asset_bundle = self._get_asset_bundle(
                bundle,
                css=css,
                js=js,
                debug_assets=debug_assets,
                rtl=rtl,
                assets_params=assets_params,
                autoprefix=autoprefix,
            )
            links = asset_bundle.get_links()
            span.set(links=len(links))
        return links

    _external_libs = staticmethod(external_libs)
    _served_external_libs_table = staticmethod(served_external_libs)
    _served_lib_files = staticmethod(served_lib_files)

    _specifier_to_static_url = staticmethod(addon_specifier_to_url)

    def _resolve_specifier_url(self, spec: str) -> str | None:
        return resolve_specifier_url(spec, self._external_libs())

    _get_import_map_url_counts = staticmethod(count_import_map_urls)

    _combine_bundle_with_templates = staticmethod(combine_bundle_with_templates)

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "bundle",
            "tuple(sorted(assets_params.items()))",
            cache="assets",
        ),
    )
    def _get_native_module_data_cached(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None = None,
    ) -> dict:
        asset_bundle = self._get_asset_bundle(
            bundle,
            js=True,
            css=False,
            debug_assets=False,
            assets_params=assets_params,
        )
        with _debug.perf("native_module_data_uncached", bundle=bundle) as span:
            data = asset_bundle.get_native_module_data()
            span.set(specifiers=len(data.get("import_map", ())))
        return data

    def _get_standalone_bundle(self, bundle: str) -> tuple[str, str] | None:
        assets_params = self.env["ir.asset"]._prepare_assets_params()
        try:
            return self._get_standalone_bundle_cached(bundle, assets_params)
        except _StandaloneBundleDeclined:
            _debug.logic("standalone_bundle_declined", bundle=bundle)
            return None

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "bundle",
            "tuple(sorted(assets_params.items()))",
            cache="assets",
        ),
    )
    def _get_standalone_bundle_cached(
        self, bundle: str, assets_params: dict[str, Any]
    ) -> tuple[str, str]:
        with _debug.perf("standalone_bundle_uncached", bundle=bundle) as span:
            asset_bundle = self._get_asset_bundle(
                bundle, css=False, assets_params=assets_params
            )
            esbuild_result, _child_bundles = self._compile_with_esbuild_locked(
                bundle, asset_bundle, assets_params, standalone=True
            )
            if not esbuild_result.code:
                _debug.logic(
                    "standalone_bundle_declined", bundle=bundle, reason="no_code"
                )
                raise _StandaloneBundleDeclined
            code = self._combine_bundle_with_templates(
                esbuild_result.code,
                asset_bundle.generate_esm_template_bundle(use_import=False),
            )
            code = self._prepare_loader_shim_js() + "\n" + code
            try:
                url = self._save_esm_attachment(
                    bundle,
                    code,
                    metafile=esbuild_result.metafile,
                    sourcemap=None,
                )
            except Exception as exc:
                _logger.warning(
                    "Could not persist the standalone bundle %s", bundle, exc_info=True
                )
                raise _StandaloneBundleDeclined from exc
            span.set(bytes=len(code))
        return url, code

    def _get_esm_bundle_payload(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None = None,
        debug_assets: bool = False,
        page: str | None = None,
        with_test_satellites: bool | None = None,
    ) -> dict:
        if assets_params is None:
            assets_params = self.env["ir.asset"]._prepare_assets_params()
        if with_test_satellites is None:
            with_test_satellites = self._has_esm_test_satellites("")
        carried = bool(page) and self._page_carries_bundle(
            page, bundle, assets_params, with_test_satellites
        )
        _debug.logic(
            "esm_payload_route",
            bundle=bundle,
            page=page,
            carried=carried,
            debug=debug_assets,
        )
        if debug_assets:
            return self._get_esm_bundle_payload_uncached(
                bundle, assets_params, carried=carried
            )
        return self._get_esm_bundle_payload_cached(
            bundle,
            assets_params,
            self._get_runtime_group_parents(
                bundle, page, assets_params, with_test_satellites
            ),
            with_test_satellites,
            carried,
        )

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "bundle",
            "tuple(sorted(assets_params.items()))",
            "parents",
            "with_test_satellites",
            "carried",
            cache="assets",
        ),
    )
    def _get_esm_bundle_payload_cached(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None = None,
        parents: tuple[str, ...] = (),
        with_test_satellites: bool = False,
        carried: bool = False,
    ) -> dict:
        return self._get_esm_bundle_payload_uncached(
            bundle,
            assets_params,
            compiled=True,
            parents=parents,
            with_test_satellites=with_test_satellites,
            carried=carried,
        )

    @staticmethod
    def _is_runtime_child_compiled(bundle: str) -> bool:
        registry = esm_registry()
        return (
            bundle in registry.runtime_bundle_names
            and bundle not in registry.import_map_included_bundles
            and any(bundle in kids for kids in registry.dynamic_children.values())
        )

    def _get_runtime_group_parents(
        self,
        bundle: str,
        page: str | None = None,
        assets_params: dict[str, Any] | None = None,
        with_test_satellites: bool = False,
    ) -> tuple[str, ...]:
        registry = esm_registry()
        installed = self.env["ir.asset"]._get_addons_installed()
        declared = tuple(
            sorted(
                parent
                for parent, children in registry.dynamic_children.items()
                if bundle in children and registry.bundle_addon(parent) in installed
            )
        )
        if not page or not declared:
            return declared
        if page in declared or self._page_carries_bundle(
            page, bundle, assets_params, with_test_satellites
        ):
            _debug.logic("runtime_group_parents", bundle=bundle, page=page, by="page")
            return (page,)
        contributors = set(self._get_dynamic_parent_bundles(page, assets_params))
        matches = [parent for parent in declared if parent in contributors]
        _debug.logic(
            "runtime_group_parents",
            bundle=bundle,
            page=page,
            by="contributors",
            declared=len(declared),
            matches=len(matches),
        )
        if len(matches) == 1:
            return (matches[0],)
        return declared

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "page",
            "bundle",
            "tuple(sorted((assets_params or {}).items()))",
            "with_test_satellites",
            cache="assets",
        ),
    )
    def _page_carries_bundle(
        self,
        page: str,
        bundle: str,
        assets_params: dict[str, Any] | None,
        with_test_satellites: bool = False,
    ) -> bool:
        own = {
            asset.module_path
            for asset in self._get_asset_bundle(
                bundle,
                js=True,
                css=False,
                debug_assets=False,
                assets_params=assets_params,
            ).native_modules
        }
        if not own:
            _debug.logic(
                "page_carries_bundle", page=page, bundle=bundle, reason="no_own"
            )
            return False
        carried = self._get_runtime_parent_specs(
            (page,), assets_params, with_test_satellites
        )
        _debug.logic(
            "page_carries_bundle",
            page=page,
            bundle=bundle,
            own=len(own),
            carried=len(carried),
            result=own <= carried,
        )
        return own <= carried

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "parents",
            "tuple(sorted(assets_params.items()))",
            "with_test_satellites",
            cache="assets",
        ),
    )
    def _get_runtime_group_urls_cached(
        self,
        parents: tuple[str, ...],
        assets_params: dict[str, Any],
        with_test_satellites: bool = False,
    ) -> dict[str, str]:
        return self._get_runtime_group_urls_uncached(
            parents, assets_params, with_test_satellites
        )

    def _get_runtime_group_urls_uncached(
        self,
        parents: tuple[str, ...],
        assets_params: dict[str, Any] | None,
        with_test_satellites: bool = False,
    ) -> dict[str, str]:
        registry = esm_registry()
        installed = self.env["ir.asset"]._get_addons_installed()
        children = {}
        for name in sorted(registry.runtime_bundle_names):
            if registry.bundle_addon(name) not in installed:
                continue
            if not self._is_runtime_child_compiled(name):
                continue
            declared = self._get_runtime_group_parents(name)
            in_group = (
                parents[0] in declared if len(parents) == 1 else declared == parents
            )
            if not in_group:
                continue
            child = self._get_asset_bundle(
                name,
                js=True,
                css=False,
                debug_assets=False,
                assets_params=assets_params,
            )
            if child.native_modules:
                children[name] = child
        _debug.pipeline(
            "runtime_group_children",
            parents=list(parents),
            candidates=len(registry.runtime_bundle_names),
            children=sorted(children),
        )
        if not children:
            return {}
        group = (
            "runtime:" + "+".join(parents) + (":tests" if with_test_satellites else "")
        )
        entries, stubs, parent_specs = self._prepare_runtime_group(
            parents, children, assets_params, with_test_satellites
        )
        templates = {
            name: child.generate_esm_template_bundle(use_import=False)
            for name, child in children.items()
        }
        source_key = self._get_runtime_group_source_key(
            group, entries, templates, parent_specs, stubs
        )
        # a process that has not compiled yet serves what another one did
        reused = esm_index.resolve_group_index(
            self._read_generated_asset, group, source_key
        )
        if reused is not None:
            log_event(
                _fallback_log,
                logging.DEBUG,
                "group_reuse_by_source",
                bundle=group,
                children=len(reused),
            )
            _debug.logic("runtime_group_reused", group=group, children=len(reused))
            return reused
        with _debug.perf(
            "runtime_group_compile",
            cr=self.env.cr,
            group=group,
            children=len(children),
            entries=len(entries),
            stubs=len(stubs),
        ) as span:
            result = self._compile_runtime_group(group, children, entries, stubs)
            span.set(files=len(result.files))
        if not result.files:
            log_event(
                _fallback_log, logging.INFO, "runtime_group_per_file", bundle=group
            )
            return {}
        files = {}
        for filename, code in result.files.items():
            name = filename.removesuffix(".esm.js")
            if name in children:
                code = self._combine_bundle_with_templates(code, templates[name])
            files[filename] = code.encode("utf-8")
        if result.metafile:
            files["group.meta.json"] = result.metafile.encode("utf-8")
        try:
            urls = self._save_esm_group(group, files, set(children))
            self._save_esm_attachment_rows(
                [esm_index.group_index_row(group, source_key, urls)], bundle=group
            )
            return urls
        except ReadOnlySqlTransaction:
            _debug.logic("runtime_group_save_declined", group=group, reason="readonly")
            raise
        except Exception as exc:
            log_event(
                _attach_log,
                logging.WARNING,
                "runtime_group_save_failed",
                bundle=group,
                readonly=bool(self.env.cr.readonly),
                err=type(exc).__name__,
            )
            return {}

    def _save_esm_group(
        self, group: str, files: dict[str, bytes], children: Iterable[str]
    ) -> dict[str, str]:
        digest = hashlib.sha256()
        for filename in sorted(files):
            digest.update(filename.encode())
            digest.update(b"\0")
            digest.update(files[filename])
            digest.update(b"\0")
        unique = digest.hexdigest()[:16]
        prefix = f"/web/assets/esm/{unique}/"
        IrAttachment = self.env["ir.attachment"].sudo()
        existing = IrAttachment.search(
            IrAttachment._get_domain_generated_assets(url_pattern=f"{prefix}%")
        )
        present = set(existing.mapped("url"))
        vals_list = [
            IrAttachment._prepare_generated_asset_vals(
                name=filename,
                mimetype=(
                    "text/javascript"
                    if filename.endswith(".js")
                    else "application/json"
                ),
                raw=content,
                url=f"{prefix}{filename}",
            )
            for filename, content in files.items()
            if f"{prefix}{filename}" not in present
        ]
        self._save_esm_attachment_rows(vals_list, touch_ids=existing.ids, bundle=group)
        _debug.lifecycle(
            "esm_group_saved",
            group=group,
            files=len(files),
            new=len(vals_list),
            reused=len(existing),
        )
        log_event(
            _attach_log,
            logging.INFO,
            "group_save" if vals_list else "group_reuse",
            bundle=group,
            url=prefix,
            files=len(files),
            new=len(vals_list),
            bytes=sum(len(content) for content in files.values()),
        )
        # a child whose modules the page already carries compiles to no file
        return {
            name: f"{prefix}{name}.esm.js"
            for name in children
            if f"{name}.esm.js" in files
        }

    def _get_compiled_runtime_payload(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        parents: tuple[str, ...],
        with_test_satellites: bool = False,
    ) -> dict | None:
        if not parents:
            _debug.logic("compiled_runtime_payload", bundle=bundle, reason="no_parents")
            return None
        urls = self._get_runtime_group_urls_cached(
            parents, assets_params or {}, with_test_satellites
        )
        if not urls:
            log_event(
                _fallback_log, logging.INFO, "runtime_child_per_file", bundle=bundle
            )
            _debug.logic("compiled_runtime_payload", bundle=bundle, reason="no_urls")
            return None
        asset_bundle = self._get_asset_bundle(
            bundle,
            js=True,
            css=False,
            debug_assets=False,
            assets_params=assets_params,
        )
        payload = {
            "specifiers": sorted(a.module_path for a in asset_bundle.native_modules),
            "import_map": self._get_external_libs_served(debug_assets=False),
            "template_url": None,
        }
        url = urls.get(bundle)
        _debug.logic(
            "compiled_runtime_payload",
            bundle=bundle,
            in_group=bool(url),
            specifiers=len(payload["specifiers"]),
        )
        if url:
            payload["esm_url"] = url
            return payload
        return self._get_carried_bundle_payload(bundle, asset_bundle)

    def _get_carried_bundle_payload(
        self, bundle: str, asset_bundle: AssetsBundle
    ) -> dict:
        # the page carries every module of this bundle: the browser imports
        # the specifiers it already maps, and no per-file import map may
        # offer it a second copy of them
        log_event(_esm_log, logging.DEBUG, "bundle_carried", bundle=bundle)
        payload = {
            "specifiers": sorted(a.module_path for a in asset_bundle.native_modules),
            "import_map": self._get_external_libs_served(debug_assets=False),
            "template_url": None,
            "carried": True,
        }
        esm_tpl = asset_bundle.generate_esm_template_bundle(use_import=False)
        if esm_tpl:
            payload["template_url"] = self._save_esm_attachment(
                f"{bundle}.templates", esm_tpl
            )
        _debug.pipeline(
            "carried_bundle_payload",
            bundle=bundle,
            specifiers=len(payload["specifiers"]),
            templates=bool(esm_tpl),
        )
        return payload

    def _get_esm_bundle_payload_uncached(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        compiled: bool = False,
        parents: tuple[str, ...] = (),
        with_test_satellites: bool = False,
        carried: bool = False,
    ) -> dict:
        if carried:
            return self._get_carried_bundle_payload(
                bundle,
                self._get_asset_bundle(
                    bundle,
                    js=True,
                    css=False,
                    debug_assets=False,
                    assets_params=assets_params,
                ),
            )
        if compiled and self._is_runtime_child_compiled(bundle):
            payload = self._get_compiled_runtime_payload(
                bundle, assets_params, parents, with_test_satellites
            )
            if payload is not None:
                return payload
            _debug.logic("esm_payload_fallback", bundle=bundle, reason="no_group")
        asset_bundle = self._get_asset_bundle(
            bundle,
            js=True,
            css=False,
            debug_assets=True,
            assets_params=assets_params,
        )
        self._check_lazy_bundle_relative_imports(asset_bundle)
        with _debug.perf("esm_payload_uncached", bundle=bundle, compiled=compiled):
            native_data = asset_bundle.get_native_module_data()
        import_map = self._get_external_libs_served(debug_assets=not compiled)
        import_map.update(native_data["import_map"])
        import_map.update(native_data.get("bridge_import_map", {}))
        template_url = None
        esm_tpl = asset_bundle.generate_esm_template_bundle(use_import=False)
        if esm_tpl:
            template_url = self._save_esm_attachment(f"{bundle}.templates", esm_tpl)
        _debug.pipeline(
            "esm_payload",
            bundle=bundle,
            compiled=compiled,
            specifiers=len(native_data["import_map"]),
            import_map=len(import_map),
            templates=bool(esm_tpl),
        )
        return {
            "specifiers": sorted(native_data["import_map"]),
            "import_map": import_map,
            "template_url": template_url,
        }

    _loader_shim_cache: tuple[float, str] | None = None

    _is_hoot_test_specifier = staticmethod(is_hoot_test_specifier)

    @classmethod
    def _get_hoot_specifiers(cls, bundle: str, specifiers: Iterable[str]) -> list[str]:
        registry = esm_registry()
        if bundle in registry.import_map_includes:
            return []
        by_directory = bundle in registry.import_map_included_bundles
        return [
            spec
            for spec in specifiers
            if cls._is_hoot_test_specifier(spec, by_directory=by_directory)
        ]

    @classmethod
    def _prepare_loader_shim_js(cls) -> str:
        src_path = Path(file_path("web/static/src/module_loader.js"))
        mtime = src_path.stat().st_mtime
        cached = cls._loader_shim_cache
        if cached and cached[0] == mtime:
            return cached[1]
        source = src_path.read_text(encoding="utf-8")
        with _debug.perf("loader_shim_minify", source_bytes=len(source)) as span:
            minified = _rjsmin(source)
            span.set(minified_bytes=len(minified))
        cls._loader_shim_cache = (mtime, minified)
        log_event(
            _loader_log,
            logging.DEBUG,
            "shim_compiled",
            source_bytes=len(source),
            minified_bytes=len(minified),
        )
        return minified

    @classmethod
    def _prepare_loader_shim_node(cls, bundle: str) -> AssetNode:
        return (
            "script",
            {LOADER_SHIM_MARKER: bundle, "text": cls._prepare_loader_shim_js()},
        )

    @staticmethod
    def _has_esm_test_satellites(debug: str | bool | None) -> bool:
        return has_esm_test_satellites(
            debug, test_enable=bool(tools.config["test_enable"])
        )

    @tools.conditional(
        _ASSET_CACHE_ENABLED,
        tools.ormcache(
            "bundle",
            "tuple(sorted(assets_params.items()))",
            "with_test_satellites",
            "page_scope",
            "esbuild_ok",
            cache="assets",
        ),
    )
    def _get_native_module_nodes_cached(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None = None,
        with_test_satellites: bool = False,
        page_scope: tuple[str, ...] = (),
        esbuild_ok: bool = True,
    ) -> EsmNodePair:
        return self._get_native_module_nodes_uncached(
            bundle,
            debug=False,
            assets_params=assets_params,
            _raise_on_decline=True,
            with_test_satellites=with_test_satellites,
            page_scope=page_scope,
            esbuild_ok=esbuild_ok,
        )

    def _get_native_module_nodes(
        self,
        bundle: str,
        debug: str = "",
        assets_params: dict[str, Any] | None = None,
        page: bool = True,
    ) -> EsmNodePair:
        debug_assets = self._is_debug_assets(debug)
        if assets_params is None:
            assets_params = self.env["ir.asset"]._prepare_assets_params()
        satellites = self._has_esm_test_satellites(debug)
        page_scope = self._get_esm_page_scope(bundle)
        esbuild_ok = not debug_assets and self._can_compile_with_esbuild(bundle)
        _debug.logic(
            "native_module_nodes_route",
            bundle=bundle,
            debug=debug_assets,
            esbuild_ok=esbuild_ok,
            satellites=satellites,
            page_scope=len(page_scope),
        )
        if not debug_assets:
            try:
                pre, post = self._get_page_scoped_nodes_cached(
                    bundle,
                    assets_params=assets_params,
                    with_test_satellites=satellites,
                    page_scope=page_scope,
                    esbuild_ok=esbuild_ok,
                )
            except _EsmReadonlyDeclined:
                _debug.logic(
                    "native_module_nodes_fallback", bundle=bundle, reason="readonly"
                )
                pre, post = self._get_native_module_nodes_cached(
                    bundle,
                    assets_params=assets_params,
                    with_test_satellites=satellites,
                    page_scope=page_scope,
                    esbuild_ok=False,
                )
            except _EsmFallbackError:
                _debug.logic(
                    "native_module_nodes_fallback", bundle=bundle, reason="esbuild"
                )
                pre, post = self._get_native_module_nodes_uncached(
                    bundle,
                    debug=debug,
                    assets_params=assets_params,
                    with_test_satellites=satellites,
                    page_scope=page_scope,
                    esbuild_ok=False,
                )
        else:
            pre, post = self._get_native_module_nodes_uncached(
                bundle,
                debug=debug,
                assets_params=assets_params,
                with_test_satellites=satellites,
                page_scope=page_scope,
                esbuild_ok=False,
            )
        if not page:
            return pre, post
        self._record_esm_page_bundle(bundle)
        return self._dedup_request_page_scripts(bundle, pre), post

    def _get_page_scoped_nodes_cached(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        with_test_satellites: bool,
        page_scope: tuple[str, ...],
        esbuild_ok: bool,
    ) -> EsmNodePair:
        try:
            return self._get_esm_variant_nodes_cached(
                bundle,
                assets_params=assets_params,
                with_test_satellites=with_test_satellites,
                page_scope=page_scope,
                esbuild_ok=esbuild_ok,
            )
        except _EsmFallbackError:
            if not page_scope:
                raise
        log_event(
            _fallback_log,
            logging.INFO,
            "page_scope_fallback",
            bundle=bundle,
            page=",".join(page_scope),
        )
        _debug.logic("page_scope_dropped", bundle=bundle, page_scope=len(page_scope))
        return self._get_esm_variant_nodes_cached(
            bundle,
            assets_params=assets_params,
            with_test_satellites=with_test_satellites,
            page_scope=(),
            esbuild_ok=esbuild_ok,
        )

    _ESM_READONLY_DECLINES_KEY = "esm_readonly_declines"

    def _is_esm_readonly_test_cursor(self) -> bool:
        return bool(self.env.cr.readonly and _module.current_test)

    def _get_esm_readonly_declines(self, bundle: str) -> set[tuple]:
        return self.pool.ormcache_lrus["assets"].get(
            (self._ESM_READONLY_DECLINES_KEY, bundle), set()
        )

    def _add_esm_readonly_decline(
        self, bundle: str, variant: tuple, generation: int
    ) -> None:
        lru = self.pool.ormcache_lrus["assets"]
        if lru.generation != generation:
            _debug.logic("readonly_decline_stale", bundle=bundle)
            return
        key = (self._ESM_READONLY_DECLINES_KEY, bundle)
        declines = lru.get(key)
        if declines is None:
            declines = set()
            lru[key] = declines
        declines.add(variant)
        _debug.lifecycle(
            "readonly_decline_recorded", bundle=bundle, declines=len(declines)
        )

    def _remove_esm_readonly_declines(self, bundle: str) -> None:
        removed = self.pool.ormcache_lrus["assets"].pop(
            (self._ESM_READONLY_DECLINES_KEY, bundle), None
        )
        if _debug.lifecycle.enabled and removed:
            _debug.lifecycle(
                "readonly_declines_cleared", bundle=bundle, declines=len(removed)
            )

    def _get_esm_variant_nodes_cached(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        with_test_satellites: bool,
        page_scope: tuple[str, ...],
        esbuild_ok: bool,
    ) -> EsmNodePair:
        remembered = esbuild_ok and self._is_esm_readonly_test_cursor()
        variant = (
            tuple(sorted((assets_params or {}).items())),
            with_test_satellites,
            page_scope,
        )
        if remembered and variant in self._get_esm_readonly_declines(bundle):
            _debug.logic("readonly_decline_remembered", bundle=bundle)
            raise _EsmReadonlyDeclined
        generation = self.pool.ormcache_lrus["assets"].generation
        try:
            return self._get_native_module_nodes_cached(
                bundle,
                assets_params=assets_params,
                with_test_satellites=with_test_satellites,
                page_scope=page_scope,
                esbuild_ok=esbuild_ok,
            )
        except _EsmReadonlyDeclined:
            if remembered:
                self._add_esm_readonly_decline(bundle, variant, generation)
            raise

    _is_import_map_node = staticmethod(is_import_map_node)
    _is_loader_shim_node = staticmethod(is_loader_shim_node)
    _get_import_map_specs = staticmethod(import_map_specs)
    _narrow_import_map_node = staticmethod(narrow_import_map_node)

    def _get_native_module_nodes_uncached(
        self,
        bundle: str,
        debug: str = "",
        assets_params: dict[str, Any] | None = None,
        _raise_on_decline: bool = False,
        with_test_satellites: bool = False,
        page_scope: tuple[str, ...] = (),
        esbuild_ok: bool = True,
    ) -> EsmNodePair:
        debug_assets = self._is_debug_assets(debug)
        if assets_params is None:
            assets_params = self.env["ir.asset"]._prepare_assets_params()

        asset_bundle = self._get_asset_bundle(
            bundle,
            js=True,
            css=False,
            debug_assets=debug_assets,
            assets_params=assets_params,
        )
        native_data = (
            asset_bundle.get_native_module_data()
            if debug_assets
            else self._get_native_module_data_cached(
                bundle,
                assets_params=assets_params,
            )
        )

        if not native_data["import_map"]:
            log_event(
                _esm_log,
                logging.DEBUG,
                "no_native_modules",
                bundle=bundle,
            )
            _debug.logic("native_module_nodes", bundle=bundle, reason="no_modules")
            return [], []

        if not debug_assets and esbuild_ok:
            esbuild_result, child_bundles = self._compile_with_esbuild_locked(
                bundle, asset_bundle, assets_params, page_scope
            )
            _debug.pipeline(
                "esbuild_compiled",
                bundle=bundle,
                code=bool(esbuild_result.code),
                bytes=len(esbuild_result.code) if esbuild_result.code else 0,
                children=len(child_bundles) if child_bundles else 0,
                page_scope=len(page_scope),
            )
            if esbuild_result.code:
                return self._get_esm_nodes_prod(
                    bundle,
                    asset_bundle,
                    esbuild_result,
                    assets_params,
                    child_bundles,
                    raise_on_decline=_raise_on_decline,
                    with_test_satellites=with_test_satellites,
                )
            if _raise_on_decline:
                _debug.logic("native_module_nodes", bundle=bundle, reason="declined")
                raise _EsmFallbackError
        _debug.logic("native_module_nodes", bundle=bundle, branch="debug")
        return self._get_esm_nodes_debug(
            bundle,
            asset_bundle,
            native_data,
            debug_assets,
            assets_params,
            with_test_satellites=with_test_satellites,
            page_scope=page_scope,
        )

    def _get_dynamic_parent_bundles(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
    ) -> tuple[str, ...]:
        contributors = dict.fromkeys((bundle,))
        for asset in self.env["ir.asset"]._get_asset_paths(
            bundle=bundle,
            assets_params=(
                self.env["ir.asset"]._prepare_assets_params()
                if assets_params is None
                else assets_params
            ),
        ):
            contributors.setdefault(asset.bundle)
        _debug.perf.count(
            "dynamic_parent_bundles", bundle=bundle, contributors=len(contributors)
        )
        return tuple(contributors)

    def _get_dynamic_child_bundles(
        self,
        bundle: str,
        assets_params: dict[str, Any] | None,
        *,
        debug_assets: bool,
    ) -> list[AssetsBundle]:
        registry = esm_registry()
        child_names = dict.fromkeys(
            child_name
            for parent_name in self._get_dynamic_parent_bundles(bundle, assets_params)
            for child_name in registry.dynamic_children.get(parent_name, ())
        )
        _debug.pipeline(
            "dynamic_child_bundles",
            bundle=bundle,
            children=len(child_names),
            debug=debug_assets,
        )
        return [
            self._get_asset_bundle(
                child_name,
                js=True,
                css=False,
                debug_assets=debug_assets
                or child_name in registry.runtime_bundle_names,
                assets_params=assets_params,
            )
            for child_name in child_names
        ]

    def _prepare_esm_script_node(
        self,
        name: str,
        code: str,
        attrs: dict[str, str],
        *,
        raise_on_decline: bool,
        metafile: str | None = None,
        sourcemap: str | None = None,
        source_key: str | None = None,
    ) -> AssetNode:
        url = None
        # a failed statement (a serialization failure on a row another
        # connection touched) aborts the caller's transaction; the savepoint
        # keeps the inline fallback a fallback. It is released, not rolled
        # back, on a decline raised before any statement failed: rolling back
        # would drop the transaction's ORM caches, and with them the memo of
        # that decline
        savepoint = self.env.cr.savepoint()
        try:
            url = self._save_esm_attachment(
                name,
                code,
                metafile=metafile,
                sourcemap=sourcemap,
                source_key=source_key,
            )
        except Exception as exc:
            savepoint.close(rollback=self.env.cr.in_failed_transaction())
            log_event(
                _attach_log,
                logging.WARNING,
                "save_failed_inline",
                bundle=name,
                readonly=bool(self.env.cr.readonly),
                declined=raise_on_decline,
                err=type(exc).__name__,
            )
            if not isinstance(exc, ReadOnlySqlTransaction):
                _logger.warning(
                    "Could not persist the ESM bundle %s; serving it inline",
                    name,
                    exc_info=True,
                )
            if raise_on_decline:
                if isinstance(exc, ReadOnlySqlTransaction) and self.env.cr.readonly:
                    _debug.logic("esm_script_declined", bundle=name, reason="readonly")
                    raise _EsmReadonlyDeclined from None
                _debug.logic("esm_script_declined", bundle=name, reason="save_failed")
                raise _EsmFallbackError from None
        else:
            savepoint.close(rollback=False)
        _debug.logic("esm_script_node", bundle=name, inline=url is None)
        node: dict[str, str] = {"type": "module"}
        node["src" if url else "text"] = url or code
        node.update(attrs)
        return ("script", node)

    def _log_esm_render(
        self,
        bundle: str,
        branch: str,
        pre: list[AssetNode],
        post: list[AssetNode],
        import_map: dict[str, str],
        **extra: Any,
    ) -> None:
        real_urls, bridges, data_uris = self._get_import_map_url_counts(import_map)
        log_event(
            _esm_log,
            logging.DEBUG,
            "render",
            bundle=bundle,
            branch=branch,
            pre=len(pre),
            post=len(post),
            importmap=len(import_map),
            url=real_urls,
            bridges=bridges,
            data=data_uris,
            **extra,
        )

    def _get_esm_import_map_prod(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        assets_params: dict[str, Any] | None,
        child_bundles: list[AssetsBundle] | None,
        *,
        with_test_satellites: bool,
    ) -> tuple[dict[str, str], list[AssetsBundle], tuple[str, ...]]:
        import_map = self._get_external_libs_served(debug_assets=False)
        if child_bundles is None:
            child_bundles = self._get_dynamic_child_bundles(
                bundle, assets_params, debug_assets=False
            )
        dynamic_bundles, child_specifiers = self._merge_child_import_maps(
            import_map, child_bundles, map_specifiers=False
        )

        if dynamic_bundles:
            combined_modules = []
            for dyn_ab in dynamic_bundles:
                combined_modules.extend(dyn_ab.native_modules)
            bridge_map = dynamic_bundles[0]._bridges._prepare_native_to_legacy_bridge(
                set(import_map) | child_specifiers,
                modules=combined_modules,
            )
            import_map.update(bridge_map)
            _debug.pipeline(
                "prod_import_map_bridged",
                bundle=bundle,
                dynamic=len(dynamic_bundles),
                modules=len(combined_modules),
                bridges=len(bridge_map),
            )

        include_names = self._merge_include_import_maps(
            bundle,
            import_map,
            assets_params,
            debug_assets=False,
            resolve_bridges=False,
        )

        if with_test_satellites:
            self._merge_secondary_import_maps(
                bundle, import_map, assets_params, debug_assets=False
            )

        if include_names:
            self._add_import_map_parent_self_bridges(
                asset_bundle, import_map, served_by_children=child_specifiers
            )
        _debug.pipeline(
            "prod_import_map",
            bundle=bundle,
            entries=len(import_map),
            includes=len(include_names) if include_names else 0,
            satellites=with_test_satellites,
        )
        return import_map, dynamic_bundles, include_names

    @staticmethod
    def _add_import_map_parent_self_bridges(
        asset_bundle: AssetsBundle,
        import_map: dict[str, str],
        served_by_children: Collection[str] = (),
    ) -> None:
        self_bridges = {
            spec: shim
            for spec, shim in asset_bundle._bridges._prepare_parent_self_bridge().items()
            if spec not in served_by_children
        }
        import_map.update(self_bridges)
        for asset in asset_bundle.native_modules:
            header = asset.parsed_header
            if not (header and header["alias"]):
                continue
            alias = header["alias"]
            if alias in served_by_children:
                continue
            if import_map.get(alias, "").startswith("/web/assets/esm/bridges/"):
                continue
            shim = self_bridges.get(asset.module_path)
            if shim:
                import_map[alias] = shim
                _debug.logic("parent_self_bridge_aliased", alias=alias)

    def _get_esm_nodes_prod(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        esbuild_result: EsbuildResult,
        assets_params: dict[str, Any] | None,
        child_bundles: list[AssetsBundle] | None = None,
        *,
        raise_on_decline: bool = False,
        with_test_satellites: bool = False,
    ) -> EsmNodePair:
        esbuild_code = esbuild_result.code
        pre = []
        post = []
        prod_import_map, dynamic_bundles, include_names = self._get_esm_import_map_prod(
            bundle,
            asset_bundle,
            assets_params,
            child_bundles,
            with_test_satellites=with_test_satellites,
        )

        pre.append(
            (
                "script",
                {
                    "type": "importmap",
                    "data-bundle": bundle,
                    "text": json.dumps(
                        {"imports": prod_import_map},
                    ),
                },
            )
        )
        pre.append(self._prepare_loader_shim_node(bundle))
        pre.extend(
            self._get_esm_library_preload_links(
                esbuild_result.metafile, prod_import_map
            )
        )
        esm_tpl = asset_bundle.generate_esm_template_bundle(
            use_import=False,
        )
        bundle_code = self._combine_bundle_with_templates(esbuild_code, esm_tpl)
        post.append(
            self._prepare_esm_script_node(
                bundle,
                bundle_code,
                {"data-bridge": bundle},
                raise_on_decline=raise_on_decline,
                metafile=esbuild_result.metafile,
                sourcemap=esbuild_result.sourcemap,
                source_key=esbuild_result.source_key,
            )
        )
        _has_satellites = bool(
            esm_registry().import_map_includes.get(bundle),
        )
        if esm_tpl and _has_satellites:
            post.append(
                self._prepare_esm_script_node(
                    f"{bundle}.templates",
                    esm_tpl,
                    {"data-templates": bundle},
                    raise_on_decline=raise_on_decline,
                )
            )
        _debug.pipeline(
            "esm_nodes_prod",
            bundle=bundle,
            pre=len(pre),
            post=len(post),
            code_bytes=len(esbuild_code),
            templates=bool(esm_tpl),
            satellites=_has_satellites,
        )
        self._log_esm_render(
            bundle,
            "prod",
            pre,
            post,
            prod_import_map,
            dyn=len(dynamic_bundles),
            includes=len(include_names) if include_names else 0,
        )
        return pre, post

    @staticmethod
    def _get_static_external_imports(metafile: str | None) -> list[str]:
        if not metafile:
            return []
        try:
            outputs = json.loads(metafile).get("outputs", {})
        except ValueError:
            _debug.logic("static_external_imports", reason="metafile_invalid")
            return []
        specs: dict[str, None] = {}
        for output in outputs.values():
            for imp in output.get("imports", ()):
                if imp.get("external") and imp.get("kind") == "import-statement":
                    specs.setdefault(imp["path"])
        return list(specs)

    def _get_esm_library_preload_links(
        self, metafile: str | None, import_map: dict[str, str]
    ) -> list[AssetNode]:
        served = self._served_external_libs_table()
        links = [
            ("link", {"rel": "modulepreload", "href": import_map[spec]})
            for spec in self._get_static_external_imports(metafile)
            if spec in served and import_map.get(spec) == served[spec]
        ]
        _debug.perf.count("library_preload_links", links=len(links))
        return links

    def _get_esm_preload_links(
        self, bundle: str, native_data: dict[str, Any]
    ) -> list[AssetNode]:
        hoot_owned = set(self._get_hoot_specifiers(bundle, native_data["import_map"]))
        reachable_without_hoot = {
            url
            for spec, url in native_data["import_map"].items()
            if spec not in hoot_owned
        }
        links = [
            ("link", {"rel": "modulepreload", "href": url})
            for url in native_data["preload_urls"]
            if url in reachable_without_hoot
        ]
        _debug.perf.count(
            "esm_preload_links",
            bundle=bundle,
            hoot=len(hoot_owned),
            candidates=len(native_data["preload_urls"]),
            links=len(links),
        )
        return links

    def _get_esm_import_map_debug(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        native_data: dict[str, Any],
        assets_params: dict[str, Any] | None,
        *,
        debug_assets: bool,
        with_test_satellites: bool,
        page_scope: tuple[str, ...] = (),
    ) -> tuple[dict[str, str], dict[str, str]]:
        import_map = self._get_external_libs_served(debug_assets=debug_assets)
        import_map.update(native_data["import_map"])

        lazy_bundles = self._get_dynamic_child_bundles(
            bundle, assets_params, debug_assets=True
        )
        self._merge_child_import_maps(import_map, lazy_bundles)
        self._merge_include_import_maps(
            bundle,
            import_map,
            assets_params,
            debug_assets=debug_assets,
            resolve_bridges=True,
        )
        if with_test_satellites:
            self._merge_secondary_import_maps(
                bundle, import_map, assets_params, debug_assets=debug_assets
            )

        all_native_specifiers = set(native_data["import_map"])
        combined_native_modules = list(asset_bundle.native_modules)
        for lazy_ab in lazy_bundles:
            all_native_specifiers.update(m.module_path for m in lazy_ab.native_modules)
            combined_native_modules.extend(lazy_ab.native_modules)

        provided = (
            self._get_secondary_provider_specs(bundle, assets_params, page_scope)
            - all_native_specifiers
            if page_scope
            else set()
        )
        if provided:
            bridge_map, discovered = (
                asset_bundle._bridges.prepare_page_provided_bridges(
                    all_native_specifiers, provided, modules=combined_native_modules
                )
            )
            import_map.update(bridge_map)
        else:
            discovered, _ext_seen = asset_bundle._bridges._discover_bridge_specifiers(
                all_native_specifiers,
                set(self._external_libs()),
                modules=combined_native_modules,
            )
        resolved_bridges = self._add_import_map_bridge_urls(
            import_map, discovered, drop_unresolved=False, bundle=bundle
        )
        _debug.pipeline(
            "debug_import_map",
            bundle=bundle,
            entries=len(import_map),
            lazy=len(lazy_bundles),
            native=len(all_native_specifiers),
            provided=len(provided),
            discovered=len(discovered),
            resolved=len(resolved_bridges),
        )
        return import_map, resolved_bridges

    _prepare_register_native_modules_js = staticmethod(
        prepare_register_native_modules_js
    )

    def _prepare_esm_bridge_js(
        self,
        bundle: str,
        import_map: dict[str, str],
        bridge_specifiers: list[str],
    ) -> str:
        hoot_specs = self._get_hoot_specifiers(bundle, bridge_specifiers)
        hoot_spec_set = set(hoot_specs)
        non_hoot_specs = [s for s in bridge_specifiers if s not in hoot_spec_set]
        bridge_code = ""

        if non_hoot_specs:
            bridge_code = self._prepare_register_native_modules_js(
                [(spec, import_map.get(spec, spec)) for spec in non_hoot_specs],
                "__m",
            )

        start_hoot = [s for s in hoot_specs if s.endswith("/start.hoot")]
        other_tests = [s for s in hoot_specs if s not in start_hoot]
        _debug.logic(
            "esm_bridge_js",
            bundle=bundle,
            registered=len(non_hoot_specs),
            hoot=len(hoot_specs),
            start_hoot=bool(start_hoot),
        )
        if start_hoot and any(".test" in spec for spec in other_tests):
            specifier_list = ",\n".join(f"  {json.dumps(s)}" for s in other_tests)
            bridge_code += (
                f"const {{loadAndStart}} = await import("
                f"{json.dumps(start_hoot[0])});\n"
                f"loadAndStart([\n{specifier_list}\n]);\n"
            )
        return bridge_code

    @staticmethod
    def _bridge_external_specifiers(native_data: dict[str, Any]) -> set[str]:
        return bridge_external_specifiers(
            native_data["import_map"], external_lib_aliases()
        )

    def _get_esm_nodes_debug(
        self,
        bundle: str,
        asset_bundle: AssetsBundle,
        native_data: dict[str, Any],
        debug_assets: bool,
        assets_params: dict[str, Any] | None,
        *,
        with_test_satellites: bool = False,
        page_scope: tuple[str, ...] = (),
    ) -> EsmNodePair:
        pre_nodes = []
        post_nodes = []
        import_map, resolved_bridges = self._get_esm_import_map_debug(
            bundle,
            asset_bundle,
            native_data,
            assets_params,
            debug_assets=debug_assets,
            with_test_satellites=with_test_satellites,
            page_scope=page_scope,
        )

        pre_nodes.append(
            (
                "script",
                {
                    "type": "importmap",
                    "data-bundle": bundle,
                    "text": json.dumps({"imports": import_map}, indent=2),
                },
            )
        )

        if not debug_assets:
            pre_nodes.extend(self._get_esm_preload_links(bundle, native_data))

        bridge_specifiers = sorted(
            set(native_data["import_map"])
            | self._bridge_external_specifiers(native_data)
        )
        if bridge_specifiers:
            pre_nodes.append(self._prepare_loader_shim_node(bundle))
            bridge_code = self._prepare_esm_bridge_js(
                bundle, import_map, bridge_specifiers
            )
            if bridge_code.strip():
                post_nodes.append(
                    inline_module_node("data-bridge", bundle, bridge_code)
                )

        esm_tpl = asset_bundle.generate_esm_template_bundle(use_import=True)
        if esm_tpl:
            post_nodes.append(inline_module_node("data-templates", bundle, esm_tpl))

        _debug.pipeline(
            "esm_nodes_debug",
            bundle=bundle,
            pre=len(pre_nodes),
            post=len(post_nodes),
            bridges=len(bridge_specifiers),
            templates=bool(esm_tpl),
        )
        self._log_esm_render(
            bundle,
            "debug",
            pre_nodes,
            post_nodes,
            import_map,
            bridge_shims=len(resolved_bridges),
        )
        return pre_nodes, post_nodes

    def _save_esm_attachment(
        self,
        bundle: str,
        content: str,
        metafile: str | None = None,
        sourcemap: str | None = None,
        source_key: str | None = None,
    ) -> str:
        content_bytes = content.encode("utf-8")
        content_hash = cache_hash(content_bytes)[:16]
        url = f"/web/assets/esm/{content_hash}/{bundle}.esm.js"
        rows: list[dict] = []
        touch_ids: list[int] = []

        code_is_new = self._plan_esm_row(
            rows, touch_ids, url, f"{bundle}.esm.js", "text/javascript", content_bytes
        )
        sidecars = esm_index.sidecar_urls(url)
        json_mimetype = mimetype_for("json")
        sidecar_saved = []
        for name, text in (("metafile", metafile), ("sourcemap", sourcemap)):
            if text and self._plan_esm_row(
                rows,
                touch_ids,
                sidecars[name],
                sidecars[name].rsplit("/", 1)[-1],
                json_mimetype,
                text.encode("utf-8"),
            ):
                sidecar_saved.append(name)
        if source_key and (
            self._read_generated_asset(esm_index.index_url(bundle, source_key)) is None
        ):
            rows.append(
                esm_index.index_row(
                    bundle, source_key, url, bool(metafile), bool(sourcemap)
                )
            )

        self._save_esm_attachment_rows(rows, touch_ids=touch_ids, bundle=bundle)
        self._remove_esm_readonly_declines(bundle)
        _debug.lifecycle(
            "esm_attachment_saved",
            bundle=bundle,
            new=code_is_new,
            bytes=len(content_bytes),
            rows=len(rows),
            touched=len(touch_ids),
            sidecars=len(sidecar_saved),
            indexed=bool(source_key),
        )
        if code_is_new:
            self._log_esm_artifacts_superseded(bundle, url)
        log_event(
            _attach_log,
            logging.INFO if code_is_new else logging.DEBUG,
            "save" if code_is_new else "reuse",
            bundle=bundle,
            url=url,
            bytes=len(content_bytes),
            sidecars=",".join(sidecar_saved) or None,
            indexed=bool(source_key),
        )
        return url

    def _plan_esm_row(
        self,
        rows: list[dict],
        touch_ids: list[int],
        url: str,
        name: str,
        mimetype: str,
        content: bytes,
    ) -> bool:
        IrAttachment = self.env["ir.attachment"]
        existing = IrAttachment.sudo().search(
            IrAttachment._get_domain_generated_assets(url), limit=1
        )
        if existing:
            touch_ids.extend(existing.ids)
            _debug.logic("esm_row_planned", name=name, action="touch")
            return False
        rows.append(
            IrAttachment._prepare_generated_asset_vals(
                name=name, mimetype=mimetype, raw=content, url=url
            )
        )
        _debug.logic("esm_row_planned", name=name, action="insert", bytes=len(content))
        return True

    def _log_esm_artifacts_superseded(self, bundle: str, keep_url: str) -> None:
        if not _attach_log.isEnabledFor(logging.INFO):
            return
        stale_count = (
            self.env["ir.attachment"]
            .sudo()
            .search_count(
                [
                    "|",
                    "|",
                    ("url", "=like", f"/web/assets/%/{bundle}.esm.js"),
                    ("url", "=like", f"/web/assets/%/{bundle}.esm.js.map"),
                    ("url", "=like", f"/web/assets/%/{bundle}.meta.json"),
                    ("url", "!=", keep_url),
                    ("public", "=", True),
                ]
            )
        )
        if stale_count:
            log_event(
                _attach_log,
                logging.INFO,
                "stale_deferred",
                bundle=bundle,
                count=stale_count,
            )

    @staticmethod
    def _lock_esm_publication(cr, lock_timeout: str | None = None) -> None:
        # These dedicated write transactions must see the preceding writer's
        # commit after waiting. REPEATABLE READ would retain the snapshot from
        # the lock statement and let both writers insert the same URLs. The
        # isolation level is the transaction's first statement or PostgreSQL
        # refuses it ("must be called before any query"), so the lock
        # timeout comes after it
        cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        if lock_timeout:
            cr.execute("SELECT set_config('lock_timeout', %s, true)", (lock_timeout,))
        started = time.monotonic()
        with _debug.perf("esm_publication_lock", cr=cr, timeout=lock_timeout):
            cr.execute("SELECT pg_advisory_xact_lock(hashtext('esm:publication'))")
        log_event(
            _attach_log,
            logging.DEBUG,
            "publication_acquired",
            wait_s=time.monotonic() - started,
        )

    @staticmethod
    def _drop_rows_already_present(cr, vals_list: list[dict]) -> list[dict]:
        urls = [vals["url"] for vals in vals_list if vals.get("url")]
        if not urls:
            return vals_list
        cr.execute("SELECT url FROM ir_attachment WHERE url = ANY(%s)", (urls,))
        present = {row[0] for row in cr.fetchall()}
        _debug.perf.count("esm_rows_present", checked=len(urls), present=len(present))
        return [vals for vals in vals_list if vals.get("url") not in present]

    @staticmethod
    def _touch_esm_attachment_rows(cr, touch_ids: Sequence[int]) -> None:
        cr.execute(
            "UPDATE ir_attachment SET write_date = now() at time zone 'UTC'"
            " WHERE id = ANY(%s)",
            (list(touch_ids),),
        )

    def _save_esm_attachment_rows_autonomously(self, vals_list: list[dict]) -> None:
        from odoo.db import db_connect

        with db_connect(self.env.cr.dbname).cursor() as own_cr:
            try:
                self._lock_esm_publication(own_cr, _AUTONOMOUS_LOCK_TIMEOUT)
                fresh = self._drop_rows_already_present(own_cr, vals_list)
                if fresh:
                    api.Environment(own_cr, SUPERUSER_ID, {})["ir.attachment"].create(
                        fresh
                    )
                own_cr.commit()
                _debug.lifecycle(
                    "esm_rows_saved",
                    by="autonomous",
                    rows=len(vals_list),
                    fresh=len(fresh),
                )
            except LockNotAvailable:
                own_cr.rollback()
                _debug.lifecycle(
                    "esm_rows_not_persisted",
                    reason="lock_timeout",
                    rows=len(vals_list),
                )

    def _save_esm_attachment_rows_in_test(
        self, vals_list: list[dict], touch_ids: Sequence[int]
    ) -> None:
        # the test transaction is rolled back and a read-only test cursor
        # cannot write at all, so what a test compiled was gone before the
        # next class ran. The rows are content-addressed and idempotent:
        # they go through their own connection, which outlives the test,
        # the way a request escalates to a read-write cursor. The test
        # transaction is REPEATABLE READ and cannot see that commit, so a
        # writable test cursor also keeps its own copy for the test to read
        if vals_list:
            self._save_esm_attachment_rows_autonomously(vals_list)
        if self.env.cr.readonly:
            if vals_list:
                # persisted for the next process, but not for this
                # transaction, which cannot see the commit: the caller's
                # read-only fallback stands, as it did before
                _debug.logic(
                    "esm_rows_declined",
                    by="test",
                    reason="readonly",
                    rows=len(vals_list),
                )
                raise ReadOnlySqlTransaction(
                    "cannot persist ESM attachments on a read-only test cursor"
                )
            return
        if vals_list:
            self.env["ir.attachment"].with_user(SUPERUSER_ID).create(vals_list)
        if touch_ids:
            # the touch stays on the test cursor: the same row updated from
            # another connection is a serialization failure for a
            # REPEATABLE READ test transaction that touches it too
            self._touch_esm_attachment_rows(self.env.cr, touch_ids)
        _debug.lifecycle(
            "esm_rows_saved", by="test", rows=len(vals_list), touched=len(touch_ids)
        )

    def _save_esm_attachment_rows(
        self,
        vals_list: list[dict],
        touch_ids: Sequence[int] = (),
        bundle: str = "",
    ) -> None:
        # Compiled public assets are shared across companies. In particular,
        # autonomous persistence must not take a foreign-key lock on a company
        # held by the transaction that is waiting for this compilation.
        vals_list = [dict(vals, company_id=False) for vals in vals_list]
        if _module.current_test:
            self._save_esm_attachment_rows_in_test(vals_list, touch_ids)
            return
        if not request:
            if vals_list:
                if self.env.cr.readonly:
                    _debug.logic(
                        "esm_rows_declined",
                        by="own_cursor",
                        reason="readonly",
                        rows=len(vals_list),
                    )
                    raise ReadOnlySqlTransaction(
                        "cannot persist ESM attachments on a read-only cursor"
                    )
                self.env["ir.attachment"].with_user(SUPERUSER_ID).create(vals_list)
            if touch_ids and not self.env.cr.readonly:
                self._touch_esm_attachment_rows(self.env.cr, touch_ids)
                self.env["ir.attachment"].browse(list(touch_ids)).invalidate_recordset(
                    ["write_date"],
                )
            _debug.lifecycle(
                "esm_rows_saved",
                by="own_cursor",
                rows=len(vals_list),
                touched=len(touch_ids),
            )
            return
        try:
            with self.env.registry.cursor(readonly=False) as rw_cr:
                if vals_list:
                    self._lock_esm_publication(rw_cr)
                    fresh = self._drop_rows_already_present(rw_cr, vals_list)
                    if fresh:
                        rw_env = api.Environment(rw_cr, SUPERUSER_ID, {})
                        rw_env["ir.attachment"].create(fresh)
                    _debug.pipeline(
                        "esm_rows_escalated",
                        bundle=bundle,
                        rows=len(vals_list),
                        fresh=len(fresh),
                    )
                if touch_ids:
                    self._touch_esm_attachment_rows(rw_cr, touch_ids)
            _debug.lifecycle(
                "esm_rows_saved",
                by="rw_cursor",
                rows=len(vals_list),
                touched=len(touch_ids),
            )
        except Exception:
            if not vals_list:
                log_event(
                    _attach_log,
                    logging.DEBUG,
                    "touch_failed",
                    bundle=bundle,
                    ids=len(touch_ids),
                )
                return
            _logger.warning(
                "ESM attachment escalation to a read-write cursor failed; "
                "creating on the request cursor",
                exc_info=True,
            )
            if self.env.cr.readonly:
                _debug.logic(
                    "esm_rows_declined",
                    by="request_cursor",
                    reason="readonly",
                    rows=len(vals_list),
                )
                raise ReadOnlySqlTransaction(
                    "no writable cursor reachable for ESM attachments"
                ) from None
            _debug.lifecycle("esm_rows_saved", by="request_cursor", rows=len(vals_list))
            self.env["ir.attachment"].with_user(SUPERUSER_ID).create(vals_list)

    def _get_asset_link_urls(self, bundle: str, debug: str = "") -> list[str]:
        asset_nodes = self._get_asset_nodes(bundle, js=False, debug=debug)
        return [node[1]["href"] for node in asset_nodes if node[0] == "link"]

    def _pregenerate_assets_bundles(self) -> list[str]:
        _logger.runbot("Pregenerating assets bundles")

        js_bundles, css_bundles = self._get_bundles_to_pregenerate()
        self._log_pregeneration_coverage(js_bundles)
        _debug.pipeline("pregenerate", js=len(js_bundles), css=len(css_bundles))

        start = time.time()
        links = list(self._get_external_libs_served(debug_assets=False).values())
        for bundle in sorted(js_bundles):
            with _debug.perf(
                "pregenerate_js_bundle", cr=self.env.cr, bundle=bundle
            ) as span:
                asset_bundle = self._get_asset_bundle(bundle, css=False, js=True)
                if asset_bundle.has_js_content:
                    links.append(asset_bundle.js().url)
                if asset_bundle.native_modules:
                    links.extend(
                        url
                        for url in self._get_asset_urls(bundle, css=False, js=True)
                        if url.startswith("/web/assets/esm/") and url not in links
                    )
                    self._pregenerate_secondary_page_scopes(bundle)
                span.set(
                    js=asset_bundle.has_js_content,
                    native=len(asset_bundle.native_modules),
                )
        installed = self.env["ir.asset"]._get_addons_installed()
        assets_params = self.env["ir.asset"]._prepare_assets_params()
        satellites = self._has_esm_test_satellites("")
        registry = esm_registry()
        for parent in sorted(registry.dynamic_children):
            if registry.bundle_addon(parent) not in installed:
                _debug.logic(
                    "pregenerate_group_skipped", parent=parent, reason="not_installed"
                )
                continue
            urls = self._get_runtime_group_urls_cached(
                (parent,), assets_params, satellites
            )
            _debug.pipeline("pregenerate_group", parent=parent, urls=len(urls))
            links.extend(url for url in sorted(urls.values()) if url not in links)
        _logger.info("JS Assets bundles generated in %s seconds", time.time() - start)
        start = time.time()
        for bundle in sorted(css_bundles):
            with _debug.perf(
                "pregenerate_css_bundle", cr=self.env.cr, bundle=bundle
            ) as span:
                asset_bundle = self._get_asset_bundle(bundle, css=True, js=False)
                if asset_bundle.has_css_content:
                    links.append(asset_bundle.css().url)
                span.set(css=asset_bundle.has_css_content)
        _logger.info("CSS Assets bundles generated in %s seconds", time.time() - start)
        _debug.pipeline("pregenerate_done", links=len(links))
        return links

    def _pregenerate_secondary_page_scopes(self, bundle: str) -> None:
        registry = esm_registry()
        parents = registry.secondary_parents.get(bundle)
        if not parents or not self._can_compile_with_esbuild(bundle):
            _debug.logic(
                "pregenerate_page_scopes_skipped",
                bundle=bundle,
                reason="no_parents" if not parents else "no_esbuild",
            )
            return
        installed = self.env["ir.asset"]._get_addons_installed()
        assets_params = self.env["ir.asset"]._prepare_assets_params()
        satellites = self._has_esm_test_satellites("")
        _debug.pipeline("pregenerate_page_scopes", bundle=bundle, parents=len(parents))
        for parent in parents:
            if registry.bundle_addon(parent) not in installed:
                continue
            try:
                self._get_native_module_nodes_cached(
                    bundle,
                    assets_params=assets_params,
                    with_test_satellites=satellites,
                    page_scope=(parent,),
                )
            except _EsmFallbackError:
                log_event(
                    _pregen_log,
                    logging.INFO,
                    "page_scope_declined",
                    bundle=bundle,
                    page=parent,
                )
                _debug.logic(
                    "pregenerate_page_scope_declined", bundle=bundle, page=parent
                )

    def _log_pregeneration_coverage(self, js_bundles: set[str]) -> None:
        if not _pregen_log.isEnabledFor(logging.DEBUG):
            return
        registry = esm_registry()
        dynamic = {
            child
            for children in registry.dynamic_children.values()
            for child in children
        }
        installed = self.env["ir.asset"]._get_addons_installed()
        uncovered = dynamic - js_bundles
        uncovered_here = {b for b in uncovered if b.split(".", 1)[0] in installed}
        log_event(
            _pregen_log,
            logging.DEBUG,
            "coverage",
            discovered=len(js_bundles),
            dynamic_declared=len(dynamic),
            uncovered_declared=len(uncovered),
            uncovered_installed=len(uncovered_here),
            bundles=",".join(sorted(uncovered_here)) or "none",
        )

    def _get_bundles_to_pregenerate(self) -> tuple[set[str], set[str]]:

        views = self.env["ir.ui.view"].search(
            [("type", "=", "qweb"), ("arch_db", "like", "t-call-assets")]
        )
        js_bundles = set()
        css_bundles = set()
        for view in views:
            for call_asset in etree.fromstring(view.arch_db).xpath(
                "//*[@t-call-assets]"
            ):
                asset = call_asset.get("t-call-assets")
                js = str2bool(call_asset.get("t-js", "True"))
                css = str2bool(call_asset.get("t-css", "True"))
                if js:
                    js_bundles.add(asset)
                if css:
                    css_bundles.add(asset)
        _debug.pipeline(
            "bundles_to_pregenerate",
            views=len(views),
            js=len(js_bundles),
            css=len(css_bundles),
        )
        return (js_bundles, css_bundles)

    def _dedup_request_page_scripts(
        self,
        bundle: str,
        pre_nodes: list[AssetNode],
    ) -> list[AssetNode]:
        if not request:
            return pre_nodes
        first = not getattr(request, "_esm_import_map_rendered", False)
        if first:
            if not any(self._is_import_map_node(node) for node in pre_nodes):
                return pre_nodes
            request._esm_import_map_rendered = True
            request._esm_import_map_specs = self._get_import_map_specs(pre_nodes)
            _debug.lifecycle(
                "page_import_map_rendered",
                bundle=bundle,
                specs=len(request._esm_import_map_specs),
            )
            return pre_nodes
        rendered = getattr(request, "_esm_import_map_specs", frozenset())
        nodes, added = self._narrow_import_map_nodes(pre_nodes, rendered)
        _debug.logic(
            "page_import_map_narrowed",
            bundle=bundle,
            rendered=len(rendered),
            added=len(added) if added else 0,
        )
        if added:
            request._esm_import_map_specs = rendered | added
        self._log_narrowed_import_map(bundle, added)
        return nodes

    def _get_esm_page_scope(self, bundle: str) -> tuple[str, ...]:
        registry = esm_registry()
        if not request or bundle not in registry.secondary_bundle_names:
            return ()
        rendered = set(getattr(request, "_esm_page_bundles", ()))
        return tuple(
            parent
            for parent in registry.secondary_parents.get(bundle, ())
            if parent in rendered
        )

    @staticmethod
    def _record_esm_page_bundle(bundle: str) -> None:
        if not request:
            return
        rendered = tuple(getattr(request, "_esm_page_bundles", ()))
        if bundle not in rendered:
            request._esm_page_bundles = (*rendered, bundle)
            _debug.lifecycle(
                "page_bundle_recorded", bundle=bundle, page=len(rendered) + 1
            )
