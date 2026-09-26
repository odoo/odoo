from collections import defaultdict
from datetime import datetime, time

from odoo import _, fields, models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = "res.company"

    account_production_wip_account_id = fields.Many2one('account.account', string='Production WIP Account', check_company=True)
    account_production_wip_overhead_account_id = fields.Many2one('account.account', string='Production WIP Overhead Account', check_company=True)
    cost_method = fields.Selection(
        selection_add=[('fifo', "First In First Out (FIFO)")],
        ondelete={'fifo': 'set default'},
    )

    def write(self, vals):
        companies = self.filtered(lambda c: c.cost_method != vals['cost_method']) if 'cost_method' in vals else []
        res = super().write(vals)
        for company in companies:
            products = self.env['product.product'].with_company(company).search([
                ('is_storable', '=', True),
                '|',
                    ('categ_id', '=', False),
                    ('categ_id.property_cost_method', '=', False)
            ])
            last_closing_date = company._get_last_closing_date()
            products._correct_inventory_valuation(last_closing_date)
        return res

    def use_stock_account(self):
        # OVERRIDE: real/physical stock valuation is available.
        return True

    def get_inventory_value(self, at_date=None):
        # OVERRIDE: use the real valuation computed from stock moves/quants instead of the
        # `qty_available * standard_price` approximation used when stock isn't installed.
        self.ensure_one()
        value_by_account: dict = defaultdict(float)
        accounts_by_product = self.with_context(prefetch_fields=False)._get_accounts_by_product(at_date)
        for product, accounts in accounts_by_product.items():
            account = accounts['valuation']
            if not account:
                continue
            product_value = product.with_context(to_date=at_date).total_value
            value_by_account[account] += product_value
        return value_by_account

    def _get_inventory_valuation_products(self, date):
        # OVERRIDE: properly scope `qty_available` to valued internal locations (and to the
        # given date) rather than the plain field value.
        # sudo: qty_available expands kit BoMs (mrp.bom) which accounting users cannot read.
        # Kits are never valued on their own, so restrict to the valuation product domain
        # and skip the kit BoM expansion that qty_available would otherwise trigger.
        self.ensure_one()
        valued_product_context = self.env['product.product'].sudo().with_company(self).with_context(
            skip_kit_qty_available=True,
        )._with_valuation_context()
        if date:
            valued_product_context = valued_product_context.with_context(at_date=date, to_date=date)
        return valued_product_context.search(self._get_inventory_valuation_products_domain())

    def _get_extra_closing_aml_vals(self, at_date):
        # OVERRIDE: also account for location-to-location reclassification entries.
        return self._get_location_valuation_vals(at_date)

    def _get_closing_move_extra_vals(self, at_date):
        vals = super()._get_closing_move_extra_vals(at_date)
        vals['closing_datetime'] = datetime.combine(at_date, time.max) if at_date else fields.Datetime.now()
        return vals

    def _get_closing_date_field(self):
        return 'closing_datetime'

<<<<<<< e264fedcb3dbc4d2e2d3511ff86f4dd104e63228
    def _get_last_closing_date(self):
        closing = self._get_last_closing_move()
        if not closing:
            return datetime.min
        return closing.closing_datetime
||||||| 9b1d65acc28ea8af10bb9d8e3da535cc503097b2
        vals_list = self._get_continental_realtime_variation_vals(accounts_by_product, at_date, aml_vals_list)
        if vals_list:
            aml_vals_list += vals_list
        return aml_vals_list

    @api.model
    def _cron_post_stock_valuation(self):
        periods = ['daily']
        if fields.Date.today() == fields.Date.today() + relativedelta(day=31):
            periods.append('monthly')
        domain = Domain([
            ('inventory_period', 'in', periods),
            ('inventory_valuation', '!=', 'real_time'),
        ])
        companies = self.env['res.company'].search(domain)
        for company in companies:
            company.with_context(closing_cron=True).action_close_stock_valuation(auto_post=True)

    def _get_valuation_product_domain(self):
        return [('is_storable', '=', True)]

    def _get_accounts_by_product(self, products=None):
        if not products:
            products = self.env['product.product'].with_company(self).search_fetch(
                self._get_valuation_product_domain(), ['categ_id'],
            )

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
=======
        vals_list = self._get_continental_realtime_variation_vals(accounts_by_product, at_date, aml_vals_list)
        if vals_list:
            aml_vals_list += vals_list
        return aml_vals_list

    @api.model
    def _cron_post_stock_valuation(self):
        periods = ['daily']
        if fields.Date.today() == fields.Date.today() + relativedelta(day=31):
            periods.append('monthly')
        domain = Domain([
            ('inventory_period', 'in', periods),
        ])
        companies = self.env['res.company'].search(domain)
        for company in companies:
            try:
                company.with_context(closing_cron=True).action_close_stock_valuation(auto_post=True)
            except UserError:
                continue

    def _get_valuation_product_domain(self):
        return [('is_storable', '=', True)]

    def _get_accounts_by_product(self, products=None):
        if not products:
            products = self.env['product.product'].with_company(self).search_fetch(
                self._get_valuation_product_domain(), ['categ_id'],
            )

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
>>>>>>> 26d8f1fefcf4b0e2ee2534e35e4eaee59271ba34

    def _get_location_valuation_vals(self, at_date=None, location_domain=False):
        """ Reclassification entries between stock locations with their own valuation account. """
        location_domain = Domain.AND([
            location_domain or [],
            [('valuation_account_id', '!=', False)],
            [('company_id', '=', self.id)],
        ])
        amls_vals_list = []
        valued_location = self.env['stock.location'].search(location_domain)
        last_closing_date = self._get_last_closing_date()
        moves_base_domain = Domain([
            ('product_id.is_storable', '=', True),
            ('product_id.valuation', '=', 'periodic')
        ])
        if last_closing_date:
            moves_base_domain &= Domain([('date', '>', last_closing_date)])
        if at_date:
            moves_base_domain &= Domain([('date', '<=', at_date)])
        moves_in_domain = Domain([
            ('is_out', '=', True),
            ('company_id', '=', self.id),
            ('location_dest_id', 'in', valued_location.ids),
        ]) & moves_base_domain
        moves_in_by_location = self.env['stock.move']._read_group(
            moves_in_domain,
            ['location_dest_id', 'product_category_id'],
            ['value:sum'],
        )
        moves_out_domain = Domain([
            ('is_in', '=', True),
            ('company_id', '=', self.id),
            ('location_id', 'in', valued_location.ids),
        ]) & moves_base_domain
        moves_out_by_location = self.env['stock.move']._read_group(
            moves_out_domain,
            ['location_id', 'product_category_id'],
            ['value:sum'],
        )
        account_balance = defaultdict(float)
        for location, category, value in moves_in_by_location:
            stock_valuation_acc = category.property_stock_valuation_account_id or self.account_stock_valuation_id
            account_balance[location.valuation_account_id, stock_valuation_acc] += value

        for location, category, value in moves_out_by_location:
            stock_valuation_acc = category.property_stock_valuation_account_id or self.account_stock_valuation_id
            account_balance[location.valuation_account_id, stock_valuation_acc] -= value

        for (location_account, stock_account), balance in account_balance.items():
            if balance == 0:
                continue
            amls_vals = self._prepare_inventory_aml_vals(
                location_account,
                stock_account,
                balance,
                _('Closing: Location Reclassification - [%(account)s]', account=location_account.display_name),
            )
            amls_vals_list += amls_vals
        return amls_vals_list
