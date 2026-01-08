from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_available_fidelity_programs(self):
        today = fields.Date.context_today(self)
        return self.env['fidelity.program'].search([
            ('available_in_pos', '=', True),
            '|', ('limit_usage_remaining', '>', 0), ('limit_usage', '=', False),
            '|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False),
            '|', ('start_date', '=', False), ('start_date', '<=', today),
            '|', ('end_date', '=', False), ('end_date', '>=', today),
        ])
