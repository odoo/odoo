from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.onchange('private_city_id')
    def _onchange_private_city_id(self):
        # @api.onchange on hr.version (the _inherits delegate) doesn't fire when the field is edited through hr.employee's own form.
        # Only hr.employee's own onchange methods do.
        # Mirrors hr.employee._onchange_private_state_id in hr/models/hr_employee.py.
        self.version_id._inverse_private_city_id()
