from collections import defaultdict

from odoo import _, api, fields, models


class StockValuationReport(models.AbstractModel):
    _name = 'stock_account.stock.valuation.report'
    _description = 'Stock Valuation'

    @api.model
    def get_report_values(self, date=False):
        return {
            'data': self.with_context(allowed_company_ids=self.env.company.ids)._get_report_data(date=date),
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

        if date == fields.Date.context_today(self):
            date = False
        # PERF: only products holding stock contribute to the valuation. Match the
        # context used by total_value so qty_available scopes to valued internal locations.
        # Lot-valuated products are kept regardless because their value is summed from lots.
        # sudo: qty_available expands kit BoMs (mrp.bom) which accounting users cannot read.
        valued_product_context = self.env['product.product'].sudo().with_company(company)._with_valuation_context()
        if date:
            valued_product_context = valued_product_context.with_context(at_date=date, to_date=date)
        valued_products = valued_product_context.search([
            ('is_storable', '=', True),
            '|', ('qty_available', '!=', 0), ('lot_valuated', '=', True),
        ])
        accounts_by_product = company._get_accounts_by_product(products=valued_products)
        if not date:
            inventory_data = company.stock_value(accounts_by_product)
            accounting_data = company.stock_accounting_value(accounts_by_product)
        else:
            inventory_data = company.stock_value(accounts_by_product, at_date=date)
            accounting_data = company.stock_accounting_value(accounts_by_product, at_date=date)

        accounts = inventory_data.keys() | accounting_data.keys()
        account_ids = {acc.id for acc in accounts}

        initial_balance = {
            'label': _("Initial Balance"),
            'value': 0,
            'lines_by_account_id': defaultdict(lambda: {
                'value': 0,
            }),
        }
        ending_stock = {
            'label': _("Ending Stock"),
            'value': 0,
            'lines_by_account_id': defaultdict(lambda: {
                'value': 0,
            }),
        }

        # Compute Opening Balance values and Ending Stock values.
        for account in accounts:
            opening_balance = accounting_data.get(account, 0)
            ending_balance = inventory_data.get(account, 0)
            account_ids.add(account.id)
            if opening_balance:
                initial_balance['value'] += opening_balance
                initial_balance['lines_by_account_id'][account.id]['value'] += opening_balance
            if ending_balance:
                ending_stock['value'] += ending_balance
                ending_stock['lines_by_account_id'][account.id]['value'] += ending_balance

        # Get accounting data.
        location_valuation_vals = company._get_location_valuation_vals(
            date, location_domain=[('usage', '=', 'inventory')],
        )
        stock_valuation_account_vals = company.with_context(inventory_data=inventory_data)._get_stock_valuation_account_vals(
            accounts_by_product, date, company._get_location_valuation_vals(date))

        report_data = {
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'ending_stock': ending_stock,
            'initial_balance': initial_balance,
        }

        if self._must_include_inventory_loss():
            # Compute Inventory Loss values.
            inventory_loss = {
                'label': _("Inventory Loss"),
                'value': 0,
            }
            lines_by_account_id = defaultdict(lambda: {
                'debit': 0,
                'credit': 0,
            })
            for vals in location_valuation_vals:
                account_ids.add(vals['account_id'])
                inventory_loss['value'] -= vals['debit']
                lines_by_account_id[vals['account_id']]['debit'] += vals['debit']
                lines_by_account_id[vals['account_id']]['credit'] += vals['credit']
            inventory_loss['lines'] = [{
                'account_id': account_id,
                'debit': vals['debit'],
                'credit': vals['credit'],
            } for (account_id, vals) in lines_by_account_id.items()]
            report_data['inventory_loss'] = inventory_loss

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
            account_ids.add(vals['account_id'])
            stock_variation['value'] += vals['debit']
            lines_by_account_id[vals['account_id']]['debit'] += vals['debit']
            lines_by_account_id[vals['account_id']]['credit'] += vals['credit']
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

    def action_print_as_pdf(self):
        return

    def action_print_as_xlsx(self):
        return

    def _must_include_inventory_loss(self):
        return bool(self.env['stock.location'].search_count([
            ('usage', '=', 'inventory'),
            ('valuation_account_id', '!=', False),
        ], limit=1))
