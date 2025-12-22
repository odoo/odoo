
from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def create(self, vals):
        configs = super().create(vals)
        if any(config.hr_presence_control_ip or config.hr_presence_control_email for config in configs):
            self.env['hr.employee.base']._check_presence()
        return configs
