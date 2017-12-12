# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, pycompat
from odoo.addons import decimal_precision as dp



class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    property_valuation = fields.Selection([
        ('manual_periodic', 'Periodic (manual)'),
        ('real_time', 'Perpetual (automated)')], string='Inventory Valuation',
        company_dependent=True, copy=True, default='manual_periodic',
        help="""Manual: The accounting entries to value the inventory are not posted automatically.
        Automated: An accounting entry is automatically created to value the inventory when a product enters or leaves the company.""")
    valuation = fields.Char(compute='_compute_valuation_type', inverse='_set_valuation_type')
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')], string='Costing Method',
        company_dependent=True, copy=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.""")
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
        # When going from FIFO to AVCO or to standard, we update the standard price with the
        # average value in stock.
        if self.property_cost_method == 'fifo' and self.cost_method in ['average', 'standard']:
            # Cannot use the `stock_value` computed field as it's already invalidated when
            # entering this method.
            valuation = sum([variant._sum_remaining_values() for variant in self.product_variant_ids])
            qty_available = self.with_context(company_owned=True).qty_available
            if qty_available:
                self.standard_price = valuation / qty_available
        return self.write({'property_cost_method': self.cost_method})

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
    def action_open_product_moves(self):
        self.ensure_one()
        action = self.env.ref('stock_account.stock_move_valuation_action').read()[0]
        action['domain'] = [('product_tmpl_id', '=', self.id)]
        action['context'] = {
            'search_default_outgoing': True,
            'search_default_incoming': True,
            'search_default_done': True,
            'is_avg': self.cost_method == 'average',
        }
        return action

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

    stock_value = fields.Float(
        'Value', compute='_compute_stock_value')

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

    def _get_fifo_candidates_in_move(self):
        """ Find IN moves that can be used to value OUT moves.
        """
        self.ensure_one()
        domain = [('product_id', '=', self.id), ('remaining_qty', '>', 0.0)] + self.env['stock.move']._get_in_base_domain()
        candidates = self.env['stock.move'].search(domain, order='date, id')
        return candidates

    def _sum_remaining_values(self):
        StockMove = self.env['stock.move']
        domain = [('product_id', '=', self.id)] + StockMove._get_all_base_domain()
        moves = StockMove.search(domain)
        return sum(moves.mapped('remaining_value'))

    @api.multi
    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state', 'product_tmpl_id.cost_method')
    def _compute_stock_value(self):
        for product in self:
            if product.cost_method in ['standard', 'average']:
                product.stock_value = product.standard_price * product.with_context(company_owned=True).qty_available
            elif product.cost_method == 'fifo':
                product.stock_value = product._sum_remaining_values()

    @api.multi
    def action_open_product_moves(self):
        self.ensure_one()
        action = self.env.ref('stock_account.stock_move_valuation_action').read()[0]
        action['domain'] = [('product_id', '=', self.id)]
        action['context'] = {
            'search_default_outgoing': True,
            'search_default_incoming': True,
            'search_default_done': True,
            'is_avg': self.cost_method == 'average',
        }
        return action


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_valuation = fields.Selection([
        ('manual_periodic', 'Manual'),
        ('real_time', 'Automated')], string='Inventory Valuation',
        company_dependent=True, copy=True, required=True,
        help="""Manual: The accounting entries to value the inventory are not posted automatically.
        Automated: An accounting entry is automatically created to value the inventory when a product enters or leaves the company.
        """)
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')], string="Costing Method",
        company_dependent=True, copy=True, required=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        """)
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

    @api.onchange('property_cost_method')
    def onchange_property_valuation(self):
        if not self._origin:
            # don't display the warning when creating a product category
            return
        return {
            'warning': {
                'title': _("Warning"),
                'message': _("Changing your cost method is an important change that will impact your inventory valuation. Are you sure you want to make that change?"),
            }
        }

