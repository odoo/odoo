# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    crm_team_id = fields.Many2one('crm.team', related='config_id.crm_team_id', string="Sales Channel", readonly=True)
