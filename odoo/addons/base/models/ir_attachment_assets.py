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
    def _get_domain_esm_generated_assets(self) -> Domain:
        return self._get_domain_generated_assets() & Domain.OR(
            [
                [("url", "=like", f"{ESM_BRIDGES_URL_PREFIX}%")],
                [("url", "=like", f"{ESM_LIBS_URL_PREFIX}%")],
                [("name", "=like", "%.esm.js")],
                [("name", "=like", "%.esm.js.map")],
                [("name", "=like", "%.meta.json")],
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
    def _gc_esm_assets(self) -> tuple[int, int]:
        grace_days = self._get_esm_gc_grace_days()
        cutoff = fields.Datetime.now() - timedelta(days=grace_days)
        bridge_cutoff = fields.Datetime.now() - timedelta(
            days=self._get_esm_bridge_gc_grace_days()
        )
        is_bridge = Domain("url", "=like", f"{ESM_BRIDGES_URL_PREFIX}%")
        aged = self._get_domain_esm_generated_assets() & Domain.OR(
            [
                ~is_bridge & Domain("write_date", "<", cutoff),
                is_bridge & Domain("write_date", "<", bridge_cutoff),
            ]
        )
        deleted_artifacts = deleted_bridges = 0
        offset = 0
        more = False
        _debug.lifecycle(
            "esm_gc_started", grace_days=grace_days, batch=self._ESM_GC_BATCH
        )
        while True:
            if deleted_artifacts + deleted_bridges >= self._ESM_GC_BATCH:
                more = True
                _debug.logic("esm_gc_stopped", reason="batch_full", offset=offset)
                break
            candidates = self.sudo().search(
                aged, order="id", limit=self._ESM_GC_BATCH, offset=offset
            )
            if not candidates:
                _debug.logic("esm_gc_stopped", reason="exhausted", offset=offset)
                break
            stale_artifacts, bridges = self._get_esm_gc_collectable(candidates)
            to_gc = stale_artifacts | bridges
            _debug.pipeline(
                "esm_gc_batch",
                candidates=len(candidates),
                stale=len(stale_artifacts),
                bridges=len(bridges),
            )
            offset += len(candidates) - len(to_gc)
            if not to_gc:
                continue
            with _debug.perf("esm_gc_unlink", cr=self.env.cr, count=len(to_gc)):
                to_gc.unlink()
            deleted_artifacts += len(stale_artifacts)
            deleted_bridges += len(bridges)

        _debug.lifecycle(
            "esm_gc_done",
            artifacts=deleted_artifacts,
            bridges=deleted_bridges,
            more=more,
        )
        if not deleted_artifacts and not deleted_bridges:
            return 0, 0
        _logger.info(
            "GC'd %d stale ESM artifact(s) and %d aged bridge shim(s) "
            "older than %d day(s)",
            deleted_artifacts,
            deleted_bridges,
            grace_days,
        )
        return deleted_artifacts + deleted_bridges, int(more)

    def _get_esm_gc_collectable(self, candidates):
        bridges = candidates.filtered(
            lambda a: a.url.startswith(ESM_BRIDGES_URL_PREFIX)
        )
        artifacts = candidates - bridges
        if not artifacts:
            _debug.logic(
                "esm_gc_collectable", reason="bridges_only", bridges=len(bridges)
            )
            return self.browse(), bridges
        live_ids = set()
        seen_names = set()
        live_dirs = set()
        for att in self.sudo().search_fetch(
            self._get_domain_generated_assets()
            & Domain("name", "in", list(set(artifacts.mapped("name")))),
            ["name", "url"],
            order="write_date desc, id desc",
        ):
            if att.name not in seen_names:
                seen_names.add(att.name)
                live_ids.add(att.id)
                live_dirs.add(att.url.rpartition("/")[0])
        stale = artifacts.filtered(
            lambda a: a.id not in live_ids and a.url.rpartition("/")[0] not in live_dirs
        )
        _debug.logic(
            "esm_gc_collectable",
            artifacts=len(artifacts),
            live=len(live_ids),
            live_dirs=len(live_dirs),
            stale=len(stale),
            bridges=len(bridges),
        )
        return stale, bridges

    @api.model
    def regenerate_assets_bundles(self) -> None:
        self._check_admin_access()
        generated = self.search(self._get_domain_generated_assets())
        _debug.lifecycle("regenerate_assets_bundles", generated=len(generated))
        if generated:
            with _debug.perf(
                "regenerate_unlink", cr=self.env.cr, generated=len(generated)
            ):
                generated.unlink()
        else:
            _debug.lifecycle("assets_cache_cleared", reason="regenerate_no_generated")
            self.env.registry.clear_cache("assets")
