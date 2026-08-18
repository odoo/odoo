from collections import defaultdict
from datetime import datetime, time

from odoo import _, fields, models
from odoo.fields import Domain
from odoo.addons.base.models.res_company import company_default_for


class ResCompany(models.Model):
    _inherit = "res.company"

    account_production_wip_account_id = fields.Many2one('account.account', string='Production WIP Account', check_company=True)
    account_production_wip_overhead_account_id = fields.Many2one('account.account', string='Production WIP Overhead Account', check_company=True)

    cost_method = fields.Selection(
        string="Cost Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        **company_default_for('cost_method', 'product.category', 'property_cost_method'),
        default='standard',
        required=True,
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

    def get_inventory_value(self, accounts_by_product=None, at_date=None):
        # OVERRIDE: use the real valuation computed from stock moves/quants instead of the
        # `qty_available * standard_price` approximation used when stock isn't installed.
        self.ensure_one()
        value_by_account: dict = defaultdict(float)
        if not accounts_by_product:
            accounts_by_product = self.with_context(prefetch_fields=False)._get_accounts_by_product()
        for product, accounts in accounts_by_product.items():
            account = accounts['valuation']
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

    def _get_last_closing_date(self):
        closing = self._get_last_closing_move()
        if not closing:
            return datetime.min
        return closing.closing_datetime

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
