# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_stock_valuation_total = fields.Boolean('Total Inventory Valuation')
    kpi_stock_valuation_total_value = fields.Monetary(compute='_compute_kpi_stock_valuation_total_value')

    def _compute_kpi_stock_valuation_total_value(self):
        self._ensure_user_has_one_of_the_group('stock.group_stock_manager')
        __, end, companies = self._get_kpi_compute_parameters()
        values = self.env['stock.valuation.layer']._read_group(
            domain=[('company_id', 'in', companies.ids), ('create_date', '<', end)],
            groupby=['company_id'],
            aggregates=['value:sum'],
        )
        values_per_company = {company.id: agg for company, agg in values}
        for digest in self:
            company = digest.company_id or self.env.company
            digest.kpi_stock_valuation_total_value = values_per_company.get(company.id, 0)

    def _compute_kpis_app_name(self):
        res = super()._compute_kpis_app_name()
        res['kpi_stock_valuation_total'] = 'stock'
        return res

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        menu_root_id = self.env.ref('stock.menu_stock_root').id
        res['kpi_stock_valuation_total'] = f'stock_account.stock_valuation_layer_action&menu_id={menu_root_id}'
        return res
