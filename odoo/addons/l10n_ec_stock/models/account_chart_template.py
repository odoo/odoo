# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo):
        # EXTENDS account to set up default accounts on stock locations
        res = super()._load(template_code, company, install_demo)
        if template_code == 'ec':
            self._l10n_ec_setup_location_accounts(company)
        return res

    def _l10n_ec_setup_location_accounts(self, companies):
        parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
        loss_locs = dict(self.env['stock.location']._read_group(domain=[('location_id', '=', parent_location.id), ('usage', '=', 'inventory'), ('scrap_location', '=', False)], groupby=['company_id', 'id'])) if parent_location else {}
        prod_locs = dict(self.env['stock.location']._read_group(domain=[('location_id', '=', parent_location.id), ('usage', '=', 'production'), ('scrap_location', '=', False)], groupby=['company_id', 'id'])) if parent_location else {}
        for company in companies:
            # get template data
            Template = self.env['account.chart.template'].with_company(company)
            template_code = company.chart_template
            full_data = Template._get_chart_template_data(template_code)
            template_data = full_data.pop('template_data')

            ref = template_data.get('loss_stock_valuation_account')
            if (loss_loc := loss_locs.get(company)) and (loss_loc_account := ref and Template.ref(ref, raise_if_not_found=False)):
                loss_loc.write({
                    'valuation_in_account_id': loss_loc_account.id,
                    'valuation_out_account_id': loss_loc_account.id,
                })

            ref = template_data.get('production_stock_valuation_account')
            if (prod_loc := prod_locs.get(company)) and (prod_loc_account := ref and Template.ref(ref, raise_if_not_found=False)):
                prod_loc.write({
                    'valuation_in_account_id': prod_loc_account.id,
                    'valuation_out_account_id': prod_loc_account.id,
                })
