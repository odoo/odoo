from odoo import models

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        if not res["is_system"]:
            return res

        all_onboarding_records = self.env['onboarding.onboarding'].search([])
        open_onboarding_records = all_onboarding_records.filtered(lambda onboarding: not onboarding.is_onboarding_closed)

        res['onboarding_to_display'] = open_onboarding_records.mapped("route_name")
        return res
