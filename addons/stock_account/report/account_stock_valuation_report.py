from collections import defaultdict

from odoo import _, models


class StockValuationReport(models.AbstractModel):
    _inherit = 'account.stock.valuation.report'

    def _get_report_data(self, date=False, product_category=False, warehouse=False):
        # OVERRIDE: add the "Inventory Loss" section (stock locations used to reclassify
        # losses) and enable the "Generate Entry" (periodic closing) button, both only
        # meaningful when the stock module is installed.
        report_data = super()._get_report_data(date=date, product_category=product_category, warehouse=warehouse)

        if not self._must_include_inventory_loss():
            return report_data

        date = self._normalize_report_date(date)

        location_valuation_vals = self._get_extra_stock_valuation_aml_vals(date)
        inventory_loss = {
            'label': _("Inventory Loss"),
            'value': 0,
        }
        lines_by_account_id = defaultdict(lambda: {
            'debit': 0,
            'credit': 0,
        })
        account_ids = set()
        for vals in location_valuation_vals:
            account_ids.add(vals['account_id'])
            inventory_loss['value'] -= vals['balance'] if vals['balance'] > 0 else 0
            lines_by_account_id[vals['account_id']]['debit'] += vals['balance'] if vals['balance'] > 0 else 0
            lines_by_account_id[vals['account_id']]['credit'] -= vals['balance'] if vals['balance'] < 0 else 0
        inventory_loss['lines'] = [{
            'account_id': account_id,
            'debit': vals['debit'],
            'credit': vals['credit'],
        } for (account_id, vals) in lines_by_account_id.items()]
        report_data['inventory_loss'] = inventory_loss

        missing_account_ids = account_ids - set(report_data['accounts_by_id'].keys())
        if missing_account_ids:
            accounts_read_data = self.env['account.account'].search_read(
                [('id', 'in', list(missing_account_ids))],
                ['id', 'name', 'code', 'display_name'],
            )
            report_data['accounts_by_id'].update({acc_data['id']: acc_data for acc_data in accounts_read_data})

        return report_data

    def _must_include_inventory_loss(self):
        return bool(self.env['stock.location'].search_count([
            ('usage', '=', 'inventory'),
            ('valuation_account_id', '!=', False),
        ], limit=1))

    def _get_extra_stock_valuation_aml_vals(self, date):
        return self.env.company._get_location_valuation_vals(
            date, location_domain=[('usage', '=', 'inventory')],
        )
