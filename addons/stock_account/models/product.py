# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.addons import decimal_precision as dp



class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    property_valuation = fields.Selection([
        ('manual_periodic', 'Periodic (manual)'),
        ('real_time', 'Perpetual (automated)')], string='Inventory Valuation',
        company_dependent=True, copy=True, default='manual_periodic',
        help="If perpetual valuation is enabled for a product, the system will automatically create journal entries corresponding to stock moves, with product price as specified by the 'Costing Method'" \
             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products.")
    valuation = fields.Char(compute='_compute_valuation_type', inverse='_set_valuation_type')
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', '(financial) FIFO'),
        ('average', 'AVCO')], string='Costing Method',
        company_dependent=True, copy=True,
        help="""Standard Price: The cost price is manually updated at the end of a specific period (usually once a year).
                Average Price: The cost price is recomputed at each incoming shipment and used for the product valuation.
                Real Price: The cost price displayed is the price of the last outgoing product (will be use in case of inventory loss for example).""")
    cost_method = fields.Char(compute='_compute_cost_method', inverse='_set_cost_method')
    property_stock_account_input = fields.Many2one(
        'account.account', 'Stock Input Account',
        company_dependent=True, domain=[('deprecated', '=', False)],
        help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
             "there is a specific valuation account set on the source location. When not set on the product, the one from the product category is used.")
    property_stock_account_output = fields.Many2one(
        'account.account', 'Stock Output Account',
        company_dependent=True, domain=[('deprecated', '=', False)],
        help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
             "there is a specific valuation account set on the destination location. When not set on the product, the one from the product category is used.")
    average_price = fields.Float(
        'Average Cost', compute='_compute_average_price',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help="Average cost of the product, in the default unit of measure of the product.")

    @api.multi
    def _compute_average_price(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.average_price = template.product_variant_ids.average_price
        for template in (self - unique_variants):
            template.average_price = 0.0


    @api.one
    @api.depends('property_valuation', 'categ_id.property_valuation')
    def _compute_valuation_type(self):
        self.valuation = self.property_valuation or self.categ_id.property_valuation

    @api.one
    def _set_valuation_type(self):
        return self.write({'property_valuation': self.valuation})

    @api.one
    @api.depends('property_cost_method', 'categ_id.property_cost_method')
    def _compute_cost_method(self):
        self.cost_method = self.property_cost_method or self.categ_id.property_cost_method

    def _is_cost_method_standard(self):
        return self.property_cost_method == 'standard'

    @api.one
    def _set_cost_method(self):
        return self.write({'property_cost_method': self.cost_method})

    @api.onchange('type')
    def onchange_type_valuation(self):
        # TO REMOVE IN MASTER
        pass

    @api.multi
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self)._get_product_accounts()
        res = self._get_asset_accounts()
        accounts.update({
            'stock_input': res['stock_input'] or self.property_stock_account_input or self.categ_id.property_stock_account_input_categ_id,
            'stock_output': res['stock_output'] or self.property_stock_account_output or self.categ_id.property_stock_account_output_categ_id,
            'stock_valuation': self.categ_id.property_stock_valuation_account_id or False,
        })
        return accounts

    @api.multi
    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self).get_product_accounts(fiscal_pos=fiscal_pos)
        accounts.update({'stock_journal': self.categ_id.property_stock_journal or False})
        return accounts


