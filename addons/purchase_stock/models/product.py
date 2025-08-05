# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import formatLang


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_buy_route(self):
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)
        if buy_route:
            return self.env['stock.route'].search([('id', '=', buy_route.id)]).ids
        return []

    route_ids = fields.Many2many(default=lambda self: self._get_buy_route())


class ProductProduct(models.Model):
    _inherit = 'product.product'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'product_id', string="PO Lines") # used to compute quantities
    monthly_demand = fields.Float(compute='_compute_monthly_demand')

    @api.depends_context('monthly_demand_start_date', 'monthly_demand_limit_date', 'warehouse_id')
    def _compute_monthly_demand(self):
        start_date = self.env.context.get('monthly_demand_start_date', fields.Datetime.now() - relativedelta(months=1))
        limit_date = self.env.context.get('monthly_demand_limit_date', fields.Datetime.now())
        warehouse_id = self.env.context.get('warehouse_id')
        move_domain = Domain([
            ('product_id', 'in', self.ids),
            ('state', '=', 'done'),
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
        for product in self:
            product.monthly_demand = qty_by_product.get(product.id, 0)

    @api.model
    def _get_monthly_demand_moves_location_domain(self):
        return [('location_dest_usage', 'in', ['customer', 'production'])]

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
        orderpoint_id = self.env.context.get('default_orderpoint_id')
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
        if orderpoint_id:
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
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
        if not orderpoint:
            return
        if 'buy' not in orderpoint.route_id.rule_ids.mapped('action'):
            orderpoint.route_id = self.env['stock.rule'].search([('action', '=', 'buy')], limit=1).route_id.id
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
