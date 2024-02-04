# Copyright 2020 Alexandre Díaz <dev@redneboa.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.http import request

from odoo.addons.base.models.assetsbundle import AssetsBundle, ScssStylesheetAsset


class AssetsBundleCompanyColor(AssetsBundle):
    def get_company_color_asset_node(self):
        """Process the user active company scss and returns the node to inject"""
        try:
            active_company_id = int(
                request.httprequest.cookies.get("cids", "").split(",")[0]
            )
        except Exception:
            active_company_id = False
        company_id = (
            self.env["res.company"].browse(active_company_id) or self.env.company
        )
        asset = ScssStylesheetAsset(self, url=company_id.scss_get_url())
        compiled = self.compile_css(asset.compile, asset.get_source())
        return "style", {}, compiled
