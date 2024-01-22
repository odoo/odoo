# Copyright 2020 Alexandre Díaz <dev@redneboa.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models

from .assetsbundle import AssetsBundleCompanyColor


class QWeb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _generate_asset_nodes_cache(
        self,
        bundle,
        css=True,
        js=True,
        debug=False,
        async_load=False,
        defer_load=False,
        lazy_load=False,
        media=None,
    ):
        res = super()._generate_asset_nodes(
            bundle, css, js, debug, async_load, defer_load, lazy_load, media
        )
        if bundle == "web_company_color.company_color_assets":
            asset = AssetsBundleCompanyColor(
                bundle, [], env=self.env, css=True, js=True
            )
            res += [asset.get_company_color_asset_node()]
        return res

    def _get_asset_content(self, bundle, defer_load=False, lazy_load=False, media=None):
        """Handle 'special' web_company_color bundle"""
        if bundle == "web_company_color.company_color_assets":
            return [], []
        return super()._get_asset_content(
            bundle, defer_load=defer_load, lazy_load=lazy_load, media=media
        )
