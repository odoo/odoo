# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        help='If set, this Sales Team will be used for sales and assignations related to this partner')

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id and not self.team_id:
            self.team_id = self.user_id.sale_team_id