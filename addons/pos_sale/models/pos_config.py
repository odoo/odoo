# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", domain=[('team_type', '=', 'pos')],
        default=lambda self: self.env['crm.team'].search([('team_type', '=', 'pos')], limit=1).id,
        help="This Point of sale's sales will be related to this Sales Team.")
