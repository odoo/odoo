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

        report_data = {
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'ending_stock': ending_stock,
            'initial_balance': initial_balance,
        }

        # Accruals have a stock valuation counterpart, so they modify the inventory valuation
        # account balance and must be computed before it.
        accrual, accrual_valuation_aml_vals = self._get_accrual_data(date=date)
        if accrual:
            account_ids.update(self._get_line_account_ids(accrual['lines']))
            report_data['accrual'] = accrual

        extra_aml_vals_list = self._get_extra_stock_valuation_aml_vals(date)
        if company.use_stock_account():
            # Real/physical stock valuation available (`stock_account` installed): `Ending Stock`
            # already independently reflects it, so net the accrual's stock-valuation
            # counterpart out of Stock Variation below instead, to avoid double-counting it.
            extra_aml_vals_list += accrual_valuation_aml_vals
        else:
            # No independent stock valuation: `Ending Stock` is only ever as accurate as the
            # accounting data, so fold the accrual's stock-valuation counterpart into it
            # directly instead of netting it against a Stock Variation that can't reflect it.
            for vals in accrual_valuation_aml_vals:
                ending_stock['value'] += vals['balance']
                ending_stock['lines_by_account_id'][vals['account_id']]['value'] += vals['balance']
                account_ids.add(vals['account_id'])

        stock_valuation_account_vals = company.with_context(inventory_data=inventory_data)._get_stock_valuation_account_vals(
            date, extra_aml_vals_list)

        stock_variation = {
            'label': self.env._("Stock Variation"),
            'value': 0,
        }
        lines_by_account_id = defaultdict(float)
        for vals in stock_valuation_account_vals:
            account_ids.add(vals['account_id'])
            stock_variation['value'] += vals['balance']
            lines_by_account_id[vals['account_id']] += vals['balance']
        stock_variation['lines'] = [{
            'account_id': account_id,
            'debit': balance if balance > 0 else 0,
            'credit': -balance if balance < 0 else 0,
        } for (account_id, balance) in lines_by_account_id.items()]

        accounts_read_data = self.env['account.account'].search_read(
            [('id', 'in', account_ids)],
            ['id', 'name', 'code', 'display_name']
        )
        report_data.update(
            accounts_by_id={acc_data['id']: acc_data for acc_data in accounts_read_data},
            stock_variation=stock_variation,
        )
        return report_data

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

    def _get_accrual_data(self, date=False):
        """ (accrual display data or False, valuation_aml_vals) """
        company = self.env.company
        accrual_entry_date = date or fields.Date.context_today(self)
        accrual_labels = {
            'bills_to_receive': self.env._("Bills to Receive"),
            'billed_not_received': self.env._("Billed Not Received"),
            'invoices_to_issue': self.env._("Invoices to be Issued"),
            'invoiced_not_delivered': self.env._("Invoiced Not Delivered"),
        }

        lines_by_key = {}
        valuation_amount_by_account = defaultdict(float)
        for accrual_type, candidate_lines in company._get_accrual_candidate_lines(date=date).items():
            if not candidate_lines:
                continue

            # The accrual amount itself: each line's own "amount left to invoice" already
            # is that, in its order's currency; no move-vals construction needed for it.
            total = sum(
                line.order_id.currency_id._convert(line.amount_to_invoice_at_date, company.currency_id, company)
                for line in candidate_lines
            )

            # The inventory part (perpetual-valuation adjustment for real_time, storable
            # products): only the wizard knows how to compute it.
            wizard = self.env['account.accrued.orders.wizard'].with_context(
                active_model=candidate_lines._name,
                active_ids=candidate_lines.ids,
                accrual_entry_date=fields.Date.to_string(accrual_entry_date),
                accrual_allow_mixed_currencies=True,
            ).new({
                'company_id': company.id,
                'date': accrual_entry_date,
            })
            is_purchase = candidate_lines._name == 'purchase.order.line'
            __, main_counterpart_vals_list = wizard._get_accrual_main_line_vals(
                candidate_lines, is_purchase, accrual_entry_date)
            inventory_vals_list, __ = wizard._get_accrual_cogs_line_vals(
                candidate_lines, is_purchase, accrual_entry_date)

            # The stock-valuation side: nets against Stock Variation, so aggregated globally
            # under "Total Inventory Valuation" regardless of which accrual type it comes from.
            for vals in inventory_vals_list:
                amount = vals['debit'] - vals['credit']
                if company.currency_id.is_zero(amount):
                    continue
                account = self.env['account.account'].browse(vals['account_id'])
                valuation_amount_by_account[account] += amount

            # Its accrual counterpart (the bills_to_receive/billed_not_received/
            # invoices_to_issue/invoiced_not_delivered account(s) actually posted to, which can
            # vary by product/category): shown nested under this accrual type instead.
            type_valuation_amount_by_account = defaultdict(float)
            for vals in main_counterpart_vals_list:
                amount = vals['debit'] - vals['credit']
                if company.currency_id.is_zero(amount):
                    continue
                account = self.env['account.account'].browse(vals['account_id'])
                type_valuation_amount_by_account[account] += amount

            if company.currency_id.is_zero(total) and not type_valuation_amount_by_account:
                continue
            lines_by_key[accrual_type] = {
                'label': accrual_labels[accrual_type],
                # `_get_aml_vals` doesn't flip the balance for purchase (unlike sale), so the
                # bills_to_receive/billed_not_received counterpart is credited/debited the
                # opposite way 'total' > 0 would naively suggest: flip it so the debit/credit
                # column this ends up displayed under matches that real entry.
                'value': -total if is_purchase else total,
                'valuation_amount_by_account': type_valuation_amount_by_account,
            }

        account_ids = {
            account.id
            for line in lines_by_key.values()
            for account in line['valuation_amount_by_account']
        }
        account_ids |= {account.id for account in valuation_amount_by_account}
        display_name_by_account_id = {
            account.id: account.display_name
            for account in self.env['account.account'].browse(account_ids)
        }

        def _line_vals(display_name, account_id, value):
            # No 'value' key: the debit/credit split must drive the display,
            # or the signed value overrides it (StockValuationReportLine.formattedValue).
            return {
                'display_name': display_name,
                'account_id': account_id,
                'debit': value if value > 0 else 0,
                'credit': -value if value < 0 else 0,
            }

        accrual_data = {
            'label': self.env._("Accruals"),
            'value': 0,
            'lines': [],
        }
        for line in lines_by_key.values():
            # The accrual entry's expense-side counterpart, nested under this accrual type
            # rather than shown disconnected from the type it comes from.
            type_line = _line_vals(line['label'], False, line['value'])
            type_line['lines'] = [
                _line_vals(display_name_by_account_id[account.id], account.id, amount)
                for account, amount in line['valuation_amount_by_account'].items()
            ]
            accrual_data['lines'].append(type_line)

        # The "Accruals" section's own total only reflects the inventory valuation impact (the
        # part netted out of Stock Variation): the accrual types' own amounts (above) are shown
        # for context but land on AP/AR and income/expense accounts, not inventory ones.
        for account, amount in valuation_amount_by_account.items():
            if company.currency_id.is_zero(amount):
                continue
            accrual_data['value'] += amount

        if valuation_amount_by_account and not company.currency_id.is_zero(accrual_data['value']):
            # `_line_vals` (not 'value'): the debit/credit split must drive which column this
            # lands in, same as its sibling accrual-type lines.
            total_line = _line_vals(self.env._("Total Inventory Valuation"), False, accrual_data['value'])
            total_line['lines'] = [
                _line_vals(display_name_by_account_id[account.id], account.id, amount)
                for account, amount in valuation_amount_by_account.items()
                if not company.currency_id.is_zero(amount)
            ]
            accrual_data['lines'].append(total_line)

        valuation_aml_vals = [
            {'account_id': account.id, 'balance': amount}
            for account, amount in valuation_amount_by_account.items()
            if not company.currency_id.is_zero(amount)
        ]

        # Lines can still net out to nothing to show (e.g. two order lines
        # offsetting each other); valuation_aml_vals is still needed either way.
        if not accrual_data['lines']:
            return False, valuation_aml_vals
        return accrual_data, valuation_aml_vals
