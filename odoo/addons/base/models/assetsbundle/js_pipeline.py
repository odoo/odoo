import logging
from typing import TYPE_CHECKING

from odoo.libs.asset_log import log_event
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import SourceMapGenerator
from odoo.tools import config
from odoo.tools.assets.esm_graph import (
    has_module_syntax,
)
from odoo.tools.json import scriptsafe as json

if TYPE_CHECKING:
    from .bundle import AssetsBundle
from .assets import JavascriptAsset
from .common import _bundle_log

_debug = DebugLog(__name__)


class ModuleSyntaxInLegacyBundleError(RuntimeError):
    pass


class JsPipeline:
    def __init__(self, bundle: AssetsBundle) -> None:
        self._bundle = bundle

    @staticmethod
    def _is_asset_error_fatal() -> bool:
        return bool(config["test_enable"] or "assets" in config["dev_mode"])

    def _module_syntax_error_stub(self, asset: JavascriptAsset) -> str | None:
        bundle = self._bundle
        if bundle._is_esm_bundle:
            return None
        header = asset.parsed_header
        if header and header["ignore"]:
            _debug.logic("module_syntax_ignored", bundle=bundle.name, url=asset.url)
            return None
        if not header and not has_module_syntax(asset.raw_content):
            return None
        msg = (
            f"Module-syntax file {asset.url or asset.name!r} cannot be "
            f"concatenated into non-ESM bundle {bundle.name!r}; declare the "
            "bundle under the 'esm' key of its module's manifest to serve "
            "it. File skipped."
        )
        log_event(
            _bundle_log,
            logging.ERROR,
            "module_syntax_in_legacy_bundle",
            bundle=bundle.name,
            url=asset.url or "<inline>",
        )
        _debug.logic(
            "module_syntax_stub",
            bundle=bundle.name,
            url=asset.url or "<inline>",
            fatal=self._is_asset_error_fatal(),
        )
        if self._is_asset_error_fatal():
            raise ModuleSyntaxInLegacyBundleError(msg)
        return f"console.error({json.dumps(msg)});"

    def minified_bundle(self, template_bundle: str) -> str:
        with _debug.perf(
            "js_minify",
            bundle=self._bundle.name,
            assets=len(self._bundle.javascripts),
            templates=bool(template_bundle),
        ):
            content_bundle = ";\n".join(
                self._module_syntax_error_stub(asset) or asset.minify()
                for asset in self._bundle.javascripts
            )
        if template_bundle:
            content_bundle += ";" + template_bundle
        _debug.pipeline(
            "js_minified_bundle",
            bundle=self._bundle.name,
            assets=len(self._bundle.javascripts),
            bytes=len(content_bundle),
            templates=len(template_bundle),
        )
        return content_bundle

    def sourcemap_bundle(
        self, generator: SourceMapGenerator, sourcemap_url: str, template_bundle: str
    ) -> str:
        content_bundle_list = []
        content_line_count = 0
        line_header = JavascriptAsset._HEADER_LINE_COUNT
        stubbed = 0  # debuglog
        for asset in self._bundle.javascripts:
            stub = self._module_syntax_error_stub(asset)
            if stub:
                content_bundle_list.append(stub)
                content_line_count += stub.count("\n") + 1
                stubbed += 1  # debuglog
                continue
            generator.add_source(
                asset.url,
                asset.content,
                content_line_count,
                start_offset=line_header,
            )

            content_bundle_list.append(asset.with_header(asset.content, minimal=False))
            content_line_count += asset.content.count("\n") + 1 + line_header

        content_bundle = ";\n".join(content_bundle_list)
        if template_bundle:
            content_bundle += ";" + template_bundle

        content_bundle += "\n\n//# sourceMappingURL=" + sourcemap_url
        _debug.pipeline(
            "sourcemap_bundle",
            bundle=self._bundle.name,
            assets=len(self._bundle.javascripts),
            stubbed=stubbed,
            lines=content_line_count,
            bytes=len(content_bundle),
        )

        return content_bundle
