# -*- coding: utf-8 -*-
from odoo import models


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super()._get_bundles_to_pregenarate()
        assets = {'mass_mailing.assets_iframe_style'}
        return (js_assets | assets, css_assets | assets)
