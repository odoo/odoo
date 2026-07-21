# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrQWeb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super()._get_bundles_to_pregenarate()
        assets = {"bus.websocket_worker_assets"}
        return (js_assets | assets, css_assets | assets)
