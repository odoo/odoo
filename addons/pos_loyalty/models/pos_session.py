# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        data += ['loyalty.program', 'loyalty.rule', 'loyalty.reward', 'loyalty.card']
        return data

    def filter_local_data(self, models_to_filter):
        res = super().filter_local_data(models_to_filter)
        if 'loyalty.program' in models_to_filter:
            loyalty_programs = self.env['loyalty.program'].search([('id', 'in', models_to_filter['loyalty.program'])])
            valid_programs = self.config_id._get_program_ids()
            res['loyalty.program'] = (loyalty_programs - valid_programs).ids
        return res
