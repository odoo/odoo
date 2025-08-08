from collections import defaultdict

from odoo import _, api, fields, models


class StockValuationReport(models.AbstractModel):
    _name = 'stock_account.stock.valuation.report'
    _description = 'Stock Valuation'

    @api.model
    def get_report_values(self, date=False):
        return {
            'data': self._get_report_data(date=date),
            'context': {},
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        doc = self._get_report_data()
        docs.append(self._include_pdf_specifics(doc, data))
        return {
            'doc_ids': docids,
            'doc_model': 'stock.valuation.report',
            'docs': docs,
        }

    def _get_report_data(self, date=False, product_category=False, warehouse=False):
        company = self.env.company
        # Check if date is a string instance
        if isinstance(date, str):
            date = fields.Date.from_string(date)

        if date == fields.Date.today():
            inventory_data = company.stock_value()
            accounting_data = company.stock_accounting_value()
        else:
            inventory_data = company.stock_value(at_date=date)
            accounting_data = company.stock_accounting_value(at_date=date)

        accounts = inventory_data.keys() | accounting_data.keys()
        accounts_by_id = {}

        accounts_lines = []
        initial_balance = {
            'label': _("Initial Balance"),
            'value': 0,
            'lines_by_account_id': defaultdict(lambda: {
                'value': 0,
                'accounts': [],
            }),
        }
        ending_stock = {
            'label': _("Ending Stock"),
            'value': 0,
            'lines_by_account_id': defaultdict(lambda: {
                'value': 0,
                'accounts': [],
            }),
        }

        # Compute Opening Balance values and Ending Stock values.
        for account in accounts:
            opening_balance = accounting_data.get(account, 0)
            ending_balance = inventory_data.get(account, 0)
            variation = ending_balance - opening_balance
            account_vals = account.read(['name', 'code', 'display_name'])[0]
            accounts_by_id[account.id] = account_vals
            account_line = {
                'account_id': account.id,
                'opening_balance': opening_balance,
                'ending_balance': ending_balance,
                'variation': variation,
            }
            accounts_lines.append(account_line)
            if opening_balance:
                initial_balance['value'] += opening_balance
                initial_balance['lines_by_account_id'][account.id]['value'] += opening_balance
                initial_balance['lines_by_account_id'][account.id]['accounts'].append(account_vals)
            if ending_balance:
                ending_stock['value'] += ending_balance
                ending_stock['lines_by_account_id'][account.id]['value'] += ending_balance
                ending_stock['lines_by_account_id'][account.id]['accounts'].append(account_vals)

        # Get accounting data.
        accounts_by_product = company._get_accounts_by_product()
        location_valuation_vals = company._get_location_valuation_vals(
            location_domain=[('usage', '=', 'inventory')]
        )
        stock_valuation_account_vals = company._get_stock_valuation_account_vals(accounts_by_product, location_valuation_vals)

        # Compute Inventory Loss values.
        inventory_loss = {
            'label': _("Inventory Loss"),
            'value': 0,
        }
        lines_by_account_id = defaultdict(lambda: {
            'debit': 0,
            'credit': 0,
            'lines': [],
        })
        for vals in location_valuation_vals:
            account = self.env['account.account'].browse(vals['account_id'])
            account_vals = account.read(['name', 'code', 'display_name'])[0]
            accounts_by_id[account.id] = account_vals
            inventory_loss['value'] -= vals['debit']
            lines_by_account_id[account.id]['debit'] += vals['debit']
            lines_by_account_id[account.id]['credit'] += vals['credit']
            lines_by_account_id[account.id]['lines'].append(vals)
        inventory_loss['lines'] = [{
            'account_id': account_id,
            'debit': vals['debit'],
            'credit': vals['credit'],
        } for (account_id, vals) in lines_by_account_id.items()]

        # Compute Stock Variation values.
        stock_variation = {
            'label': _("Stock Variation"),
            'value': 0,
        }
        lines_by_account_id = defaultdict(lambda: {
            'debit': 0,
            'credit': 0,
            'lines': [],
        })
        for vals in stock_valuation_account_vals:
            account = self.env['account.account'].browse(vals['account_id'])
            account_vals = account.read(['name', 'code', 'display_name'])[0]
            accounts_by_id[account.id] = account_vals
            stock_variation['value'] += vals['debit']
            lines_by_account_id[account.id]['debit'] += vals['debit']
            lines_by_account_id[account.id]['credit'] += vals['credit']
            lines_by_account_id[account.id]['lines'].append({
                **vals,
                'account_id': account.id,
            })
        stock_variation['lines'] = [{
            'account_id': account_id,
            'debit': vals['debit'],
            'credit': vals['credit'],
        } for (account_id, vals) in lines_by_account_id.items()]

        data = {
            'accounts_by_id': accounts_by_id,
            'accounts_lines': accounts_lines,
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'ending_stock': ending_stock,
            'initial_balance': initial_balance,
            'inventory_loss': inventory_loss,
            'stock_variation': stock_variation,
        }
        return data

    def action_print_as_pdf(self):
        return

    def action_print_as_xlsx(self):
        return
