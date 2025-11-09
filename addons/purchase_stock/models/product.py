# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import formatLang
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('route_ids', 'purchase_ok')
    def _onchange_buy_route(self):
        if self.purchase_ok:
            return
        buy_routes = self.env['stock.rule'].search([
            ('action', '=', 'buy'),
            ('picking_type_id.code', '=', 'incoming'),
            ('active', '=', True),
        ]).route_id
        if any(route in self.route_ids._origin for route in buy_routes):
            return {'warning': {
                'title': self.env._('Warning!'),
                'message': self.env._(
                    'This product has the "Buy" route checked but is not purchasable.'
                )
            }}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'product_id', string="PO Lines")  # used to compute quantities
    monthly_demand = fields.Float(compute='_compute_monthly_demand')
    suggested_qty = fields.Integer(compute='_compute_suggested_quantity', search='_search_product_with_suggested_quantity')
    suggest_estimated_price = fields.Float(compute='_compute_suggest_estimated_price')

    @api.depends("monthly_demand")
    @api.depends_context("suggest_based_on", "suggest_days", "suggest_percent", "warehouse_id")
    def _compute_suggested_quantity(self):
        ctx = self.env.context
        self.suggested_qty = 0
        if ctx.get("suggest_based_on") == "actual_demand":
            for product in self:
                if product.virtual_available >= 0:
                    continue
                qty = - product.virtual_available * ctx.get("suggest_percent", 0) / 100
                product.suggested_qty = max(float_round(qty, precision_digits=0, rounding_method="UP"), 0)
        elif ctx.get("suggest_based_on"):
            for product in self:
                if product.monthly_demand <= 0:
                    continue
                monthly_ratio = ctx.get("suggest_days", 0) / (365.25 / 12)  # eg. 7 days / (365.25 days/yr / 12 mth/yr) = 0.23 months
                qty = product.monthly_demand * monthly_ratio * ctx.get("suggest_percent", 0) / 100
                qty -= max(product.qty_available, 0) + max(product.incoming_qty, 0)
                product.suggested_qty = max(float_round(qty, precision_digits=0, rounding_method="UP"), 0)

    @api.depends("suggested_qty")
    @api.depends_context("suggest_based_on", "suggest_days", "suggest_percent", "warehouse_id")
    def _compute_suggest_estimated_price(self):
        seller_args = {
            "partner_id": self.env['res.partner'].browse(self.env.context.get("partner_id")),
            "params": {'order_id': self.env['purchase.order'].browse(self.env.context.get("order_id"))}
        }
        self.suggest_estimated_price = 0.0
        for product in self:
            if product.suggested_qty <= 0:
                continue
            # Get lowest price pricelist for suggested_qty or lowest min_qty pricelist
            seller = product._select_seller(quantity=product.suggested_qty, **seller_args) or \
                     product._select_seller(quantity=None, ordered_by="min_qty", **seller_args)

            price = seller.price_discounted if seller else product.standard_price
            product.suggest_estimated_price = price * product.suggested_qty

    def _search_product_with_suggested_quantity(self, operator, value):
        if operator in ["in", "not in"]:
            return NotImplemented

        search_domain = self.env.context.get("suggest_domain") or [('type', '=', 'consu')]
        safe_search_domain = [c if c[0] != "suggested_qty" else [1, "=", 1] for c in search_domain]
        products = self.search_fetch(safe_search_domain, ["suggested_qty"])
        ids = products.filtered_domain([("suggested_qty", operator, value)]).ids

        return [('id', 'in', ids)]

    @api.depends_context('suggest_days', 'suggest_based_on', 'warehouse_id')
    def _compute_quantities(self):
        return super()._compute_quantities()

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        if self.env.context.get("suggest_based_on") and "suggest_days" in self.env.context:
            # Override to compute actual demand suggestion and update forecast on Kanban card
            to_date = fields.Datetime.now() + relativedelta(days=self.env.context.get("suggest_days"))
        return super()._compute_quantities_dict(
            lot_id=lot_id,
            owner_id=owner_id,
            package_id=package_id,
            from_date=from_date,  # Keeping default which fetches all past deliveries
            to_date=to_date,
        )

    @api.depends_context('suggest_based_on', 'warehouse_id')
    def _compute_monthly_demand(self):
        based_on = self.env.context.get("suggest_based_on", "30_days")
        warehouse_id = self.env.context.get('warehouse_id')
        start_date, limit_date = self._get_monthly_demand_range(based_on)

        move_domain = Domain([
            ('product_id', 'in', self.ids),
            ('state', 'in', ['assigned', 'confirmed', 'partially_available', 'done']),
            ('date', '>=', start_date),
            ('date', '<', limit_date),
        ])
        move_domain = Domain.AND([
            move_domain,
            self._get_monthly_demand_moves_location_domain(),
        ])
        if warehouse_id:
            move_domain = Domain.AND([
                move_domain,
                [('location_id.warehouse_id', '=', warehouse_id)]
            ])
        move_qty_by_products = self.env['stock.move']._read_group(move_domain, ['product_id'], ['product_qty:sum'])
        qty_by_product = {product.id: qty for product, qty in move_qty_by_products}

        factor = 1
        if based_on == "one_year":
            factor = 12
        elif based_on == "three_months" or based_on == "last_year_quarter":
            factor = 3
        elif based_on == "one_week":
            factor = 7 / (365.25 / 12)  # 7 days / (365.25 days/yr / 12 mth/yr) = 0.23 months
        for product in self:
            product.monthly_demand = qty_by_product.get(product.id, 0) / factor

    @api.model
    def _get_monthly_demand_moves_location_domain(self):
        return Domain.OR([
            [('location_dest_usage', 'in', ['customer', 'production'])],
            Domain.AND([
                [('location_final_id.usage', '=', 'customer')],
                [('move_dest_ids', '=', False)],
            ])
        ])

    def _get_quantity_in_progress(self, location_ids=False, warehouse_ids=False):
        if not location_ids:
            location_ids = []
        if not warehouse_ids:
            warehouse_ids = []

        qty_by_product_location, qty_by_product_wh = super()._get_quantity_in_progress(location_ids, warehouse_ids)
        domain = self._get_lines_domain(location_ids, warehouse_ids)
        groups = self.env['purchase.order.line'].sudo()._read_group(domain,
            ['order_id', 'product_id', 'product_uom_id', 'orderpoint_id', 'location_final_id'],
            ['product_qty:sum'])
        for order, product, uom, orderpoint, location_final, product_qty_sum in groups:
            if orderpoint:
                location = orderpoint.location_id
            elif location_final:
                location = location_final
            else:
                location = order.picking_type_id.default_location_dest_id
            product_qty = uom._compute_quantity(product_qty_sum, product.uom_id, round=False)
            qty_by_product_location[(product.id, location.id)] += product_qty
            qty_by_product_wh[(product.id, location.warehouse_id.id)] += product_qty
        return qty_by_product_location, qty_by_product_wh

    def _get_lines_domain(self, location_ids=False, warehouse_ids=False):
        domains = []
        rfq_domain = (
            Domain('state', 'in', ('draft', 'sent', 'to approve'))
            & Domain('product_id', 'in', self.ids)
        )
        if location_ids:
            domains.append(Domain([
                '|',
                    '&',
                    ('orderpoint_id', '=', False),
                    '|',
                        '&',
                            ('location_final_id', '=', False),
                            ('order_id.picking_type_id.default_location_dest_id', 'in', location_ids),
                        '&',
                            ('move_ids', '=', False),
                            ('location_final_id', 'child_of', location_ids),
                    '&',
                        ('move_dest_ids', '=', False),
                        ('orderpoint_id.location_id', 'in', location_ids)
            ]))
        if warehouse_ids:
            domains.append(Domain([
                '|',
                    '&',
                        ('orderpoint_id', '=', False),
                        ('order_id.picking_type_id.warehouse_id', 'in', warehouse_ids),
                    '&',
                        ('move_dest_ids', '=', False),
                        ('orderpoint_id.warehouse_id', 'in', warehouse_ids)
            ]))
        return rfq_domain & Domain.OR(domains or [Domain.TRUE])

    def _get_monthly_demand_range(self, based_on):
        start_date = limit_date = datetime.now()

        if not based_on or based_on == 'actual_demand' or based_on == '30_days':
            start_date = start_date - relativedelta(days=30)  # Default monthly demand
        elif based_on == 'one_week':
            start_date = start_date - relativedelta(weeks=1)
        elif based_on == 'three_months':
            start_date = start_date - relativedelta(months=3)
        elif based_on == 'one_year':
            start_date = start_date - relativedelta(years=1)
        else:  # Relative period of time.
            today = datetime.now()
            start_date = datetime(year=today.year - 1, month=today.month, day=1)

            if based_on == 'last_year_m_plus_1':
                start_date += relativedelta(months=1)
            elif based_on == 'last_year_m_plus_2':
                start_date += relativedelta(months=2)

            if based_on == 'last_year_quarter':
                limit_date = start_date + relativedelta(months=3)
            else:
                limit_date = start_date + relativedelta(months=1)

        return start_date, limit_date


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    last_purchase_date = fields.Date('Last Purchase', compute='_compute_last_purchase_date')
    show_set_supplier_button = fields.Boolean(
        'Show Set Supplier Button', compute='_compute_show_set_supplier_button')

    def _compute_last_purchase_date(self):
        self.last_purchase_date = False
        purchases = self.env['purchase.order'].search([
            ('state', '=', 'purchase'),
            ('order_line.product_id', 'in',
             self.product_tmpl_id.product_variant_ids.ids),
            ('partner_id', 'in', self.partner_id.ids),
        ], order='date_order desc')
        for supplier in self:
            products = supplier.product_tmpl_id.product_variant_ids
            for purchase in purchases:
                if purchase.partner_id != supplier.partner_id:
                    continue
                if not (products & purchase.order_line.product_id):
                    continue
                supplier.last_purchase_date = purchase.date_order
                break

    def _compute_show_set_supplier_button(self):
        self.show_set_supplier_button = True
        orderpoint_id = self.env.context.get('orderpoint_id', self.env.context.get('default_orderpoint_id'))
        if orderpoint_id:
            orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
            self.filtered(
                lambda s: s.id == orderpoint.supplier_id.id
            ).show_set_supplier_button = False

    @api.depends('partner_id', 'min_qty', 'product_uom_id', 'currency_id', 'price')
    @api.depends_context('use_simplified_supplier_name')
    def _compute_display_name(self):
        if self.env.context.get('use_simplified_supplier_name'):
            super()._compute_display_name()
        else:
            for supplier in self:
                price_str = formatLang(self.env, supplier.price, currency_obj=supplier.currency_id)
                supplier.display_name = f'{supplier.partner_id.display_name} ({supplier.min_qty} {supplier.product_uom_id.name} - {price_str})'

    def action_set_supplier(self):
        self.ensure_one()
        orderpoint_id = self.env.context.get('orderpoint_id')
        if not orderpoint_id:
            return
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
        if 'buy' not in orderpoint.route_id.rule_ids.mapped('action'):
            domain = Domain.AND([
                [('action', '=', 'buy')],
                Domain.OR([
                    [('company_id', '=', orderpoint.company_id.id)],
                    [('company_id', '=', False)],
                ]),
            ])
            orderpoint.route_id = self.env['stock.rule'].search(domain, limit=1).route_id.id
        orderpoint.supplier_id = self
        supplier_min_qty = self.product_uom_id._compute_quantity(self.min_qty, orderpoint.product_id.uom_id)
        if orderpoint.qty_to_order < supplier_min_qty:
            orderpoint.qty_to_order = supplier_min_qty
        if self.env.context.get('replenish_id'):
            replenish = self.env['product.replenish'].browse(self.env.context.get('replenish_id'))
            replenish.supplier_id = self
            return {
                'type': 'ir.actions.act_window',
                'name': 'Replenish',
                'res_model': 'product.replenish',
                'res_id': replenish.id,
                'target': 'new',
                'view_mode': 'form',
            }
        return orderpoint.action_stock_replenishment_info()
