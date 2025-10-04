# -*- coding: utf-8 -*-
from odoo import models

class IrQWeb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super(IrQWeb, self)._get_bundles_to_pregenarate()
        assets = {
            'web_editor.assets_legacy_wysiwyg',
            'web_editor.backend_assets_wysiwyg',
            'web_editor.assets_wysiwyg',
            'web_editor.wysiwyg_iframe_editor_assets',
        }
        return (js_assets | assets, css_assets | assets)
