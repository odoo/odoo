from collections import defaultdict

from odoo import _, models


class StockValuationReport(models.AbstractModel):
    _inherit = 'stock_account.stock.valuation.report'

    def _get_report_data(self, date=False, product_category=False, warehouse=False):
        report_data = super()._get_report_data(date=date, product_category=product_category, warehouse=warehouse)
        if not self._must_include_cost_of_production():
            return report_data
        production_locations_valuation_vals = self.env.company._get_location_valuation_vals(
            location_domain=[('usage', '=', 'production')]
        )
        cost_of_production = {
            'label': _("Cost of Production"),
            'value': 0,
        }
        lines_by_account_id = defaultdict(lambda: {
            'debit': 0,
            'credit': 0,
            'lines': [],
        })
        for vals in production_locations_valuation_vals:
            account = self.env['account.account'].browse(vals['account_id'])
            if account:
                account_vals = account.read(['name', 'code', 'display_name'])[0]
                report_data['accounts_by_id'][account.id] = account_vals
            cost_of_production['value'] -= vals['debit']
            lines_by_account_id[account.id]['debit'] += vals['debit']
            lines_by_account_id[account.id]['credit'] += vals['credit']
            lines_by_account_id[account.id]['lines'].append(vals)
        cost_of_production['lines'] = [{
            'account_id': account_id,
            'debit': vals['debit'],
            'credit': vals['credit'],
        } for (account_id, vals) in lines_by_account_id.items()]
        report_data['cost_of_production'] = cost_of_production
        return report_data

    def _must_include_cost_of_production(self):
        return bool(self.env['stock.location'].search_count([
            ('usage', '=', 'production'),
            ('valuation_account_id', '!=', False),
        ], limit=1))
