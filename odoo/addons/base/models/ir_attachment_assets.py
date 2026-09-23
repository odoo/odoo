import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools.assets.constants import ESM_BRIDGE_REFRESH_DAYS

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

ASSETS_URL_PREFIX = "/web/assets/"
ESM_BRIDGES_URL_PREFIX = "/web/assets/esm/bridges/"
ESM_LIBS_URL_PREFIX = "/web/assets/lib/"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    _ESM_GC_GRACE_DAYS = 7

    _ESM_BRIDGE_GC_GRACE_DAYS = 90

    _ESM_GC_BATCH = 1000

    def unlink(self) -> bool:
        clear_assets = any(
            url and url.startswith(ASSETS_URL_PREFIX) for url in self.mapped("url")
        )
        res = super().unlink()
        if clear_assets:
            _debug.lifecycle(
                "assets_cache_cleared", reason="attachment_unlink", count=len(self)
            )
            self.env.registry.clear_cache("assets")
        return res

    @api.model
    def _prepare_generated_asset_vals(
        self, *, name: str, mimetype: str, raw: bytes, url: str
    ) -> dict:
        return {
            "name": name,
            "mimetype": mimetype,
            "res_model": "ir.ui.view",
            "res_id": False,
            "type": "binary",
            "public": True,
            "raw": raw,
            "url": url,
        }

    @api.model
    def _is_generated_asset_vals(self, values: dict) -> bool:
        return bool(
            (values.get("url") or "").startswith(ASSETS_URL_PREFIX)
            and values.get("res_model") == "ir.ui.view"
            and not values.get("res_id")
            and values.get("public")
        )

    @api.model
    def _should_index_content(self, values: dict) -> bool:
        # nobody searches a compiled bundle by its words; indexing one costs
        # the text extraction of a megabyte of minified code per row
        if self._is_generated_asset_vals(values):
            _debug.logic("index_skipped", reason="generated_asset")
            return False
        return super()._should_index_content(values)

    @api.model
    def _get_domain_generated_assets(
        self, url: str | None = None, url_pattern: str | None = None
    ) -> Domain:
        if url:
            url_leaf = ("url", "=", url)
        elif url_pattern:
            url_leaf = ("url", "=like", url_pattern)
        else:
            url_leaf = ("url", "=like", f"{ASSETS_URL_PREFIX}%")
        return Domain(
            [
                ("public", "=", True),
                ("res_model", "=", "ir.ui.view"),
                ("res_id", "=", 0),
                ("create_uid", "=", api.SUPERUSER_ID),
                url_leaf,
            ]
        )

    @api.model
    def _get_esm_bridge_gc_grace_days(self) -> int:
        configured = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int(
                "web.esm.bridge_gc_grace_days", self._ESM_BRIDGE_GC_GRACE_DAYS
            )
        )
        _debug.logic(
            "esm_bridge_gc_grace",
            configured=configured,
            floor=int(2 * ESM_BRIDGE_REFRESH_DAYS) + 1,
        )
        return max(int(2 * ESM_BRIDGE_REFRESH_DAYS) + 1, configured)

    @api.model
    def _get_esm_gc_grace_days(self) -> int:
        return max(
            1,
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int("web.esm.gc_grace_days", self._ESM_GC_GRACE_DAYS),
        )

    @api.autovacuum
    def _gc_esm_bridges(self) -> int:
        # a bridge shim belongs to no build: pages import it by content, and a
        # reuse refreshes its write_date, so age alone says it is unused.
        # Every other generated ESM file is a build's, collected with it
        cutoff = fields.Datetime.now() - timedelta(
            days=self._get_esm_bridge_gc_grace_days()
        )
        aged = self.sudo().search(
            self._get_domain_generated_assets(url_pattern=f"{ESM_BRIDGES_URL_PREFIX}%")
            & Domain("write_date", "<", cutoff),
            limit=self._ESM_GC_BATCH,
        )
        _debug.lifecycle("esm_bridges_gc", aged=len(aged), batch=self._ESM_GC_BATCH)
        if aged:
            with _debug.perf("esm_gc_unlink", cr=self.env.cr, count=len(aged)):
                aged.unlink()
            _logger.info("GC'd %d aged ESM bridge shim(s)", len(aged))
        return len(aged)

    @api.model
    def regenerate_assets_bundles(self) -> None:
        self._check_admin_access()
        generated = self.search(self._get_domain_generated_assets())
        builds = self.env["ir.asset.build"].sudo().search([])
        _debug.lifecycle(
            "regenerate_assets_bundles", generated=len(generated), builds=len(builds)
        )
        builds.unlink()
        if generated:
            with _debug.perf(
                "regenerate_unlink", cr=self.env.cr, generated=len(generated)
            ):
                generated.unlink()
        else:
            _debug.lifecycle("assets_cache_cleared", reason="regenerate_no_generated")
            self.env.registry.clear_cache("assets")
