import functools
import logging
from pathlib import Path

from psycopg.errors import ReadOnlySqlTransaction

from odoo import models
from odoo.fields import Domain
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.tools.assets.esbuild import minify_js
from odoo.tools.assets.esm_libs import served_lib_content

from odoo.addons.base.models.ir_qweb_assets import _EsmReadonlyDeclined

_attach_log = get_asset_logger("attach")
_debug = DebugLog(__name__)


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _get_external_libs_served(self, *, debug_assets: bool) -> dict[str, str]:
        if debug_assets:
            _debug.logic("served_libs_fallback", reason="debug_assets")
            return dict(self._external_libs())
        try:
            self._create_served_libs()
        except _EsmReadonlyDeclined:
            _debug.logic("served_libs_fallback", reason="readonly_declined")
            return dict(self._external_libs())
        return dict(self._served_external_libs_table())

    @staticmethod
    def _minify_served_lib(path: Path, declared_url: str) -> bytes:
        source = path.read_text(encoding="utf-8")
        with _debug.perf(
            "served_lib_minify", url=declared_url, bytes=len(source)
        ) as span:
            minified = minify_js(source, label=declared_url, keep_names=True)
            span.set(minified=minified is not None)
        return (minified if minified is not None else source).encode("utf-8")

    def _create_served_libs(self) -> None:
        files = self._served_lib_files()
        if not files:
            _debug.logic("served_libs_skipped", reason="no_files")
            return
        IrAttachment = self.env["ir.attachment"].sudo()
        present = set(
            IrAttachment.search_fetch(
                IrAttachment._get_domain_generated_assets()
                & Domain("url", "in", list(files)),
                ["url"],
            ).mapped("url")
        )
        vals_list = []
        for served_url, (_lib, declared_url) in files.items():
            if served_url in present:
                continue
            path = _lib.files[declared_url]
            vals_list.append(
                IrAttachment._prepare_generated_asset_vals(
                    name=declared_url.lstrip("/"),
                    mimetype="text/javascript",
                    raw=served_lib_content(
                        served_url,
                        functools.partial(self._minify_served_lib, path, declared_url),
                    ),
                    url=served_url,
                )
            )
        _debug.lifecycle(
            "served_libs",
            declared=len(files),
            present=len(present),
            missing=len(vals_list),
        )
        if not vals_list:
            return
        try:
            self._save_esm_attachment_rows(vals_list, bundle="esm.libs")
        except ReadOnlySqlTransaction:
            _debug.logic(
                "served_libs_save_failed",
                readonly=self.env.cr.readonly,
                files=len(vals_list),
            )
            if not self.env.cr.readonly:
                raise
            log_event(
                _attach_log,
                logging.WARNING,
                "libs_save_declined",
                files=len(vals_list),
                reused=len(present),
                readonly=True,
            )
            raise _EsmReadonlyDeclined from None
        log_event(
            _attach_log,
            logging.INFO,
            "libs_save",
            files=len(vals_list),
            reused=len(present),
        )
