# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons import web_editor, portal, mail


class IrQweb(mail.IrQweb, web_editor.IrQweb, portal.IrQweb):

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super()._get_bundles_to_pregenarate()
        assets = {'mass_mailing.iframe_css_assets_edit'}
        return (js_assets | assets, css_assets | assets)
