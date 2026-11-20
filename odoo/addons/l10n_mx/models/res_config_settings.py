# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_mx_edi = fields.Boolean('Mexican Electronic Invoicing')

    @api.model
    def get_views(self, views, options=None):
        # HACK to not show the view since it uninstalls the module if unticked!
        # However, we don't want to force the upgrade of the module.
        # 'module_l10n_mx_edi' will be removed in master.
        mx_view = self.env.ref('l10n_mx.res_config_settings_view_form', raise_if_not_found=False).sudo()
        if mx_view.active:
            mx_view.active = False
        return super().get_views(views, options)
