# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import AccessError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_pos_team(self):
        team = self.env['crm.team'].search(['|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)], limit=1)
        return team

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team",
        help="This Point of sale's sales will be related to this Sales Team.",
        default=_get_default_pos_team)
