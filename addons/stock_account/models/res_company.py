from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.fields import Domain
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    account_stock_journal_id = fields.Many2one('account.journal', string='Stock Journal', check_company=True)

    account_stock_valuation_id = fields.Many2one('account.account', string='Stock Valuation Account', check_company=True)

    account_production_wip_account_id = fields.Many2one('account.account', string='Production WIP Account', check_company=True)
    account_production_wip_overhead_account_id = fields.Many2one('account.account', string='Production WIP Overhead Account', check_company=True)

    inventory_period = fields.Selection(
        string='Inventory Period',
        selection=[
            ('manual', 'Manual'),
            ('daily', 'Daily'),
            ('monthly', 'Monthly'),
        ],
        default='manual',
        required=True)

    inventory_valuation = fields.Selection(
        string='Valuation',
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        default='periodic',
    )

    cost_method = fields.Selection(
        string="Cost Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        default='standard',
        required=True,
    )

    def action_close_stock_valuation(self, auto_post=False):
        self.ensure_one()
        aml_vals_list = self._action_close_stock_valuation()

        if not aml_vals_list:
            # No account moves to create, so nothing to display.
            raise UserError(_("Nothing to close"))

        moves_vals = {
            'journal_id': self.account_stock_journal_id.id,
            'date': fields.Date.today(),
            'ref': _('Stock Closing'),
            'line_ids': [Command.create(aml_vals) for aml_vals in aml_vals_list],
        }
        account_move = self.env['account.move'].create(moves_vals)

        if auto_post:
            account_move._post()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Items"),
            'res_model': 'account.move',
            'res_id': account_move.id,
            'views': [(False, 'form')],
        }

    def stock_value(self, accounts_by_product=None, at_date=None):
        self.ensure_one()
        value_by_account: dict = defaultdict(float)
        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()
        for product, accounts in accounts_by_product.items():
            account = accounts['valuation']
            product_value = product.with_context(to_date=at_date).total_value
            value_by_account[account] += product_value
        return value_by_account

    def stock_accounting_value(self, accounts_by_product=None, at_date=None):
        self.ensure_one()
        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()
        account_data = defaultdict(float)
        stock_valuation_accounts_ids = set()
        for dummy, accounts in accounts_by_product.items():
            stock_valuation_accounts_ids.add(accounts['valuation'].id)
        stock_valuation_accounts = self.env['account.account'].browse(stock_valuation_accounts_ids)
        domain = Domain([
            ('account_id', 'in', stock_valuation_accounts.ids),
            ('company_id', '=', self.id),
            ('parent_state', '=', 'posted'),
        ])
        if at_date:
            domain = domain & Domain([('date', '<=', at_date)])
        amls_group = self.env['account.move.line']._read_group(domain, ['account_id'], ['balance:sum'])
        for account, balance in amls_group:
            account_data[account] += balance
        return account_data

    def _action_close_stock_valuation(self):
        aml_vals_list = []
        accounts_by_product = self._get_accounts_by_product()

        vals_list = self._get_location_valuation_vals()
        if vals_list:
            # Needed directly since it will impact the accounting stock valuation.
            aml_vals_list += vals_list

        vals_list = self._get_stock_valuation_account_vals(accounts_by_product, aml_vals_list)
        if vals_list:
            aml_vals_list += vals_list

        vals_list = self._get_continental_realtime_variation_vals(accounts_by_product, aml_vals_list)
        if vals_list:
            aml_vals_list += vals_list
        return aml_vals_list

    @api.model
    def _cron_post_stock_valuation(self):
        domain = Domain([('inventory_period', '=', 'daily')])
        if fields.Date.today() == fields.Date.today() + relativedelta(day=31):
            domain = domain & Domain([('inventory_period', '=', 'monthly')])
        companies = self.env['res.company'].search(domain)
        for company in companies:
            company.action_close_stock_valuation(auto_post=True)

    def _get_accounts_by_product(self, products=None):
        if not products:
            products = self.env['product.product'].with_company(self).search([('is_storable', '=', True)])

        accounts_by_product = {}
        for product in products:
            accounts = product._get_product_accounts()
            accounts_by_product[product] = {
                'valuation': accounts['stock_valuation'],
                'variation': accounts['stock_variation'],
                'expense': accounts['expense'],
            }
        return accounts_by_product

    @api.model
    def _get_extra_balance(self, vals_list=None):
        extra_balance = defaultdict(float)
        if not vals_list:
            return extra_balance
        for vals in vals_list:
            extra_balance[vals['account_id']] += (vals['debit'] - vals['credit'])
        return extra_balance

    def _get_location_valuation_vals(self):
        amls_vals_list = []
        valued_location = self.env['stock.location'].search([('valuation_account_id', '!=', False)])

        moves_in_by_location = self.env['stock.move']._read_group(
            [('is_out', '=', True), ('location_dest_id', 'in', valued_location.ids)],
            ['location_dest_id'],
            ['value:sum'],
        )
        moves_out_by_location = self.env['stock.move']._read_group(
            [('is_in', '=', True), ('location_id', 'in', valued_location.ids)],
            ['location_id'],
            ['value:sum'],
        )
        account_balance = defaultdict(float)
        incoming_value_by_location = dict(moves_in_by_location)
        outgoing_value_by_location = dict(moves_out_by_location)
        locations = incoming_value_by_location.keys() | outgoing_value_by_location.keys()
        for location in locations:
            # TODO: It would be better to replay the period to get the exact correct value.
            inventory_value = incoming_value_by_location.get(location, 0.0) - outgoing_value_by_location.get(location, 0.0)
            account_balance[location.valuation_account_id] += inventory_value
        current_valuation = self.env['account.move.line']._read_group(
            domain=[
                ('account_id', 'in', valued_location.valuation_account_id.ids),
                ('company_id', '=', self.id),
                ('parent_state', '=', 'posted'),
            ],
            groupby=['account_id'],
            aggregates=['balance:sum'],
        )
        for account, balance in current_valuation:
            account_balance[account] -= balance
        for account, balance in account_balance.items():
            if balance == 0:
                continue
            amls_vals = self._prepare_inventory_aml_vals(
                account,
                self.account_stock_valuation_id,
                balance,
                _('Closing: Location Reclassification - [%(account)s]', account=account.display_name),
            )
            amls_vals_list += amls_vals
        return amls_vals_list

    def _get_stock_valuation_account_vals(self, accounts_by_product, extra_aml_vals_list=None):
        amls_vals_list = []
        if not accounts_by_product:
            return amls_vals_list

        extra_balance = self._get_extra_balance(extra_aml_vals_list)

        inventory_data = self.stock_value(accounts_by_product)
        accounting_data = self.stock_accounting_value(accounts_by_product)

        accounts = inventory_data.keys() | accounting_data.keys()
        for account in accounts:
            account_variation = False
            if account.account_stock_variation_id:
                account_variation = account.account_stock_variation_id
            if not account_variation and account.account_stock_expense_id:
                account_variation = account.account_stock_expense_id
            if not account_variation:
                continue
            balance = inventory_data.get(account, 0) - accounting_data.get(account, 0)
            balance -= extra_balance.get(account.id, 0)

            amls_vals = self._prepare_inventory_aml_vals(
                account,
                account_variation,
                balance,
                _('Closing: Stock Variation Global for company [%(company)s]', company=self.display_name),
            )
            amls_vals_list += amls_vals

        return amls_vals_list

    def _get_continental_realtime_variation_vals(self, accounts_by_product, extra_aml_vals_list=None):
        """ In continental perpetual the inventory variation is never posted.
        This method compute the variation for a period and post it.
        """
        if self.anglo_saxon_accounting:
            return []
        extra_balance = self._get_extra_balance(extra_aml_vals_list)

        fiscal_year_date_from = self.compute_fiscalyear_dates(fields.Date.today())['date_from']

        amls_vals_list = []
        accounting_data_today = self.stock_accounting_value(accounts_by_product)
        accounting_data_last_period = self.stock_accounting_value(accounts_by_product, at_date=fiscal_year_date_from)

        accounts = accounting_data_today.keys() | accounting_data_last_period.keys()

        for account in accounts:
            variation_acc = account.account_variation_id
            expense_acc = account.account_expense_id

            if not variation_acc or not expense_acc:
                continue

            balance_today = accounting_data_today.get(account, 0) - extra_balance[account]
            balance_last_period = accounting_data_last_period.get(account, 0)
            balance_over_period = balance_today - balance_last_period

            existing_balance = sum(self.env['account.move.line']._search([
                ('account_id', '=', variation_acc.id),
                ('company_id', '=', self.id),
                ('parent_state', '=', 'posted'),
            ]).mapped('balance'))

            amls_vals = self._prepare_inventory_aml_vals(
                expense_acc,
                variation_acc,
                balance_over_period - existing_balance,
                _('Closing: Stock Variation Over Period'),
            )
            amls_vals_list.append(amls_vals)

        return amls_vals_list

    def _prepare_inventory_aml_vals(self, debit_acc, credit_acc, balance, ref, product_id=False):
        if balance < 0:
            temp = credit_acc
            credit_acc = debit_acc
            debit_acc = temp
            balance = abs(balance)
        return [{
            'account_id': credit_acc.id,
            'name': ref,
            'debit': 0,
            'credit': balance,
            'product_id': product_id,
        }, {
            'account_id': debit_acc.id,
            'name': ref,
            'debit': balance,
            'credit': 0,
            'product_id': product_id,
        }]

    def _set_category_defaults(self):
        for company in self:
            self.env['ir.default'].set('product.category', 'property_valuation', company.inventory_valuation, company_id=company.id)
            self.env['ir.default'].set('product.category', 'property_cost_method', company.cost_method, company_id=company.id)
            self.env['ir.default'].set('product.category', 'property_stock_journal', company.account_stock_journal_id.id, company_id=company.id)
            self.env['ir.default'].set('product.category', 'property_stock_valuation_account_id', company.account_stock_valuation_id.id, company_id=company.id)
