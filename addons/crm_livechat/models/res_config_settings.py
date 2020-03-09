# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_generate_lead = fields.Boolean('Lead Generation', implied_group='crm_livechat.group_generate_lead')

    @api.onchange('group_use_lead')
    def _onchange_group_use_lead(self):
        super(ResConfigSettings, self)._onchange_group_use_lead()
        if not self.group_use_lead and self.group_generate_lead:
            self.group_generate_lead = False
