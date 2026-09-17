import functools
import hashlib
import logging
from collections.abc import Callable, Collection, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from odoo.api import Environment
from odoo.libs.asset_log import log_event
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import SourceMapGenerator
from odoo.tools.assets.constants import (
    SCRIPT_EXTENSIONS,
    STYLE_EXTENSIONS,
    TEMPLATE_EXTENSIONS,
)
from odoo.tools.assets.esbuild import EsbuildCompiler, EsbuildResult
from odoo.tools.assets.esm_bridges import BridgeShimManager
from odoo.tools.assets.esm_graph import _cached_module_classification, is_odoo_module
from odoo.tools.assets.esm_registry import (
    esm_registry,
    external_libs,
    invalidate_esm_registry,
)
from odoo.tools.misc import file_path

if TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment
from .assets import (
    JavascriptAsset,
    SassStylesheetAsset,
    ScssStylesheetAsset,
    StylesheetAsset,
    XMLAsset,
)
from .common import (
    BundleFileSpec,
    NativeModuleData,
    XMLBlock,
    _bundle_log,
    _pipeline_fingerprint,
    _sourcemap_source_root,
)
from .css_pipeline import CssPipeline
from .js_pipeline import JsPipeline
from .store import AssetAttachmentStore
from .xml_pipeline import XmlTemplatePipeline

_debug = DebugLog(__name__)


@functools.cache
def _check_external_libs_once() -> None:
    try:
        AssetsBundle._check_external_libs(external_libs())
    except ValueError as exc:
        if JsPipeline._is_asset_error_fatal():
            raise
        log_event(
            _bundle_log,
            logging.ERROR,
            "external_libs_invalid",
            error=str(exc).replace("\n", " ")[:400],
        )
        _debug.logic("external_libs_invalid_tolerated", error=type(exc).__name__)


