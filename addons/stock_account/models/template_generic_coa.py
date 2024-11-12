from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('generic_coa', 'res.company')
    def _get_generic_coa_res_company(self):
        res = super()._get_generic_coa_res_company()
        res[self.env.company.id].update({
            'account_production_wip_account_id': 'wip',
            'account_production_wip_overhead_account_id': 'cost_of_production',
        })
        return res

    def _load_wip_accounts(self, company, template_data):
        company = company or self.env.company
        if company.id in template_data:
            company_data = template_data[company.id]
            if 'account_production_wip_account_id' in company_data:
                company.account_production_wip_account_id = self.ref(company_data['account_production_wip_account_id'])
            if 'account_production_wip_overhead_account_id' in company_data:
                company.account_production_wip_overhead_account_id = self.ref(company_data['account_production_wip_overhead_account_id'])
