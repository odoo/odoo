from odoo import models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append('hr.employee')
        return result

    def _loader_params_hr_employee(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'name', 'allowed_floor_ids'],
            }
        }

    def _get_pos_ui_hr_employee(self, params):
        return self.env['hr.employee'].search_read(
            params['search_params']['domain'],
            params['search_params']['fields']
        )