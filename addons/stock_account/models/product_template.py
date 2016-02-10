# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    property_valuation = fields.Selection([
        ('manual_periodic', 'Periodic (manual)'),
        ('real_time', 'Perpetual (automated)')],
        string='Inventory Valuation', copy=True,
        company_dependent=True, default='manual_periodic',
        help="If perpetual valuation is enabled for a product, the system will automatically create journal entries corresponding to stock moves, with product price as specified by the 'Costing Method'" \
             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products.")
    valuation = fields.Char(compute='_compute_valuation_type', store=True)
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('average', 'Average Price'),
        ('real', 'Real Price')],
        company_dependent=True,
        help="""Standard Price: The cost price is manually updated at the end of a specific period (usually once a year).
                Average Price: The cost price is recomputed at each incoming shipment and used for the product valuation.
                Real Price: The cost price displayed is the price of the last outgoing product (will be use in case of inventory loss for example).""",
        string="Costing Method", copy=True)
    cost_method = fields.Char(compute='_compute_cost_method', store=True)
    property_stock_account_input = fields.Many2one(
        'account.account',
        string='Stock Input Account',
        domain=[('deprecated', '=', False)],
        company_dependent=True,
        help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
             "there is a specific valuation account set on the source location. When not set on the product, the one from the product category is used.")
    property_stock_account_output = fields.Many2one(
        'account.account',
        string='Stock Output Account',
        domain=[('deprecated', '=', False)],
        company_dependent=True,
        help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
             "there is a specific valuation account set on the destination location. When not set on the product, the one from the product category is used.")

    @api.depends('property_cost_method')
    def _compute_cost_method(self):
        for product in self:
            product.cost_method = product.property_cost_method or product.categ_id.property_cost_method

    @api.depends('property_valuation')
    def _compute_valuation_type(self):
        for product in self:
            product.valuation = product.property_valuation or product.categ_id.property_valuation

    @api.onchange('type')
    def _onchange_type_valuation(self):
        if self.type != 'product':
            self.valuation = 'manual_periodic'

    @api.model
    def create(self, vals):
        if vals.get('cost_method'):
            vals['property_cost_method'] = vals['cost_method']
        if vals.get('valuation'):
            vals['property_valuation'] = vals['valuation']
        return super(ProductTemplate, self).create(vals)

    @api.multi
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self)._get_product_accounts()
        accounts.update({
            'stock_input': self.property_stock_account_input or self.categ_id.property_stock_account_input_categ_id,
            'stock_output': self.property_stock_account_output or self.categ_id.property_stock_account_output_categ_id,
            'stock_valuation': self.categ_id.property_stock_valuation_account_id,
        })
        return accounts

    @api.multi
    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        self.ensure_one()
        accounts = super(ProductTemplate, self).get_product_accounts(fiscal_pos=fiscal_pos)
        accounts['stock_journal'] = self.categ_id.property_stock_journal
        return accounts

    def do_change_standard_price(self, new_price, account_id):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        AccountMove = self.env['account.move']
        locations = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', self.env.user.company_id.id)])
        for prod_temp in self:
            accounts = prod_temp.get_product_accounts()
            for location in locations:
                product = prod_temp.with_context(location=location.id, compute_child=False)
                diff = product.standard_price - new_price
                if not diff:
                    raise UserError(_("No difference between standard price and new price!"))
                for prod_variant in product.product_variant_ids.filtered('qty_available'):
                    qty = prod_variant.qty_available
                    # Accounting Entries
                    amount_diff = abs(diff * qty)
                    if diff * qty > 0:
                        debit_account_id = account_id
                        credit_account_id = accounts['stock_valuation'].id
                    else:
                        debit_account_id = accounts['stock_valuation'].id
                        credit_account_id = account_id

                    lines = [(0, 0, {'name': _('Standard Price changed'),
                                     'account_id': debit_account_id,
                                     'debit': amount_diff,
                                     'credit': 0,
                                     'product_id': product.id}),
                             (0, 0, {'name': _('Standard Price changed'),
                                     'account_id': credit_account_id,
                                     'debit': 0,
                                     'credit': amount_diff,
                                     'product_id': product.id})]
                    move_vals = {
                        'journal_id': accounts['stock_journal'].id,
                        'company_id': location.company_id.id,
                        'line_ids': lines}
                    AccountMove.create(move_vals).post()
            prod_temp.standard_price = new_price
        return True
