from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.onchange('private_city_id')
    def _onchange_private_city_id(self):
        self.version_id._inverse_private_city_id()
