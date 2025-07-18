from datetime import datetime
from dateutil.relativedelta import relativedelta
from math import ceil

from odoo import api, Command, fields, models


class PurchaseOrderSuggest(models.TransientModel):
    _name = 'purchase.order.suggest'
    _description = 'Purchase Order Suggest'

    purchase_order_id = fields.Many2one('purchase.order', required=True)
    currency_id = fields.Many2one('res.currency', related='purchase_order_id.currency_id')
    partner_id = fields.Many2one('res.partner', related='purchase_order_id.partner_id', change_default=True)
    product_ids = fields.Many2many('product.product')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    based_on = fields.Selection(
        selection=[
            ('actual_demand', "Actual Demand"),
            ('one_week', "Last 7 days"),
            ('one_month', "Last 30 days"),
            ('three_months', "Last 3 months"),
            ('one_year', "Last 12 months"),
            ('last_year', "Same month last year"),
            ('last_year_2', "Next month last year"),
            ('last_year_3', "After next month last year"),
            ('last_year_quarter', "Last year quarter"),
        ],
        default='one_month',
        string='Based on',
        help="Estimate the sales volume for the period based on past period or order the forecasted quantity for that period.",
        required=True
    )
    number_of_days = fields.Integer(
        string="Replenish for", required=True,
        default=7,
        help="Suggested quantities to replenish will be computed to cover this amount of days for all filtered products in this catalog.")
    percent_factor = fields.Integer(default=100, required=True)
    estimated_price = fields.Float(
        string="Expected",
        compute='_compute_estimated_price',
        digits='Product Price')
    product_count = fields.Integer(compute='_compute_estimated_price')
    hide_warehouse = fields.Boolean(compute='_compute_hide_warehouse')
    multiplier = fields.Float(compute='_compute_multiplier')

    def _compute_hide_warehouse(self):
        if not self.env.user.has_group('stock.group_stock_multi_warehouses'):
            self.hide_warehouse = True
        else:
            company_warehouses_count = self.env['stock.warehouse'].search_count([('company_id', '=', self.env.company.id)])
            self.hide_warehouse = company_warehouses_count < 2

    @api.depends('based_on', 'number_of_days', 'percent_factor', 'product_ids', 'warehouse_id')
    def _compute_estimated_price(self):
        for suggest in self:
            estimated_price, product_count = 0, 0
            seller_args = {
                "partner_id": suggest.purchase_order_id.partner_id,
                "params": {'order_id': suggest.purchase_order_id}
            }
            # Explicitly fetch existing records to avoid "NewId origin" shenanigans
            products = self.env['product.product'].browse(self.product_ids.ids)
            products = products.with_context(suggest._get_suggested_products_context())

            for product in products:
                if self.based_on == 'actual_demand':
                    quantity = ceil(product.outgoing_qty * (self.percent_factor / 100))
                else:
                    quantity = ceil(product.monthly_demand * self.multiplier)
                qty_to_deduce = max(product.qty_available, 0) + max(product.incoming_qty, 0)
                quantity -= qty_to_deduce
                if quantity <= 0:
                    continue
                # Then, compute the price either from pricelist or standard price
                # Try pricelist for quantity first, then lowest min_qty pricelist
                seller = (
                    product._select_seller(quantity=quantity, **seller_args)
                    or product._select_seller(quantity=None, ordered_by="min_qty", **seller_args)
                )
                price = seller.price_discounted if seller else product.standard_price
                estimated_price += price * quantity
            suggest.product_count = product_count
            suggest.estimated_price = estimated_price

    @api.depends('number_of_days', 'percent_factor')
    def _compute_multiplier(self):
        for suggest in self:
            suggest.multiplier = (suggest.number_of_days / (365.25 / 12)) * (suggest.percent_factor / 100)

    def action_purchase_order_suggest(self):
        """ Auto-fill the Purchase Order with vendor's product regarding the
        past demand (real consumtion for a given period of time.)"""
        self.ensure_one()
        order = self.purchase_order_id
        supplierinfos = self.env['product.supplierinfo'].search([
            ('partner_id', '=', order.partner_id.id),
        ])
        products = self.product_ids or supplierinfos.product_id
        products = products.with_context(self._get_suggested_products_context())

        # Create new PO lines for each product with a monthy demand.
        po_lines_commands = []
        for product in products:
            existing_po_lines = order.order_line.filtered(lambda pol: pol.product_id == product)
            supplierinfo = supplierinfos.filtered(lambda supinfo: supinfo.product_id == product)[:1]

            if self.based_on == 'actual_demand':
                quantity = ceil(product.outgoing_qty * (self.percent_factor / 100))
            else:
                quantity = ceil(product.monthly_demand * self.multiplier)
            qty_to_deduce = max(product.qty_available, 0) + max(product.incoming_qty, 0)
            quantity -= qty_to_deduce

            if quantity > 0:  # Save fetching new val if we don't need it
                suggest_line = self.env['purchase.order.line']._prepare_purchase_order_line(
                    product,
                    quantity,
                    product.uom_id,
                    order.company_id,
                    supplierinfo,
                    order,
                )
            existing_po_lines = order.order_line.filtered(lambda pol: pol.product_id == product)
            # Keep 0 or 1 line max, delete all others
            if existing_po_lines:
                to_unlink = existing_po_lines[:-1] if quantity > 0 else existing_po_lines
                po_lines_commands += [Command.unlink(line.id) for line in to_unlink]
                if quantity > 0:
                    po_lines_commands.append(Command.update(existing_po_lines[-1].id, suggest_line))
            elif quantity > 0:
                po_lines_commands.append(Command.create(suggest_line))

        order.order_line = po_lines_commands
        self._save_values_for_vendor()
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'refresh': True},
        }

    def _get_suggested_products_context(self):
        self.ensure_one()
        if self.based_on == 'actual_demand':
            context = {
                'from_date': fields.Datetime.now(),
                'to_date': fields.Datetime.now() + relativedelta(days=self.number_of_days),
            }
        else:
            start_date, limit_date = self._get_period_of_time()
            context = {
                'monthly_demand_start_date': start_date,
                'monthly_demand_limit_date': limit_date,
            }
        if self.warehouse_id and not self.hide_warehouse:
            context['warehouse_id'] = self.warehouse_id.id
        context['suggest_based_on'] = self.based_on
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

            if self.based_on == 'last_year_quarter':
                limit_date = start_date + relativedelta(months=3)
            else:
                limit_date = start_date + relativedelta(months=1)
        return start_date, limit_date

    def _save_values_for_vendor(self):
        """ Save fields' value as default values for the PO vendor."""
        cid = self.env.company.id
        condition = f'partner_id={self.partner_id.id}'
        for field in ['based_on', 'number_of_days', 'percent_factor']:
            self.env['ir.default'].set('purchase.order.suggest', field, self[field], company_id=cid, condition=condition)