class ProductProduct(models.Model):
    _inherit = 'product.product'

    average_price = fields.Float(
        'Average Cost', 
        digits=dp.get_precision('Product Price'),
        groups="base.group_user",
        compute='_compute_average_price',
        help="Calculated average cost")
    stock_value = fields.Float(
        'Value', compute='_compute_stock_value')

    @api.onchange('type')
    def onchange_type_valuation(self):
        # TO REMOVE IN MASTER
        pass

    @api.multi
    def do_change_standard_price(self, new_price, account_id):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        AccountMove = self.env['account.move']

        locations = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', self.env.user.company_id.id)])

        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}

        for location in locations:
            for product in self.with_context(location=location.id, compute_child=False).filtered(lambda r: r.valuation == 'real_time'):
                diff = product.standard_price - new_price
                if float_is_zero(diff, precision_rounding=product.currency_id.rounding):
                    raise UserError(_("No difference between standard price and new price!"))
                if not product_accounts[product.id].get('stock_valuation', False):
                    raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
                qty_available = product.qty_available
                if qty_available:
                    # Accounting Entries
                    if diff * qty_available > 0:
                        debit_account_id = account_id
                        credit_account_id = product_accounts[product.id]['stock_valuation'].id
                    else:
                        debit_account_id = product_accounts[product.id]['stock_valuation'].id
                        credit_account_id = account_id

                    move_vals = {
                        'journal_id': product_accounts[product.id]['stock_journal'].id,
                        'company_id': location.company_id.id,
                        'line_ids': [(0, 0, {
                            'name': _('Standard Price changed  - %s') % (product.display_name),
                            'account_id': debit_account_id,
                            'debit': abs(diff * qty_available),
                            'credit': 0,
                        }), (0, 0, {
                            'name': _('Standard Price changed  - %s') % (product.display_name),
                            'account_id': credit_account_id,
                            'debit': 0,
                            'credit': abs(diff * qty_available),
                        })],
                    }
                    move = AccountMove.create(move_vals)
                    move.post()

        self.write({'standard_price': new_price})
        return True

    def _get_latest_cumulated_value(self, not_move=False):
        self.ensure_one()
        # TODO: only filter on IN and OUT stock.move
        domain = [
            ('product_id', '=', self.id),
            ('state', '=', 'done'),
            ]
        if not_move:
            domain += [('id', '!=', not_move.id)]
        latest = self.env['stock.move'].search(domain, order='date desc, id desc', limit=1)
        if not latest:
            return 0.0
        return latest.cumulated_value

    def _get_candidates_out_move(self):
        self.ensure_one()
        # TODO: filter at start of period
        candidates = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('location_dest_id.usage', 'not in', ('transit', 'internal')),
            ('location_id.usage', 'in', ('transit', 'internal')),
            ('remaining_qty', '>', 0),
            ('state', '=', 'done')
        ], order='date, id') #TODO: case
        return candidates

    def _get_candidates_move(self):
        self.ensure_one()
        # TODO: filter at start of period
        candidates = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('location_dest_id.usage', 'in', ('transit', 'internal')),
            ('location_id.usage', 'not in', ('transit', 'internal')),
            ('remaining_qty', '>', 0),
            ('state', '=', 'done')
        ], order='date, id') #TODO: case where 
        return candidates

    @api.multi
    def _compute_average_price(self):
        for product in self:
            if product.qty_available > 0:
                last_cumulated_value = product._get_latest_cumulated_value()
                product.average_price = last_cumulated_value / product.qty_available
            else:
                product.average_price = 0
    
    @api.multi
    def _compute_stock_value(self):
        for product in self:
            if product.cost_method == 'standard':
                product.stock_value = product.standard_price * product.qty_available
            elif product.cost_method == 'average':
                product.stock_value = product._get_latest_cumulated_value()
            elif product.cost_method == 'fifo': #Could also do same as for average, but it would lead to more rounding errors
                moves = product._get_candidates_move()
                value = 0
                for move in moves:
                    value += move.remaining_qty * move.price_unit
                product.stock_value = value


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_valuation = fields.Selection([
        ('manual_periodic', 'Periodic (manual)'),
        ('real_time', 'Perpetual (automated)')], string='Inventory Valuation',
        company_dependent=True, copy=True, required=True,
        help="If perpetual valuation is enabled for a product, the system "
             "will automatically create journal entries corresponding to "
             "stock moves, with product price as specified by the 'Costing "
             "Method'. The inventory variation account set on the product "
             "category will represent the current inventory value, and the "
             "stock input and stock output account will hold the counterpart "
             "moves for incoming and outgoing products.")
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', '(financial) FIFO)'),
        ('average', 'AVCO')], string="Costing Method",
        company_dependent=True, copy=True, required=True,
        help="Standard Price: The cost price is manually updated at the end "
             "of a specific period (usually once a year).\nAverage Price: "
             "The cost price is recomputed at each incoming shipment and "
             "used for the product valuation.\nReal Price: The cost price "
             "displayed is the price of the last outgoing product (will be "
             "used in case of inventory loss for example).""")
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        help="When doing real-time inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.")
    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', 'Stock Input Account', company_dependent=True,
        domain=[('deprecated', '=', False)], oldname="property_stock_account_input_categ",
        help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
             "there is a specific valuation account set on the source location. This is the default value for all products in this category. It "
             "can also directly be set on each product")
    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', 'Stock Output Account', company_dependent=True,
        domain=[('deprecated', '=', False)], oldname="property_stock_account_output_categ",
        help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
             "there is a specific valuation account set on the destination location. This is the default value for all products in this category. It "
             "can also directly be set on each product")
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True,
        domain=[('deprecated', '=', False)],
        help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",)
