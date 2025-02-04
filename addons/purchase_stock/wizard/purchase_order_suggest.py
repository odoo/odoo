from datetime import datetime
from math import floor
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models

class PurchaseOrderSuggest(models.TransientModel):
    _name = 'purchase.order.suggest'
    _description = 'Purchase Order Suggest'

    based_on = fields.Selection(
        selection=[
            ('one_week', "Last 7 days"),
            ('one_month', "Last 30 days"),
            ('three_months', "Last 3 months"),
            ('one_year', "Last 12 months"),
            ('last_year', "Same month last year"),
            ('last_year_2', "Next month last year"),
            ('last_year_3', "After next month last year"),
        ],
        default='one_month',
        string='Based on',
        required=True
    )
    currency_id = fields.Many2one('res.currency', related='purchase_order_id.currency_id')
    deduce_forecast_quantity = fields.Boolean(
        'Deduce forecast quantity', default=True,
        help="What is already forecasted for these products in your stock will be deduced from the new calculated quantities to replenish.")
    estimated_price = fields.Float(
        string="Expected",
        compute='_compute_estimated_price',
        digits='Product Price')
    hide_warehouse = fields.Boolean(compute='_compute_hide_warehouse')
    multiplier = fields.Float(compute='_compute_multiplier')
    number_of_days = fields.Integer(
        string="Replenish for", required=True,
        help="Suggested quantities to replenish will be computed for all filtered products\
              in this catalog in order to cover this amount of days of average demand.")
    percent_factor = fields.Integer(default=100, required=True)
    product_count = fields.Integer(compute='_compute_product_count')
    product_ids = fields.Many2many('product.product')
    purchase_order_id = fields.Many2one('purchase.order', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def _compute_hide_warehouse(self):
        company_warehouses_count = self.env['stock.warehouse'].search_count([('company_id', '=', self.env.company.id)])
        self.hide_warehouse = not self.env.user.has_group('stock.group_stock_multi_warehouses') or company_warehouses_count < 2

    @api.depends('based_on', 'deduce_forecast_quantity', 'number_of_days', 'percent_factor', 'product_ids', 'warehouse_id')
    def _compute_estimated_price(self):
        for suggest in self:
            estimated_price = 0
            # Explicitly fetch existing records to avoid "NewId origin" shenanigans
            # and add context's values needed by the monthly demand's compute.
            products = self.env['product.product'].browse(self.product_ids.ids).with_context(
                suggest._get_montlhy_demand_context()
            )
            seller_params = {'order_id': suggest.purchase_order_id}

            for product in products:
                quantity = product.monthly_demand * suggest.multiplier
                if suggest.deduce_forecast_quantity:
                    quantity -= product.virtual_available
                if quantity <= 0:
                    continue
                price = product.standard_price
                seller = product._select_seller(
                    partner_id=suggest.purchase_order_id.partner_id,
                    quantity=quantity,
                    ordered_by='min_qty',
                    params=seller_params
                )
                if seller:
                    price = seller.price_discounted
                estimated_price += price * quantity
            suggest.estimated_price = estimated_price

    @api.depends('product_ids')
    def _compute_product_count(self):
        for suggest in self:
            suggest.product_count = len(suggest.product_ids)

    @api.depends('number_of_days', 'percent_factor')
    def _compute_multiplier(self):
        for suggest in self:
            match suggest.based_on:
                case 'one_week':
                    period_in_days = 7
                case 'one_month':
                    period_in_days = 30
                case 'three_months':
                    period_in_days = 90
                case 'one_year':
                    period_in_days = 365
                case _:
                    period_in_days = 30
            suggest.multiplier = (suggest.number_of_days / period_in_days) * (suggest.percent_factor / 100)

    def action_purchase_order_suggest(self):
        """ Auto-fill the Purchase Order with vendor's product regarding the
        past demand (real consumtion for a given period of time.)"""
        self.ensure_one()
        order = self.purchase_order_id
        # Products are either the given products, either the supplier's products.
        supplierinfos = self.env['product.supplierinfo'].search([
            ('partner_id', '=', order.partner_id.id),
        ])
        products = self.product_ids or supplierinfos.product_id
        # Add context's values needed by the monthly demand's compute.
        products = products.with_context(self._get_montlhy_demand_context())
        # Create new PO lines for each product with a monthy demand.
        new_po_lines_vals = []
        update_po_lines_commands = []
        create_po_lines_commands = []
        for product in products:
            quantity = floor(product.monthly_demand * self.multiplier)
            if self.deduce_forecast_quantity:
                quantity -= product.virtual_available
            if quantity <= 0:
                continue
            supplierinfo = supplierinfos.filtered(lambda supinfo: supinfo.product_id == product)[:1]
            existing_po_line = order.order_line.filtered(lambda pol: pol.product_id == product)[:1]
            if existing_po_line:
                # If a PO line already exists for this product, we simply update its quantity.
                vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                    product,
                    quantity,
                    product.uom_id,
                    order.company_id,
                    supplierinfo,
                    order
                )
                update_po_lines_commands.append(Command.update(existing_po_line.id, vals))
            else:
                # If not, we create a new PO line.
                vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                    product,
                    quantity,
                    product.uom_id,
                    order.company_id,
                    supplierinfo,
                    order
                )
                new_po_lines_vals.append(vals)
                create_po_lines_commands.append(Command.create(vals))
        order.order_line = create_po_lines_commands + update_po_lines_commands
        action = order.action_add_from_catalog()
        action['context']['search_default_products_in_order'] = 1
        action['context']['order_id'] = order.id
        del action['context']['search_default_seller_ids']
        return action

    def _get_montlhy_demand_context(self):
        self.ensure_one()
        start_date, limit_date = self._get_period_of_time()
        context = {
            'monthly_demand_start_date': start_date,
            'monthly_demand_limit_date': limit_date,
        }
        if self.warehouse_id:
            context['warehouse_id'] = self.warehouse_id.id
        return context

    def _get_period_of_time(self):
        self.ensure_one()
        start_date = fields.Datetime.now()
        limit_date = fields.Datetime.now()
        if self.based_on == 'one_week':
            start_date = start_date - relativedelta(weeks=1)
        elif self.based_on == 'one_month':
            start_date = start_date - relativedelta(months=1)
        elif self.based_on == 'three_months':
            start_date = start_date - relativedelta(months=3)
        elif self.based_on == 'one_year':
            start_date = start_date - relativedelta(years=1)
        else:  # Relative period of time.
            today = fields.Datetime.now()
            start_date = datetime(year=today.year - 1, month=today.month, day=1)
            if self.based_on == 'last_year_2':
                start_date += relativedelta(months=1)
            elif self.based_on == 'last_year_3':
                start_date += relativedelta(months=2)
            limit_date = start_date + relativedelta(months=1)
        return start_date, limit_date