class AssetsBundle:
    _STYLESHEET_TYPES = MappingProxyType(
        {
            "css": StylesheetAsset,
            "scss": ScssStylesheetAsset,
            "sass": SassStylesheetAsset,
        }
    )
    _SCRIPT_TYPES = MappingProxyType({"js": JavascriptAsset})
    _TEMPLATE_TYPES = MappingProxyType({"xml": XMLAsset})

    _BUNDLE_FILE_EXTENSIONS = frozenset(
        _STYLESHEET_TYPES | _SCRIPT_TYPES | _TEMPLATE_TYPES
    )

    @classmethod
    def _check_external_libs(cls, import_map: Mapping[str, str]) -> None:
        missing_alias = [
            spec for spec in import_map if not EsbuildCompiler.resolves_specifier(spec)
        ]
        if missing_alias:
            _debug.logic("external_libs_rejected", reason="alias", specs=missing_alias)
            raise ValueError(
                f"esm.external_libs declares {sorted(missing_alias)} "
                f"but esbuild has no resolution for them (no per-lib alias, "
                f"no pattern-level external coverage). Production builds "
                f"will fail to resolve these specifiers.",
            )
        missing_files = []
        for spec, url in import_map.items():
            if not cls._is_addon_path_present(url.lstrip("/")):
                missing_files.append(f"{spec} -> {url}")
        if missing_files:
            _debug.logic("external_libs_rejected", reason="file", specs=missing_files)
            raise ValueError(
                f"esm.external_libs URLs point at files that do not exist "
                f"on disk: {missing_files}. Browsers would 404 on the "
                f"import-map fetch.",
            )

    @staticmethod
    def _url_extension(url: str) -> str:
        return url.partition("#")[0].partition("?")[0].rpartition(".")[2].lower()

    @staticmethod
    def _is_addon_path_present(rel: str) -> bool:
        try:
            file_path(rel)
        except ValueError, FileNotFoundError:
            return False
        return True

    def _get_external_assets_matching(
        self, external_assets: Sequence[str], css: bool, js: bool
    ) -> list[str]:
        kept = []
        for url in external_assets:
            ext = self._url_extension(url)
            if (css and ext in STYLE_EXTENSIONS) or (js and ext in SCRIPT_EXTENSIONS):
                kept.append(url)
            elif ext not in STYLE_EXTENSIONS and ext not in SCRIPT_EXTENSIONS:
                log_event(
                    _bundle_log,
                    logging.WARNING,
                    "external_asset_skipped",
                    bundle=self.name,
                    url=url,
                )
                _debug.logic("external_asset_skipped", bundle=self.name, ext=ext)
        _debug.perf.count(
            "external_assets_matched",
            bundle=self.name,
            given=len(external_assets),
            kept=len(kept),
        )
        return kept

    def _collect_files(self, files: list[BundleFileSpec], css: bool, js: bool) -> None:
        for spec in files:
            extension = self._url_extension(spec["url"])
            params = {
                "url": spec["url"],
                "filename": spec["filename"],
                "inline": spec["content"],
                "last_modified": (
                    None if self.is_debug_assets else spec.get("last_modified")
                ),
            }
            if css and (stylesheet_type := self._STYLESHEET_TYPES.get(extension)):
                self.stylesheets.append(
                    stylesheet_type(
                        self,
                        **params,
                        rtl=self.rtl,
                        autoprefix=self.autoprefix,
                        split_id=f"{len(self.stylesheets):04x}",
                    )
                )
            if js and (script_type := self._SCRIPT_TYPES.get(extension)):
                asset = script_type(self, **params)
                if self._is_esm_bundle and self._is_module_js(asset):
                    self.native_modules.append(asset)
                else:
                    self.javascripts.append(asset)
            if js and (template_type := self._TEMPLATE_TYPES.get(extension)):
                self.templates.append(template_type(self, **params))
            if extension not in self._BUNDLE_FILE_EXTENSIONS:
                log_event(
                    _bundle_log,
                    logging.WARNING,
                    "bundle_file_skipped",
                    bundle=self.name,
                    url=spec["url"],
                )
                _debug.logic(
                    "bundle_file_skipped", bundle=self.name, extension=extension
                )
        _debug.pipeline(
            "files_collected",
            bundle=self.name,
            files=len(files),
            stylesheets=len(self.stylesheets),
            javascripts=len(self.javascripts),
            native_modules=len(self.native_modules),
            templates=len(self.templates),
        )

    def __init__(
        self,
        name: str,
        files: list[BundleFileSpec],
        external_assets: Sequence[str] = (),
        *,
        env: Environment,
        css: bool = True,
        js: bool = True,
        debug_assets: bool = False,
        rtl: bool = False,
        assets_params: dict[str, Any] | None = None,
        autoprefix: bool = False,
    ) -> None:
        _check_external_libs_once()
        self.name = name
        self.env = env
        self.javascripts = []
        self.native_modules = []
        self._is_esm_bundle = name in esm_registry().bundles
        self.templates = []
        self.stylesheets = []
        self.css_errors = []
        self.files = files
        self.rtl = rtl
        self.assets_params = assets_params or {}
        self.autoprefix = autoprefix
        self._checksum_cache = {}
        self._native_module_data_cache: dict[bool, NativeModuleData] = {}
        self.is_debug_assets = debug_assets
        self.external_assets = self._get_external_assets_matching(
            external_assets, css, js
        )
        self._collect_files(files, css, js)

        self._version_assets = {
            "css": tuple(self.stylesheets),
            "js": tuple(self.javascripts + self.templates + self.native_modules),
        }

        _debug.lifecycle(
            "bundle_init",
            bundle=name,
            esm=self._is_esm_bundle,
            debug=debug_assets,
            rtl=rtl,
            css=css,
            js=js,
            external=len(self.external_assets),
        )
        log_event(
            _bundle_log,
            logging.DEBUG,
            "init",
            bundle=name,
            files=len(files),
            esm=self._is_esm_bundle,
            debug=debug_assets,
            native=len(self.native_modules),
            legacy_js=len(self.javascripts),
            templates=len(self.templates),
            css=len(self.stylesheets),
            external=len(self.external_assets),
        )

    @property
    def _has_legacy_templates(self) -> bool:
        return bool(self.templates and not self._is_esm_bundle)

    @property
    def has_js_content(self) -> bool:
        return bool(self.javascripts or self._has_legacy_templates)

    @property
    def has_css_content(self) -> bool:
        return bool(self.stylesheets)

    def _no_attachment(self) -> IrAttachment:
        return self.env["ir.attachment"].sudo().browse()

    def get_links(self) -> list[str]:
        response = []

        if self.has_css_content:
            response.append(self.get_link("css"))

        if self.has_js_content:
            response.append(self.get_link("js"))

        _debug.pipeline(
            "links",
            bundle=self.name,
            external=len(self.external_assets),
            links=len(response),
        )
        return self.external_assets + response

    def get_native_module_data(self, with_bridges: bool = True) -> NativeModuleData:
        if with_bridges not in self._native_module_data_cache:
            _debug.perf.count(
                "native_module_data_miss", bundle=self.name, bridges=with_bridges
            )
            self._native_module_data_cache[with_bridges] = self._native_module_data(
                with_bridges
            )
        return self._native_module_data_cache[with_bridges]

    def _native_module_data(self, with_bridges: bool) -> NativeModuleData:
        if not self.native_modules:
            log_event(
                _bundle_log,
                logging.DEBUG,
                "native_module_data_empty",
                bundle=self.name,
            )
            return {
                "import_map": {},
                "preload_urls": [],
                "bridge_import_map": {},
            }

        import_map = {}
        preload_urls = []

        def _map(spec: str, url: str, kind: str) -> None:
            prior = import_map.get(spec)
            if prior is not None and prior != url:
                log_event(
                    _bundle_log,
                    logging.WARNING,
                    "import_map_spec_collision",
                    bundle=self.name,
                    spec=spec,
                    kind=kind,
                    previous=prior,
                    replaced_with=url,
                )
                _debug.logic(
                    "import_map_spec_collision", bundle=self.name, spec=spec, kind=kind
                )
            import_map[spec] = url

        for asset in self.native_modules:
            spec = asset.module_path
            _map(spec, asset.url, "module_path")
            preload_urls.append(asset.url)
            if asset.url.endswith("/index.js"):
                _map(spec + "/index", asset.url, "index_long_form")
            header = asset.parsed_header
            if header and header["alias"]:
                _map(header["alias"], asset.url, "alias")

        bridge_import_map = (
            self._bridges._prepare_native_to_legacy_bridge(set(import_map))
            if with_bridges
            else {}
        )
        _debug.pipeline(
            "native_module_data",
            bundle=self.name,
            modules=len(self.native_modules),
            specs=len(import_map),
            preload=len(preload_urls),
            bridges=len(bridge_import_map),
        )
        log_event(
            _bundle_log,
            logging.DEBUG,
            "native_module_data",
            bundle=self.name,
            specs=len(import_map),
            preload=len(preload_urls),
            bridges=len(bridge_import_map),
        )

        return {
            "import_map": import_map,
            "preload_urls": preload_urls,
            "bridge_import_map": bridge_import_map,
        }

    @classmethod
    def invalidate_addon_scan_cache(cls) -> None:
        EsbuildCompiler.invalidate_addon_scan_cache()
        invalidate_esm_registry()
        _check_external_libs_once.cache_clear()
        _debug.lifecycle("addon_scan_cache_invalidated")

    @classmethod
    def _get_esbuild_addon_flags(cls, odoo_root: Path) -> tuple[list, list]:
        return EsbuildCompiler._get_esbuild_addon_flags(odoo_root)

    def _prepare_esbuild_compiler(
        self,
        exported_specs: Collection[str] | None = None,
        registered_reach: Mapping[str, str] | None = None,
        excluded_specs: Collection[str] = (),
    ) -> EsbuildCompiler:
        registry = esm_registry()
        native_modules = self.native_modules
        if excluded_specs:
            native_modules = [
                asset
                for asset in native_modules
                if asset.module_path not in excluded_specs
            ]
        _debug.logic(
            "esbuild_compiler_prepared",
            bundle=self.name,
            modules=len(native_modules),
            legacy=len(self.javascripts),
            included=self.name in registry.import_map_included_bundles,
            standalone=self.name in registry.standalone_bundles,
        )
        return EsbuildCompiler(
            self.name,
            native_modules,
            self.javascripts,
            import_map_included=self.name in registry.import_map_included_bundles,
            skip_legacy_test_imports=self.name in registry.import_map_includes,
            standalone=self.name in registry.standalone_bundles,
            addon_flags_provider=self._get_esbuild_addon_flags,
            exported_specs=exported_specs,
            registered_reach=registered_reach,
        )

    def esbuild_native_bundle(
        self,
        timeout_s: int | None = None,
        target: str | None = None,
        source_maps: str | None = None,
        dynamic_child_specs: frozenset[str] | None = None,
        secondary_parent_stubs: dict[str, str] | None = None,
        exported_specs: Collection[str] | None = None,
        registered_reach: Mapping[str, str] | None = None,
        excluded_specs: Collection[str] = (),
    ) -> EsbuildResult:
        with _debug.perf(
            "esbuild_native_bundle",
            bundle=self.name,
            modules=len(self.native_modules),
            dynamic_children=len(dynamic_child_specs or ()),
            stubs=len(secondary_parent_stubs or ()),
            excluded=len(excluded_specs),
            exported=len(exported_specs or ()),
        ) as span:
            result = self._prepare_esbuild_compiler(
                exported_specs, registered_reach, excluded_specs
            ).compile(
                timeout_s=timeout_s,
                target=target,
                source_maps=source_maps,
                dynamic_child_specs=dynamic_child_specs,
                secondary_parent_stubs=secondary_parent_stubs,
            )
            span.set(compiled=bool(result.code), bytes=len(result.code or ""))
        return result

    @functools.cached_property
    def _bridges(self) -> BridgeShimManager:
        return BridgeShimManager(self.env, self.name, self.native_modules)

    def _extension(self, asset_type: str) -> str:
        return asset_type if self.is_debug_assets else f"min.{asset_type}"

    def get_link(self, asset_type: str) -> str:
        unique = self.get_version(asset_type) if not self.is_debug_assets else "debug"
        return self.get_asset_url(unique=unique, extension=self._extension(asset_type))

    def get_version(self, asset_type: str) -> str:
        return self.get_checksum(asset_type)[0:7]

    def get_checksum(self, asset_type: str) -> str:
        if asset_type not in self._checksum_cache:
            if asset_type not in self._version_assets:
                _debug.logic(
                    "checksum_rejected", bundle=self.name, asset_type=asset_type
                )
                raise ValueError(f"Asset type {asset_type} not known")
            h = hashlib.sha256()
            h.update(_pipeline_fingerprint().encode())
            h.update(b"\x00")
            for asset in self._version_assets[asset_type]:
                h.update(asset.unique_descriptor.encode())
                h.update(b"\x00")
            self._checksum_cache[asset_type] = h.hexdigest()
            _debug.perf.count(
                "checksum_computed",
                bundle=self.name,
                asset_type=asset_type,
                assets=len(self._version_assets[asset_type]),
            )
        return self._checksum_cache[asset_type]

    @functools.cached_property
    def _store(self) -> AssetAttachmentStore:
        return AssetAttachmentStore(
            self.env,
            self.name,
            assets_params=self.assets_params,
            rtl=self.rtl,
            autoprefix=self.autoprefix,
            version_provider=self.get_version,
        )

    def get_asset_url(self, unique: str, extension: str) -> str:
        return self._store.get_asset_url(unique, extension)

    def get_attachments(
        self, extension: str, ignore_version: bool = False
    ) -> IrAttachment:
        return self._store.get_attachments(extension, ignore_version)

    def save_attachment(self, extension: str, content: str) -> IrAttachment:
        return self._store.save_attachment(extension, content)

    def _is_module_js(self, asset: JavascriptAsset) -> bool:
        if asset._filename:
            return _cached_module_classification(
                asset.url or "",
                asset._filename,
                asset.last_modified,
            )
        _debug.logic("module_js_classified_inline", bundle=self.name, url=asset.url)
        return asset.is_native or is_odoo_module(asset.url or "", asset.raw_content)

    @functools.cached_property
    def _js(self) -> JsPipeline:
        return JsPipeline(self)

    @functools.cached_property
    def _xml(self) -> XmlTemplatePipeline:
        return XmlTemplatePipeline(self)

    def _stored_or_built(
        self, asset_type: str, build: Callable[[str], IrAttachment]
    ) -> IrAttachment:
        extension = self._extension(asset_type)
        stored = self.get_attachments(extension)
        _debug.logic(
            f"{asset_type}_attachment",
            bundle=self.name,
            minified=not self.is_debug_assets,
            hit=bool(stored),
        )
        return stored[0] if stored else build(extension)

    def js(self) -> IrAttachment:
        if not self.has_js_content:
            _debug.logic("js_attachment", bundle=self.name, reason="no_content")
            return self._no_attachment()
        return self._stored_or_built("js", self._build_js)

    def _build_js(self, extension: str) -> IrAttachment:
        with _debug.perf(
            "js_build",
            cr=self.env.cr,
            bundle=self.name,
            minified=not self.is_debug_assets,
            assets=len(self.javascripts),
        ):
            template_bundle = (
                self._xml.legacy_template_iife() if self._has_legacy_templates else ""
            )
            if self.is_debug_assets:
                return self.js_with_sourcemap(template_bundle=template_bundle)
            return self.save_attachment(
                extension, self._js.minified_bundle(template_bundle)
            )

    def _save_with_sourcemap(
        self,
        extension: str,
        body_builder: Callable[[SourceMapGenerator, str], str],
    ) -> IrAttachment:
        map_extension = f"{extension}.map"
        # the map's url is a function of the version, so it is known before
        # the map exists and no placeholder row has to be written to learn it
        map_url = self._store.get_versioned_url(map_extension)
        generator = SourceMapGenerator(
            source_root=_sourcemap_source_root(self.get_asset_url("debug", extension)),
        )
        with _debug.perf(
            "sourcemap_build", cr=self.env.cr, bundle=self.name, extension=extension
        ) as span:
            content_bundle = body_builder(generator, map_url)
            span.set(bytes=len(content_bundle))
        attachment = self.save_attachment(extension, content_bundle)

        generator.file = attachment.url
        map_attachment = self.save_attachment(
            map_extension, generator.get_content().decode()
        )
        _debug.lifecycle(
            "sourcemap_saved",
            bundle=self.name,
            extension=extension,
            attachment=attachment.id,
            map=map_attachment.id,
        )

        return attachment

    def js_with_sourcemap(self, template_bundle: str | None = None) -> IrAttachment:
        return self._save_with_sourcemap(
            "js",
            lambda generator, sourcemap_url: self._js.sourcemap_bundle(
                generator, sourcemap_url, template_bundle or ""
            ),
        )

    def xml(self) -> list[XMLBlock]:
        return self._xml.xml()

    def generate_esm_template_bundle(self, use_import=True) -> str:
        return self._xml.generate_esm_template_bundle(use_import)

    def css(self) -> IrAttachment:
        if not self.has_css_content:
            _debug.logic("css_attachment", bundle=self.name, reason="no_content")
            return self._no_attachment()
        return self._stored_or_built("css", self._build_css)

    def _build_css(self, extension: str) -> IrAttachment:
        with _debug.perf(
            "css_build",
            cr=self.env.cr,
            bundle=self.name,
            minified=not self.is_debug_assets,
            stylesheets=len(self.stylesheets),
            rtl=self.rtl,
        ) as span:
            css = self.preprocess_css()
            span.set(errors=len(self.css_errors))
        if self.css_errors:
            previous_attachment = self.get_attachments(extension, ignore_version=True)
            previous_css = (
                previous_attachment.raw.decode() if previous_attachment else ""
            )
            _debug.logic(
                "css_error_banner",
                bundle=self.name,
                errors=len(self.css_errors),
                previous=bool(previous_attachment),
            )
            banner = self._css._render_css_error_banner(self.css_errors, previous_css)
            return self.save_attachment(extension, banner)

        import_rules, css = self._css.hoist_import_rules(css)
        _debug.pipeline(
            "css_import_rules_hoisted",
            bundle=self.name,
            imports=len(import_rules),
            bytes=len(css),
        )

        if self.is_debug_assets:
            return self.css_with_sourcemap("\n".join(import_rules))
        return self.save_attachment(extension, "\n".join(import_rules + [css]))

    def css_with_sourcemap(self, content_import_rules: str) -> IrAttachment:
        return self._save_with_sourcemap(
            "css",
            lambda generator, sourcemap_url: self._css.sourcemap_bundle(
                generator, sourcemap_url, content_import_rules
            ),
        )

    @functools.cached_property
    def _css(self) -> CssPipeline:
        return CssPipeline(self)

    def preprocess_css(self) -> str:
        return self._css.preprocess()


def _check_extension_tables() -> None:
    for label, declared, handled in (
        ("STYLE_EXTENSIONS", STYLE_EXTENSIONS, AssetsBundle._STYLESHEET_TYPES),
        ("SCRIPT_EXTENSIONS", SCRIPT_EXTENSIONS, AssetsBundle._SCRIPT_TYPES),
        ("TEMPLATE_EXTENSIONS", TEMPLATE_EXTENSIONS, AssetsBundle._TEMPLATE_TYPES),
    ):
        if set(declared) != set(handled):
            raise ValueError(
                f"{label} is {sorted(declared)} but AssetsBundle builds "
                f"{sorted(handled)}. Extensions only in {label} are collected "
                f"into bundles and then dropped; extensions only in AssetsBundle "
                f"are unreachable."
            )


_check_extension_tables()
