# -*- coding: utf-8 -*-
from odoo import models

class IrQWeb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super(IrQWeb, self)._get_bundles_to_pregenarate()
        assets = {'mass_mailing.iframe_css_assets_edit'}
        return (js_assets | assets, css_assets | assets)
