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
        valuation_account_ids = set(account_ids)

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

        report_data = {
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'company_inventory_valuation': company.inventory_valuation,
            'ending_stock': ending_stock,
            'initial_balance': initial_balance,
        }
        accrual, pending_cogs_vals = self._format_accrual_data(company._get_accrual_data(date=date, post=False))
        if accrual:
            account_ids.update(self._get_line_account_ids(accrual['lines']))
            report_data['accrual'] = accrual

        initial_aml_vals_list = self._get_extra_stock_valuation_aml_vals(date)
        initial_aml_vals_list += pending_cogs_vals

        stock_variation = {
            'label': self.env._("Stock Variation"),
            'value': 0,
            'lines': [],
        }
        stock_valuation_account_vals = company.with_context(inventory_data=inventory_data)._get_stock_valuation_account_vals(date, initial_aml_vals_list)
        account_ids.update(vals["account_id"] for vals in stock_valuation_account_vals)
        stock_variation["value"] = sum(
            vals["balance"] for vals in stock_valuation_account_vals
            if vals["account_id"] in valuation_account_ids
        )
        stock_variation["lines"] = self._get_balance_lines_by_account(stock_valuation_account_vals)

        accounts_read_data = self.env['account.account'].search_read(
            [('id', 'in', account_ids)],
            ['id', 'name', 'code', 'display_name']
        )
        report_data.update(
            accounts_by_id={acc_data['id']: acc_data for acc_data in accounts_read_data},
            stock_variation=stock_variation,
        )
        return report_data

    def _get_balance_lines_by_account(self, vals_list):
        """ `vals_list` ({'account_id', 'balance'} dicts) folded into one debit/credit line per account. """
        lines_by_account_id = defaultdict(float)
        for vals in vals_list:
            lines_by_account_id[vals['account_id']] += vals['balance']
        return [{
            'account_id': account_id,
            'debit': balance if balance > 0 else 0,
            'credit': -balance if balance < 0 else 0,
        } for (account_id, balance) in lines_by_account_id.items()]

    def _get_line_account_ids(self, lines):
        """ Account ids referenced anywhere in `lines`, including nested sublines (a line's
        'lines' key), so `accounts_by_id` covers them for display. """
        account_ids = set()
        for line in lines:
            if line.get('account_id'):
                account_ids.add(line['account_id'])
            if line.get('lines'):
                account_ids.update(self._get_line_account_ids(line['lines']))
        return account_ids

    def _get_extra_stock_valuation_aml_vals(self, date):
        """ Extra debit/credit vals already accounted for elsewhere, to subtract when computing
        the stock variation so it isn't double-counted (e.g. location-to-location
        reclassification entries).
        """
        return []

    def _format_accrual_data(self, accrual_data_by_type):
        """ Format `res.company._get_accrual_data`'s preview output for display.

        :return: (accrual display data or False, pending_cogs_vals)
        """
        company = self.env.company
        accrual_labels = {
            'bills_to_receive': self.env._("Bills to Receive"),
            'billed_not_received': self.env._("Billed Not Received"),
            'invoices_to_issue': self.env._("Invoices to be Issued"),
            'invoiced_not_delivered': self.env._("Invoiced Not Delivered"),
            'inventory_valuation': self.env._("Inventory Valuation"),
        }

        def _line_vals(display_name, account_id, value):
            return {
                'display_name': display_name,
                'account_id': account_id,
                'debit': value if value > 0 else 0,
                'credit': -value if value < 0 else 0,
            }

        def _amount_by_account(vals_list):
            amount_by_account = defaultdict(float)
            for vals in vals_list:
                if company.currency_id.is_zero(vals['balance']):
                    continue
                account = self.env['account.account'].browse(vals['account_id'])
                amount_by_account[account] += vals['balance']
            return amount_by_account

        def _type_line(label, amount_by_account, accrual_type=False):
            total = sum(amount_by_account.values()) if len(amount_by_account) > 1 else 0
            type_line = _line_vals(label, False, total)
            type_line['lines'] = [
                _line_vals(account.display_name, account.id, amount)
                for account, amount in amount_by_account.items()
            ]
            if accrual_type:
                type_line['accrual_type'] = accrual_type
            return type_line

        accrual_data = {
            'label': self.env._("Accruals"),
            'value': 0,
            'lines': [],
        }
        pending_cogs_vals = []
        inventory_amount_by_account = defaultdict(float)

        for accrual_type, entry in accrual_data_by_type.items():
            pending_cogs_vals += entry['cogs_vals']

            for account, amount in _amount_by_account(entry['inventory_vals']).items():
                inventory_amount_by_account[account] += amount

            type_valuation_amount_by_account = _amount_by_account(entry['accrual_vals'])
            if not type_valuation_amount_by_account:
                continue
            accrual_data['lines'].append(_type_line(accrual_labels[accrual_type], type_valuation_amount_by_account, accrual_type))

        if inventory_amount_by_account:
            accrual_data['lines'].append(_type_line(accrual_labels['inventory_valuation'], inventory_amount_by_account))

        if not accrual_data['lines']:
            return False, pending_cogs_vals
        accrual_data['value'] = sum(inventory_amount_by_account.values())
        return accrual_data, pending_cogs_vals
