from odoo import api, models


# countries where KYC is managed with Peppol and where it is mandatory
COUNTRIES_WITH_PEPPOL = {
    'BE',
}

class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_account_peppol_kpi_summary(self):
        results = {}
        all_companies = self.env['res.company'].sudo().search([
            ('account_fiscal_country_id.code', 'in', list(COUNTRIES_WITH_PEPPOL)),
        ])
        for company in all_companies:
            if company.account_peppol_proxy_state == 'active':
                results[company.id] = 'done'
            elif company.account_peppol_proxy_state == 'pending':
                results[company.id] = 'incomplete'
            else:
                results[company.id] = 'not_done'

        if not results:
            return []

        all_states = set(results.values())
        if len(all_states) == 1:
            final_state = all_states.pop()
        else:
            final_state = 'incomplete'

        return [{
            'id': 'account_peppol.proxy_state',
            'name': 'KYC',
            'type': 'kyc_status',
            'value': final_state,
        }]

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_account_peppol_kpi_summary())
        return result
