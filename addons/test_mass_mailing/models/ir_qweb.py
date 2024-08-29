# -*- coding: utf-8 -*-
from odoo.addons import base
from odoo import models

class IrQweb(models.AbstractModel, base.IrQweb):

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super()._get_bundles_to_pregenarate()
        assets = {'mass_mailing.iframe_css_assets_edit'}
        return (js_assets | assets, css_assets | assets)
