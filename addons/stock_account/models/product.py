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
            valuation = sum([variant._sum_remaining_values()[0] for variant in self.product_variant_ids])
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
        # TODO: remove me in master
        pass

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

    stock_value_currency_id = fields.Many2one('res.currency', compute='_compute_stock_value_currency')
    stock_value = fields.Float(
        'Value', compute='_compute_stock_value')
    qty_at_date = fields.Float(
        'Quantity', compute='_compute_stock_value')
    stock_fifo_real_time_aml_ids = fields.Many2many(
        'account.move.line', compute='_compute_stock_value')
    stock_fifo_manual_move_ids = fields.Many2many(
        'stock.move', compute='_compute_stock_value')

    @api.multi
    def do_change_standard_price(self, new_price, account_id):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        AccountMove = self.env['account.move']

        quant_locs = self.env['stock.quant'].sudo().read_group([('product_id', 'in', self.ids)], ['location_id'], ['location_id'])
        quant_loc_ids = [loc['location_id'][0] for loc in quant_locs]
        locations = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', self.env.user.company_id.id), ('id', 'in', quant_loc_ids)])

        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}

        for location in locations:
            for product in self.with_context(location=location.id, compute_child=False).filtered(lambda r: r.valuation == 'real_time'):
                diff = product.standard_price - new_price
                if float_is_zero(diff, precision_rounding=product.currency_id.rounding):
                    raise UserError(_("No difference between the standard price and the new price."))
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
                        'ref': product.default_code,
                        'line_ids': [(0, 0, {
                            'name': _('%s changed cost from %s to %s - %s') % (self.env.user.name, product.standard_price, new_price, product.display_name),
                            'account_id': debit_account_id,
                            'debit': abs(diff * qty_available),
                            'credit': 0,
                            'product_id': product.id,
                        }), (0, 0, {
                            'name': _('%s changed cost from %s to %s - %s') % (self.env.user.name, product.standard_price, new_price, product.display_name),
                            'account_id': credit_account_id,
                            'debit': 0,
                            'credit': abs(diff * qty_available),
                            'product_id': product.id,
                        })],
                    }
                    move = AccountMove.create(move_vals)
                    move.post()

        self.write({'standard_price': new_price})
        return True

    def _get_fifo_candidates_in_move(self):
        """ Find IN moves that can be used to value OUT moves.
        """
        return self._get_fifo_candidates_in_move_with_company()

    def _get_fifo_candidates_in_move_with_company(self, move_company_id=False):
        self.ensure_one()
        domain = [('product_id', '=', self.id), ('remaining_qty', '>', 0.0)] + self.env['stock.move']._get_in_base_domain(move_company_id)
        candidates = self.env['stock.move'].search(domain, order='date, id')
        return candidates

    def _sum_remaining_values(self):
        StockMove = self.env['stock.move']
        domain = [('product_id', '=', self.id)] + StockMove._get_all_base_domain()
        moves = StockMove.search(domain)
        return sum(moves.mapped('remaining_value')), moves

    @api.multi
    def _compute_stock_value_currency(self):
        currency_id = self.env.user.company_id.currency_id
        for product in self:
            product.stock_value_currency_id = currency_id

    @api.multi
    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state', 'stock_move_ids.remaining_value', 'product_tmpl_id.cost_method', 'product_tmpl_id.standard_price', 'product_tmpl_id.property_valuation', 'product_tmpl_id.categ_id.property_valuation')
    def _compute_stock_value(self):
        StockMove = self.env['stock.move']
        to_date = self.env.context.get('to_date')

        real_time_product_ids = [product.id for product in self if product.product_tmpl_id.valuation == 'real_time']
        if real_time_product_ids:
            self.env['account.move.line'].check_access_rights('read')
            fifo_automated_values = {}
            query = """SELECT aml.product_id, aml.account_id, sum(aml.debit) - sum(aml.credit), sum(quantity), array_agg(aml.id)
                         FROM account_move_line AS aml
                        WHERE aml.product_id IN %%s AND aml.company_id=%%s %s
                     GROUP BY aml.product_id, aml.account_id"""
            params = (tuple(real_time_product_ids), self.env.user.company_id.id)
            if to_date:
                query = query % ('AND aml.date <= %s',)
                params = params + (to_date,)
            else:
                query = query % ('',)
            self.env.cr.execute(query, params=params)

            res = self.env.cr.fetchall()
            for row in res:
                fifo_automated_values[(row[0], row[1])] = (row[2], row[3], list(row[4]))

        product_values = {product.id: 0 for product in self}
        product_move_ids = {product.id: [] for product in self}

        if to_date:
            domain = [('product_id', 'in', self.ids), ('date', '<=', to_date)] + StockMove._get_all_base_domain()
            value_field_name = 'value'
        else:
            domain = [('product_id', 'in', self.ids)] + StockMove._get_all_base_domain()
            value_field_name = 'remaining_value'

        StockMove.check_access_rights('read')
        query = StockMove._where_calc(domain)
        StockMove._apply_ir_rules(query, 'read')
        from_clause, where_clause, params = query.get_sql()
        query_str = """
            SELECT stock_move.product_id, SUM(COALESCE(stock_move.{}, 0.0)), ARRAY_AGG(stock_move.id)
            FROM {}
            WHERE {}
            GROUP BY stock_move.product_id
        """.format(value_field_name, from_clause, where_clause)
        self.env.cr.execute(query_str, params)
        for product_id, value, move_ids in self.env.cr.fetchall():
            product_values[product_id] = value
            product_move_ids[product_id] = move_ids

        for product in self:
            if product.cost_method in ['standard', 'average']:
                qty_available = product.with_context(company_owned=True, owner_id=False).qty_available
                price_used = product.standard_price
                if to_date:
                    price_used = product.get_history_price(
                        self.env.user.company_id.id,
                        date=to_date,
                    )
                product.stock_value = price_used * qty_available
                product.qty_at_date = qty_available
            elif product.cost_method == 'fifo':
                if to_date:
                    if product.product_tmpl_id.valuation == 'manual_periodic':
                        product.stock_value = product_values[product.id]
                        product.qty_at_date = product.with_context(company_owned=True, owner_id=False).qty_available
                        product.stock_fifo_manual_move_ids = StockMove.browse(product_move_ids[product.id])
                    elif product.product_tmpl_id.valuation == 'real_time':
                        valuation_account_id = product.categ_id.property_stock_valuation_account_id.id
                        value, quantity, aml_ids = fifo_automated_values.get((product.id, valuation_account_id)) or (0, 0, [])
                        product.stock_value = value
                        product.qty_at_date = quantity
                        product.stock_fifo_real_time_aml_ids = self.env['account.move.line'].browse(aml_ids)
                else:
                    product.stock_value = product_values[product.id]
                    product.qty_at_date = product.with_context(company_owned=True, owner_id=False).qty_available
                    if product.product_tmpl_id.valuation == 'manual_periodic':
                        product.stock_fifo_manual_move_ids = StockMove.browse(product_move_ids[product.id])
                    elif product.product_tmpl_id.valuation == 'real_time':
                        valuation_account_id = product.categ_id.property_stock_valuation_account_id.id
                        value, quantity, aml_ids = fifo_automated_values.get((product.id, valuation_account_id)) or (0, 0, [])
                        product.stock_fifo_real_time_aml_ids = self.env['account.move.line'].browse(aml_ids)

    def action_valuation_at_date_details(self):
        """ Returns an action with either a list view of all the valued stock moves of `self` if the
        valuation is set as manual or a list view of all the account move lines if the valuation is
        set as automated.
        """
        self.ensure_one()
        to_date = self.env.context.get('to_date')
        ctx = self.env.context.copy()
        ctx.pop('group_by', None)
        action = {
            'name': _('Valuation at date'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': ctx,
        }
        if self.valuation == 'real_time':
            action['res_model'] = 'account.move.line'
            action['domain'] = [('id', 'in', self.with_context(to_date=to_date).stock_fifo_real_time_aml_ids.ids)]
            tree_view_ref = self.env.ref('stock_account.view_stock_account_aml')
            form_view_ref = self.env.ref('account.view_move_line_form')
            action['views'] = [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')]
        else:
            action['res_model'] = 'stock.move'
            action['domain'] = [('id', 'in', self.with_context(to_date=to_date).stock_fifo_manual_move_ids.ids)]
            tree_view_ref = self.env.ref('stock_account.view_move_tree_valuation_at_date')
            form_view_ref = self.env.ref('stock.view_move_form')
            action['views'] = [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')]
        return action

    @api.multi
    def action_open_product_moves(self):
        #TODO: remove me in master
        pass

    @api.model
    def _anglo_saxon_sale_move_lines(self, name, product, uom, qty, price_unit, currency=False, amount_currency=False, fiscal_position=False, account_analytic=False, analytic_tags=False):
        """Prepare dicts describing new journal COGS journal items for a product sale.

        Returns a dict that should be passed to `_convert_prepared_anglosaxon_line()` to
        obtain the creation value for the new journal items.

        :param Model product: a product.product record of the product being sold
        :param Model uom: a product.uom record of the UoM of the sale line
        :param Integer qty: quantity of the product being sold
        :param Integer price_unit: unit price of the product being sold
        :param Model currency: a res.currency record from the order of the product being sold
        :param Interger amount_currency: unit price in the currency from the order of the product being sold
        :param Model fiscal_position: a account.fiscal.position record from the order of the product being sold
        :param Model account_analytic: a account.account.analytic record from the line of the product being sold
        """

        if product.type == 'product' and product.valuation == 'real_time':
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            # debit account dacc will be the output account
            dacc = accounts['stock_output'].id
            # credit account cacc will be the expense account
            cacc = accounts['expense'].id
            if dacc and cacc:
                return [
                    {
                        'type': 'src',
                        'name': name[:64],
                        'price_unit': price_unit,
                        'quantity': qty,
                        'price': price_unit * qty,
                        'currency_id': currency and currency.id,
                        'amount_currency': amount_currency,
                        'account_id': dacc,
                        'product_id': product.id,
                        'uom_id': uom.id,
                        'account_analytic_id': account_analytic and account_analytic.id,
                        'analytic_tag_ids': analytic_tags and analytic_tags.ids and [(6, 0, analytic_tags.ids)] or False,
                    },

                    {
                        'type': 'src',
                        'name': name[:64],
                        'price_unit': price_unit,
                        'quantity': qty,
                        'price': -1 * price_unit * qty,
                        'currency_id': currency and currency.id,
                        'amount_currency': -1 * amount_currency,
                        'account_id': cacc,
                        'product_id': product.id,
                        'uom_id': uom.id,
                        'account_analytic_id': account_analytic and account_analytic.id,
                        'analytic_tag_ids': analytic_tags and analytic_tags.ids and [(6, 0, analytic_tags.ids)] or False,
                    },
                ]
        return []

    def _get_anglo_saxon_price_unit(self, uom=False):
        price = self.standard_price
        if not self or not uom or self.uom_id.id == uom.id:
            return price or 0.0
        return self.uom_id._compute_price(price, uom)

    def _compute_average_price(self, qty_done, quantity, moves):
        average_price_unit = 0
        qty_delivered = 0
        invoiced_qty = 0
        for move in moves:
            if move.state != 'done':
                continue
            invoiced_qty += move.product_qty
            if invoiced_qty <= qty_done:
                continue
            qty_to_consider = move.product_qty
            if invoiced_qty - move.product_qty < qty_done:
                qty_to_consider = invoiced_qty - qty_done
            qty_to_consider = min(qty_to_consider, quantity - qty_delivered)
            qty_delivered += qty_to_consider
            # `move.price_unit` is negative if the move is out and positive if the move is
            # dropshipped. Use its absolute value to compute the average price unit.
            if qty_delivered:
                average_price_unit = (average_price_unit * (qty_delivered - qty_to_consider) + abs(move.price_unit) * qty_to_consider) / qty_delivered
            if qty_delivered == quantity:
                break
        return average_price_unit


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
