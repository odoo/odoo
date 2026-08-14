from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        if self.env.user._is_internal():
            result['sales_team_membership_multi'] = self.env['ir.config_parameter'].sudo().get_bool('sales_team.membership_multi')
        return result
