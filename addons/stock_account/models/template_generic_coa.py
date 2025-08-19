from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_data(self, template_code, company, template_data):
        res = super()._post_load_data(template_code, company, template_data)
        company.account_stock_valuation_id.account_stock_expense_id = company.expense_account_id
        return res

    @template('generic_coa', 'res.company')
    def _get_generic_coa_res_company(self):
        res = super()._get_generic_coa_res_company()
        res[self.env.company.id].update({
            'account_stock_journal_id': 'inventory_valuation',
            'account_stock_valuation_id': 'stock_valuation',
            'account_production_wip_account_id': 'wip',
            'account_production_wip_overhead_account_id': 'cost_of_production',
        })
        return res

    def _get_generic_coa_account_account(self):
        # TODO: Probably the correct place to add link between account
        return super()._get_generic_coa_account_account()
