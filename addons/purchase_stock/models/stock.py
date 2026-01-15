# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil import relativedelta

from odoo import api, Command, fields, models, _
from odoo.fields import Domain


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id = fields.Many2one(
        'purchase.order', related='move_ids.purchase_line_id.order_id',
        string="Purchase Orders", readonly=True)

    days_to_arrive = fields.Datetime(compute='_compute_effective_date', search="_search_days_to_arrive", copy=False)
    delay_pass = fields.Datetime(compute='_compute_date_order', search="_search_delay_pass", index=True, copy=False)

    @api.depends('state', 'location_dest_id.usage', 'date_done')
    def _compute_effective_date(self):
        for picking in self:
            if picking.state == 'done' and picking.location_dest_id.usage != 'supplier' and picking.date_done:
                picking.days_to_arrive = picking.date_done
            else:
                picking.days_to_arrive = False

    def _compute_date_order(self):
        for picking in self:
            picking.delay_pass = picking.purchase_id.date_order if picking.purchase_id else fields.Datetime.now()

    @api.model
    def _search_days_to_arrive(self, operator, value):
        return [('date_done', operator, value)]

    @api.model
    def _search_delay_pass(self, operator, value):
        return [('purchase_id.date_order', operator, value)]

    def _action_done(self):
        self.purchase_id.sudo().action_acknowledge()
        return super()._action_done()


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    buy_to_resupply = fields.Boolean(
        'Buy to Resupply', compute='_compute_buy_to_resupply',
        inverse="_inverse_buy_to_resupply", default=True,
        help="When products are bought, they can be delivered to this warehouse")
    buy_pull_id = fields.Many2one('stock.rule', 'Buy rule', copy=False)

    def _compute_buy_to_resupply(self):
        for warehouse in self:
            buy_route = warehouse.buy_pull_id.route_id
            warehouse.buy_to_resupply = bool(buy_route.product_selectable or buy_route.warehouse_ids.filtered(lambda w: w.id == warehouse.id))

    def _inverse_buy_to_resupply(self):
        for warehouse in self:
            buy_route = warehouse.buy_pull_id.route_id
            if not buy_route:
                buy_route = self.env['stock.rule'].search([
                    ('action', '=', 'buy'), ('warehouse_id', '=', warehouse.id)]).route_id
            if warehouse.buy_to_resupply:
                buy_route.warehouse_ids = [Command.link(warehouse.id)]
            else:
                buy_route.warehouse_ids = [Command.unlink(warehouse.id)]

    def _create_or_update_route(self):
        purchase_route = self._find_or_create_global_route('purchase_stock.route_warehouse0_buy', _('Buy'))
        for warehouse in self:
            if warehouse.buy_to_resupply:
                purchase_route.warehouse_ids = [Command.link(warehouse.id)]
        return super()._create_or_update_route()

    def _generate_global_route_rules_values(self):
        rules = super()._generate_global_route_rules_values()
        location_id = self.lot_stock_id
        rules.update({
            'buy_pull_id': {
                'depends': ['reception_steps', 'buy_to_resupply'],
                'create_values': {
                    'action': 'buy',
                    'picking_type_id': self.in_type_id.id,
                    'company_id': self.company_id.id,
                    'route_id': self._find_or_create_global_route('purchase_stock.route_warehouse0_buy', _('Buy')).id,
                    'propagate_cancel': self.reception_steps != 'one_step',
                },
                'update_values': {
                    'active': self.buy_to_resupply,
                    'name': self._format_rulename(location_id, False, 'Buy'),
                    'location_dest_id': location_id.id,
                    'propagate_cancel': self.reception_steps != 'one_step',
                }
            }
        })
        return rules

    def _get_all_routes(self):
        routes = super(StockWarehouse, self)._get_all_routes()
        routes |= self.filtered(lambda self: self.buy_to_resupply and self.buy_pull_id and self.buy_pull_id.route_id).mapped('buy_pull_id').mapped('route_id')
        return routes

    def get_rules_dict(self):
        result = super(StockWarehouse, self).get_rules_dict()
        for warehouse in self:
            result[warehouse.id].update(warehouse._get_receive_rules_dict())
        return result

    def _get_routes_values(self):
        routes = super(StockWarehouse, self)._get_routes_values()
        routes.update(self._get_receive_routes_values('buy_to_resupply'))
        return routes

    def _update_name_and_code(self, name=False, code=False):
        res = super(StockWarehouse, self)._update_name_and_code(name, code)
        warehouse = self[0]
        #change the buy stock rule name
        if warehouse.buy_pull_id and name:
            warehouse.buy_pull_id.write({'name': warehouse.buy_pull_id.name.replace(warehouse.name, name, 1)})
        return res


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super()._prepare_move_default_values(return_line, new_picking)
        if self.location_id.usage == "supplier":
            vals['purchase_line_id'], vals['partner_id'] = return_line.move_id._get_purchase_line_and_partner_from_chain()
        return vals

    def _create_return(self):
        picking = super()._create_return()
        if len(picking.move_ids.partner_id) == 1 and picking.partner_id != picking.move_ids.partner_id:
            picking.partner_id = picking.move_ids.partner_id
        return picking


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    show_supplier = fields.Boolean('Show supplier column', compute='_compute_show_supplier')
    supplier_id = fields.Many2one(
        'product.supplierinfo', string='Vendor Pricelist', check_company=True,
        domain="['|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]",
        inverse='_inverse_supplier_id',
    )
    supplier_id_placeholder = fields.Char(compute='_compute_supplier_id_placeholder')
    vendor_ids = fields.One2many(related='product_id.seller_ids', string="Vendors")
    effective_vendor_id = fields.Many2one(
        'res.partner', search='_search_effective_vendor_id', compute='_compute_effective_vendor_id',
        store=False, help='Either the vendor set directly or the one computed to be used by this replenishment'
    )
    available_vendor = fields.Many2one('res.partner', string='Available Vendor', search='_search_available_vendor', store=False, help="Any vendor on the product's pricelist")

    def _inverse_route_id(self):
        for orderpoint in self:
            if not orderpoint.route_id:
                orderpoint.supplier_id = False
        super()._inverse_route_id()

    @api.depends('supplier_id')
    def _compute_deadline_date(self):
        """ Extend to add more depends values """
        super()._compute_deadline_date()

    @api.depends('product_id.purchase_order_line_ids.product_qty', 'product_id.purchase_order_line_ids.state', 'supplier_id', 'supplier_id.product_uom_id', 'product_id.seller_ids', 'product_id.seller_ids.product_uom_id')
    def _compute_qty_to_order_computed(self):
        """ Extend to add more depends values
        TODO: Probably performance costly due to x2many in depends
        """
        return super()._compute_qty_to_order_computed()

    @api.depends('supplier_id')
    def _compute_lead_days(self):
        return super()._compute_lead_days()

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        # Avoid computing rule_ids if no stock.rules with the buy action
        if not self.env['stock.rule'].search([('action', '=', 'buy')]):
            return res
        # Compute rule_ids only for orderpoint whose compnay_id.days_to_purchase != orderpoint.days_to_order
        orderpoints_to_compute = self.filtered(lambda orderpoint: orderpoint.days_to_order != orderpoint.company_id.days_to_purchase)
        for orderpoint in orderpoints_to_compute:
            if 'buy' in orderpoint.rule_ids.mapped('action'):
                orderpoint.days_to_order = orderpoint.company_id.days_to_purchase
        return res

    @api.depends('effective_route_id')
    def _compute_show_supplier(self):
        buy_route = []
        for res in self.env['stock.rule'].search_read([('action', '=', 'buy')], ['route_id']):
            buy_route.append(res['route_id'][0])
        for orderpoint in self:
            orderpoint.show_supplier = orderpoint.effective_route_id.id in buy_route

    def _inverse_supplier_id(self):
        for orderpoint in self:
            if not orderpoint.route_id and orderpoint.supplier_id:
                orderpoint.route_id = self.env['stock.rule'].search([('action', '=', 'buy')])[0].route_id

    @api.depends('effective_route_id', 'supplier_id', 'rule_ids', 'product_id.seller_ids', 'product_id.seller_ids.delay')
    def _compute_supplier_id_placeholder(self):
        for orderpoint in self:
            default_supplier = orderpoint._get_default_supplier()
            orderpoint.supplier_id_placeholder = default_supplier.display_name if default_supplier else ''

    @api.depends('effective_route_id', 'supplier_id', 'rule_ids', 'product_id.seller_ids', 'product_id.seller_ids.delay')
    def _compute_effective_vendor_id(self):
        for orderpoint in self:
            orderpoint.effective_vendor_id = (orderpoint.supplier_id if orderpoint.supplier_id else orderpoint._get_default_supplier()).partner_id

    def _search_effective_vendor_id(self, operator, value):
        vendors = self.env['res.partner'].search([('id', operator, value)])
        orderpoints = self.env['stock.warehouse.orderpoint'].search([]).filtered(
            lambda orderpoint: orderpoint.effective_vendor_id in vendors
        )
        return [('id', 'in', orderpoints.ids)]

    def _search_available_vendor(self, operator, value):
        vendors = self.env['res.partner'].search([('id', operator, value)])
        orderpoints = self.env['stock.warehouse.orderpoint'].search([]).filtered(
            lambda orderpoint: orderpoint.product_id._prepare_sellers().mapped('partner_id') & vendors
        )
        return [('id', 'in', orderpoints.ids)]

    def _compute_show_supply_warning(self):
        for orderpoint in self:
            if 'buy' in orderpoint.rule_ids.mapped('action') and not orderpoint.show_supply_warning:
                orderpoint.show_supply_warning = not orderpoint.vendor_ids
                continue
            super(StockWarehouseOrderpoint, orderpoint)._compute_show_supply_warning()

    def action_view_purchase(self):
        """ This function returns an action that display existing
        purchase orders of given orderpoint.
        """
        result = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_rfq')

        # Remvove the context since the action basically display RFQ and not PO.
        result['context'] = {}
        order_line_ids = self.env['purchase.order.line'].search([('orderpoint_id', '=', self.id)])
        purchase_ids = order_line_ids.mapped('order_id')

        result['domain'] = "[('id','in',%s)]" % (purchase_ids.ids)

        return result

    def _get_default_route(self):
        route_ids = self.env['stock.rule'].search([
            ('action', '=', 'buy')
        ]).route_id
        route_id = self.rule_ids.route_id & route_ids
        if self.product_id.seller_ids and route_id:
            return route_id[0]
        return super()._get_default_route()

    def _get_default_supplier(self):
        self.ensure_one()
        if self.show_supplier and self.product_id:
            return self._get_default_rule()._get_matching_supplier(
                self.product_id, self.qty_to_order, self.product_uom, self.company_id, {}
            )
        else:
            return self.env['product.supplierinfo']

    def _get_lead_days_values(self):
        values = super()._get_lead_days_values()
        if self.supplier_id:
            values['supplierinfo'] = self.supplier_id
        return values

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        domain = Domain('orderpoint_id', 'in', self.ids)
        if self.env.context.get('written_after'):
            domain &= Domain('write_date', '>=', self.env.context.get('written_after'))
        order = self.env['purchase.order.line'].search(domain, limit=1).order_id
        if order:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The following replenishment order has been generated'),
                    'message': '%s',
                    'links': [{
                        'label': order.display_name,
                        'url': f'/odoo/action-purchase.action_rfq_form/{order.id}',
                    }],
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        return super()._get_replenishment_order_notification()

    def _prepare_procurement_values(self, date=False):
        values = super()._prepare_procurement_values(date=date)
        values['supplierinfo_id'] = self.supplier_id
        return values

    def _get_replenishment_multiple_alternative(self, qty_to_order):
        self.ensure_one()
        routes = self.effective_route_id or self.product_id.route_ids
        if not (self.product_id and any(r.action == 'buy' for r in routes.rule_ids)):
            return super()._get_replenishment_multiple_alternative(qty_to_order)
        planned_date = self._get_orderpoint_procurement_date()
        global_horizon_days = self.get_horizon_days()
        if global_horizon_days:
            planned_date -= relativedelta.relativedelta(days=int(global_horizon_days))
        date_deadline = planned_date or fields.Date.today()
        dates_info = self.product_id._get_dates_info(date_deadline, self.location_id, route_ids=self.route_id)
        supplier = self.supplier_id or self.product_id.with_company(self.company_id)._select_seller(
            quantity=qty_to_order,
            date=max(dates_info['date_order'].date(), fields.Date.today()),
            uom_id=self.product_uom
        )
        return supplier.product_uom_id

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        qty_by_product_location, dummy = self.product_id._get_quantity_in_progress(self.location_id.ids)
        for orderpoint in self:
            product_qty = qty_by_product_location.get((orderpoint.product_id.id, orderpoint.location_id.id), 0.0)
            product_uom_qty = orderpoint.product_id.uom_id._compute_quantity(product_qty, orderpoint.product_uom, round=False)
            res[orderpoint.id] += product_uom_qty
        return res


class StockLot(models.Model):
    _inherit = 'stock.lot'

    purchase_order_ids = fields.Many2many('purchase.order', string="Purchase Orders", compute='_compute_purchase_order_ids', readonly=True, store=False)
    purchase_order_count = fields.Integer('Purchase order count', compute='_compute_purchase_order_ids')

    @api.depends('name')
    def _compute_purchase_order_ids(self):
        purchase_orders = defaultdict(lambda: self.env['purchase.order'])
        for move_line in self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('state', '=', 'done')]):
            move = move_line.move_id
            if move.picking_id.location_id.usage in ('supplier', 'transit') and move.purchase_line_id.order_id:
                purchase_orders[move_line.lot_id.id] |= move.purchase_line_id.order_id
        for lot in self:
            lot.purchase_order_ids = purchase_orders[lot.id]
            lot.purchase_order_count = len(lot.purchase_order_ids)

    def action_view_po(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_form_action")
        action['domain'] = [('id', 'in', self.mapped('purchase_order_ids.id'))]
        action['context'] = dict(self.env.context, create=False)
        return action
