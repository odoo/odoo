# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_multiple_ddt = fields.Boolean(implied_group='l10n_it.group_multiple_ddt_account',
        group='base.group_portal,base.group_user,base.group_public')
    group_single_ddt = fields.Boolean(implied_group='l10n_it.group_single_ddt_account',
        group='base.group_portal,base.group_user,base.group_public')

    @api.multi
    def set_values(self):
        self.group_single_ddt = not self.group_multiple_ddt
        super(ResConfigSettings, self).set_values()

    # @api.onchange('group_multiple_ddt')
    # def onchange_group_multiple_ddt(self):
    #     # self.group_single_ddt = not self.group_multiple_ddt
    #     self.update({
    #         'group_single_ddt': not self.group_multiple_ddt,
    #     })
