# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_crm_livechat = fields.Boolean("Lead Generation")

    @api.onchange('module_crm_livechat')
    def onchange_module_crm_livechat(self):
        if self.module_crm_livechat and hasattr(self, 'group_use_lead') and not self.group_use_lead:
            self.group_use_lead = True
