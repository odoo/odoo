# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv.expression import AND


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
        date_value = fields.Datetime.from_string(value)
        return [('date_done', operator, date_value)]

    @api.model
    def _search_delay_pass(self, operator, value):
        date_value = fields.Datetime.from_string(value)
        return [('purchase_id.date_order', operator, date_value)]


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    buy_to_resupply = fields.Boolean('Buy to Resupply', default=True,
                                     help="When products are bought, they can be delivered to this warehouse")
    buy_pull_id = fields.Many2one('stock.rule', 'Buy rule', copy=False)

    def _generate_global_route_rules_values(self):
        rules = super()._generate_global_route_rules_values()
        location_id = self.lot_stock_id
        rules.update({
            'buy_pull_id': {
                'depends': ['reception_steps', 'buy_to_resupply'],
                'create_values': {
                    'action': 'buy',
                    'picking_type_id': self.in_type_id.id,
                    'group_propagation_option': 'none',
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


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super()._prepare_move_default_values(return_line, new_picking)
        if self.location_id.usage == "supplier":
            vals['purchase_line_id'], vals['partner_id'] = return_line.move_id._get_purchase_line_and_partner_from_chain()
        return vals

    def _create_return(self):
        picking = super()._create_return()
        if len(picking.move_ids.partner_id) == 1:
            picking.partner_id = picking.move_ids.partner_id
        return picking


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    show_supplier = fields.Boolean('Show supplier column', compute='_compute_show_suppplier')
    supplier_id = fields.Many2one(
        'product.supplierinfo', string='Supplier', check_company=True,
        domain="['|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]")
    vendor_id = fields.Many2one(related='supplier_id.partner_id', string="Vendor", store=True)
    purchase_visibility_days = fields.Float(default=0.0, help="Visibility Days applied on the purchase routes.")
    product_supplier_id = fields.Many2one('res.partner', compute='_compute_product_supplier_id', store=True, string='Product Supplier')

    @api.depends('product_id.purchase_order_line_ids.product_qty', 'product_id.purchase_order_line_ids.state')
    def _compute_qty(self):
        """ Extend to add more depends values """
        return super()._compute_qty()

    @api.depends('supplier_id')
    def _compute_lead_days(self):
        return super()._compute_lead_days()

    def _compute_visibility_days(self):
        res = super()._compute_visibility_days()
        for orderpoint in self:
            if 'buy' in orderpoint.rule_ids.mapped('action'):
                orderpoint.visibility_days = orderpoint.purchase_visibility_days
        return res

    @api.depends('product_tmpl_id', 'product_tmpl_id.seller_ids', 'product_tmpl_id.seller_ids.sequence', 'product_tmpl_id.seller_ids.partner_id')
    def _compute_product_supplier_id(self):
        for orderpoint in self:
            orderpoint.product_supplier_id = orderpoint.product_tmpl_id.seller_ids.sorted('sequence')[:1].partner_id.id

    def _set_visibility_days(self):
        res = super()._set_visibility_days()
        for orderpoint in self:
            if 'buy' in orderpoint.rule_ids.mapped('action'):
                orderpoint.purchase_visibility_days = orderpoint.visibility_days
        return res

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        for orderpoint in self:
            if 'buy' in orderpoint.rule_ids.mapped('action'):
                orderpoint.days_to_order = orderpoint.company_id.days_to_purchase
        return res

    @api.depends('route_id')
    def _compute_show_suppplier(self):
        buy_route = []
        for res in self.env['stock.rule'].search_read([('action', '=', 'buy')], ['route_id']):
            buy_route.append(res['route_id'][0])
        for orderpoint in self:
            orderpoint.show_supplier = orderpoint.route_id.id in buy_route

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

    def _get_lead_days_values(self):
        values = super()._get_lead_days_values()
        if self.supplier_id:
            values['supplierinfo'] = self.supplier_id
        return values

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        domain = [('orderpoint_id', 'in', self.ids)]
        if self.env.context.get('written_after'):
            domain = AND([domain, [('write_date', '>=', self.env.context.get('written_after'))]])
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

    def _prepare_procurement_values(self, date=False, group=False):
        values = super()._prepare_procurement_values(date=date, group=group)
        values['supplierinfo_id'] = self.supplier_id
        return values

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        qty_by_product_location, dummy = self.product_id._get_quantity_in_progress(self.location_id.ids)
        for orderpoint in self:
            product_qty = qty_by_product_location.get((orderpoint.product_id.id, orderpoint.location_id.id), 0.0)
            product_uom_qty = orderpoint.product_id.uom_id._compute_quantity(product_qty, orderpoint.product_uom, round=False)
            res[orderpoint.id] += product_uom_qty
        return res

    def _set_default_route_id(self):
        route_ids = self.env['stock.rule'].search([
            ('action', '=', 'buy')
        ]).route_id
        for orderpoint in self:
            route_id = orderpoint.rule_ids.route_id & route_ids
            if not orderpoint.product_id.seller_ids:
                continue
            if not route_id:
                continue
            orderpoint.route_id = route_id[0].id
        return super()._set_default_route_id()


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
        action['context'] = dict(self._context, create=False)
        return action


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    purchase_order_ids = fields.One2many('purchase.order', 'group_id')

    @api.model
    def run(self, procurements, raise_user_error=True):
        wh_by_comp = dict()
        for procurement in procurements:
            routes = procurement.values.get('route_ids')
            if routes and any(r.action == 'buy' for r in routes.rule_ids):
                company = procurement.company_id
                if company not in wh_by_comp:
                    wh_by_comp[company] = self.env['stock.warehouse'].search([('company_id', '=', company.id)])
                wh = wh_by_comp[company]
                procurement.values['route_ids'] |= wh.reception_route_id
        return super().run(procurements, raise_user_error=raise_user_error)
