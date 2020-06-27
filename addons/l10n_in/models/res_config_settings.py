# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    group_l10n_in_multiple_gstn = fields.Boolean(implied_group='l10n_in.group_l10n_in_multiple_gstn', string='Multiple GSTN Units')

    def action_view_gstn_units(self):
        action = self.env.ref('l10n_in.action_l10n_in_view_gstn').read()[0]
        if action:
            action['domain'] = ['|', ('parent_id','=', self.env.company.partner_id.id), ('id','=', self.env.company.partner_id.id)]
        return action
