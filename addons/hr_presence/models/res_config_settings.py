from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        if any(config.hr_presence_control_ip or config.hr_presence_control_email for config in configs):
            self.env['hr.employee']._check_presence()
        return configs
