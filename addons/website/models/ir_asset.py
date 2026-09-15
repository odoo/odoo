from uuid import uuid4

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrAsset(models.Model):
    _inherit = "ir.asset"

    key = fields.Char(copy=False)
    website_id = fields.Many2one(
        comodel_name="website",
        ondelete="cascade",
    )

    @api.model
    def _get_fields_invalidating_assets_cache(self):
        return super()._get_fields_invalidating_assets_cache() | {"website_id", "key"}

    def _prepare_assets_params(self):
        params = super()._prepare_assets_params()
        params["website_id"] = (
            self.env["website"].get_current_website(fallback=False).id
        )
        return params

    def _get_asset_bundle_url_segments(self, assets_params):
        segments = super()._get_asset_bundle_url_segments(assets_params)
        website_id = assets_params.get("website_id", None)
        return (*segments, str(website_id)) if website_id else segments

    def _get_assets(self, domain, *, website_id=None, **params):
        if website_id:
            domain = (
                Domain(domain) & self.env["website"].browse(website_id).website_domain()
            )
        return super()._get_assets(domain, **params)

    def _filter_bundle_assets(self, assets, *, website_id=None, **params):
        return (
            super()
            ._filter_bundle_assets(assets, **params)
            ._filtered_most_specific(website_id)
        )

    def _get_addons_active(self, *, website_id=None, **params):
        addons_list = super()._get_addons_active(**params)

        if not website_id:
            return addons_list

        IrModule = self.env["ir.module.module"].sudo()
        themes = (
            IrModule.search(IrModule.get_domain_themes())
            - self.env["website"].browse(website_id).theme_id
        )
        to_remove = set(themes.mapped("name"))

        _debug.logic(
            "theme_addons_filtered",
            website=website_id,
            removed=len(to_remove & set(addons_list)),
        )
        return [name for name in addons_list if name not in to_remove]

    def _filtered_most_specific(self, website_id=None):
        if website_id is None:
            website_id = self.env["website"].get_current_website(fallback=False).id
        if not website_id:
            return self.filtered(lambda asset: not asset.website_id)

        specific_asset_keys = {
            asset.key
            for asset in self
            if asset.website_id.id == website_id and asset.key
        }
        most_specific_assets = []
        for asset in self:
            if asset.website_id:
                if asset.website_id.id == website_id:
                    most_specific_assets.append(asset)
                continue
            if asset.key not in specific_asset_keys:
                most_specific_assets.append(asset)

        return self.browse().union(*most_specific_assets)

    def write(self, vals):
        current_website_id = self.env.context.get("website_id")
        if not current_website_id or self.env.context.get("no_cow"):
            return super().write(vals)

        for asset in self.with_context(active_test=False):
            if asset.website_id:
                _debug.logic("asset_cow_write", by="already_specific", asset=asset.id)
                super(IrAsset, asset).write(vals)
                continue

            asset_values = vals
            if not asset.key:
                # Copy-on-write needs an identity shared by the generic asset
                # and its overrides; False also matches unrelated unkeyed assets.
                super(IrAsset, asset).write(
                    {"key": vals.get("key") or f"website.asset_{uuid4().hex}"}
                )
                asset_values = {**vals, "key": asset.key}
                _debug.lifecycle("asset_key_generated", asset=asset.id, key=asset.key)

            website_specific_asset = asset.search(
                [("key", "=", asset.key), ("website_id", "=", current_website_id)],
                limit=1,
            )
            if website_specific_asset:
                _debug.logic(
                    "asset_cow_write",
                    by="existing_specific",
                    asset=asset.id,
                    specific=website_specific_asset.id,
                )
                super(IrAsset, website_specific_asset).write(asset_values)
                continue

            copy_vals = {"website_id": current_website_id, "key": asset.key}
            website_specific_asset = asset.copy(copy_vals)
            _debug.lifecycle(
                "asset_cow_copied",
                asset=asset.id,
                specific=website_specific_asset.id,
                website=current_website_id,
            )

            super(IrAsset, website_specific_asset).write(asset_values)

        return True
