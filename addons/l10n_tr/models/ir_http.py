from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        session_info = super().session_info()
        # Expose each allowed company's fiscal country code, so we can have localization specific button on list views
        allowed_companies = session_info.get('user_companies', {}).get('allowed_companies')
        if allowed_companies:
            for company in self.env['res.company'].sudo().browse(allowed_companies.keys()):
                allowed_companies[company.id]['country_code'] = company.account_fiscal_country_id.code
        return session_info
