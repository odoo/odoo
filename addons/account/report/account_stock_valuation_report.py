from collections import defaultdict

from odoo import api, fields, models


class StockValuationReport(models.AbstractModel):
    _name = 'account.stock.valuation.report'
    _description = 'Stock Valuation'

    @api.model
    def get_report_values(self, date=False):
        return {
            'data': self.with_context(allowed_company_ids=self.env.company.ids)._get_report_data(date=date),
            'context': {},
        }

    def _normalize_report_date(self, date):
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        if date == fields.Date.context_today(self):
            date = False
        return date

    def _get_report_data(self, date=False, product_category=False, warehouse=False):
        company = self.env.company
        date = self._normalize_report_date(date)

        inventory_data = company.get_inventory_value(at_date=date)
        accounting_data = company.get_inventory_accounting_value(at_date=date)

        accounts = inventory_data.keys() | accounting_data.keys()
        account_ids = {acc.id for acc in accounts}

        initial_balance = {
            'label': self.env._("Initial Balance"),
            'value': 0,
            'lines_by_account_id': defaultdict(lambda: {
                'value': 0,
            }),
        }
        ending_stock = {
            'label': self.env._("Ending Stock"),
            'value': 0,
            'lines_by_account_id': defaultdict(lambda: {
                'value': 0,
            }),
        }

        for account in accounts:
            opening_balance = accounting_data.get(account, 0)
            ending_balance = inventory_data.get(account, 0)
            if opening_balance:
                initial_balance['value'] += opening_balance
                initial_balance['lines_by_account_id'][account.id]['value'] += opening_balance
            if ending_balance:
                ending_stock['value'] += ending_balance
                ending_stock['lines_by_account_id'][account.id]['value'] += ending_balance

        extra_aml_vals_list = self._get_extra_stock_valuation_aml_vals(date)
        stock_valuation_account_vals = company.with_context(inventory_data=inventory_data)._get_stock_valuation_account_vals(
            date, extra_aml_vals_list)

        report_data = {
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'ending_stock': ending_stock,
            'initial_balance': initial_balance,
        }

        stock_variation = {
            'label': self.env._("Stock Variation"),
            'value': 0,
        }
        lines_by_account_id = defaultdict(lambda: {
            'debit': 0,
            'credit': 0,
            'lines': [],
        })
        for vals in stock_valuation_account_vals:
            account_ids.add(vals['account_id'])
            stock_variation['value'] += vals['balance']
            lines_by_account_id[vals['account_id']]['debit'] += vals['balance'] if vals['balance'] > 0 else 0
            lines_by_account_id[vals['account_id']]['credit'] -= vals['balance'] if vals['balance'] < 0 else 0
        stock_variation['lines'] = [{
            'account_id': account_id,
            'debit': vals['debit'],
            'credit': vals['credit'],
        } for (account_id, vals) in lines_by_account_id.items()]

        accounts_read_data = self.env['account.account'].search_read(
            [('id', 'in', account_ids)],
            ['id', 'name', 'code', 'display_name']
        )
        report_data.update(
            accounts_by_id={acc_data['id']: acc_data for acc_data in accounts_read_data},
            stock_variation=stock_variation,
        )
        return report_data

    def _get_extra_stock_valuation_aml_vals(self, date):
        """ Extra debit/credit vals already accounted for elsewhere, to subtract when computing
        the stock variation so it isn't double-counted (e.g. location-to-location
        reclassification entries).
        """
        return []
