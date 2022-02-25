# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import pytz


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    pos_config_ids = fields.One2many('pos.config', 'crm_team_id', string="Point of Sales")
    pos_sessions_open_count = fields.Integer(string='Open POS Sessions', compute='_compute_pos_sessions_open_count')
    pos_order_amount_total = fields.Float(string="Session Sale Amount", compute='_compute_pos_order_amount_total')

    def _compute_pos_sessions_open_count(self):
        for team in self:
            team.pos_sessions_open_count = self.env['pos.session'].search_count([('config_id.crm_team_id', '=', team.id), ('state', '=', 'opened')])

    def _compute_pos_order_amount_total(self):
        data = self.env['report.pos.order']._read_group([
            ('session_id.state', '=', 'opened'),
            ('config_id.crm_team_id', 'in', self.ids),
        ], ['price_total:sum', 'config_id'], ['config_id'])
        rg_results = dict((d['config_id'][0], d['price_total']) for d in data)
        for team in self:
            team.pos_order_amount_total = sum([
                rg_results.get(config.id, 0.0)
                for config in team.pos_config_ids
            ])
