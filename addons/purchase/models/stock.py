# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id = fields.Many2one('purchase.order', related='move_lines.purchase_line_id.order_id',
        string="Purchase Orders", readonly=True)

    @api.model
    def _create_backorder(self, backorder_moves=[]):
        res = super(StockPicking, self)._create_backorder(backorder_moves)
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                for backorder in self.search([('backorder_id', '=', picking.id)]):
                    backorder.message_post_with_view('mail.message_origin_link',
                        values={'self': backorder, 'origin': backorder.purchase_id},
                        subtype_id=self.env.ref('mail.mt_note').id)
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_line_id = fields.Many2one('purchase.order.line',
        'Purchase Order Line', ondelete='set null', index=True, readonly=True, copy=False)
    created_purchase_line_id = fields.Many2one('purchase.order.line',
        'Created Purchase Order Line', ondelete='set null', readonly=True, copy=False)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields.append('purchase_line_id')
        return distinct_fields

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        move.ensure_one()
        keys_sorted = super(StockMove, self)._prepare_merge_move_sort_method(move)
        keys_sorted.append(move.purchase_line_id.id)
        return keys_sorted

    @api.multi
    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _action_cancel(self):
        for move in self:
            if move.created_purchase_line_id:
                try:
                    activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
                except ValueError:
                    activity_type_id = False
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type_id,
                    'note': _('A sale order that generated this purchase order has been deleted. Check if an action is needed.'),
                    'user_id': move.created_purchase_line_id.product_id.responsible_id.id,
                    'res_id': move.created_purchase_line_id.order_id.id,
                    'res_model_id': self.env.ref('purchase.model_purchase_order').id,
                })
        return super(StockMove, self)._action_cancel()


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    buy_to_resupply = fields.Boolean('Purchase to resupply this warehouse', default=True,
                                     help="When products are bought, they can be delivered to this warehouse")
    buy_pull_id = fields.Many2one('procurement.rule', 'Buy rule')

    @api.multi
    def _get_buy_pull_rule(self):
        try:
            buy_route_id = self.env['ir.model.data'].get_object_reference('purchase', 'route_warehouse0_buy')[1]
        except:
            buy_route_id = self.env['stock.location.route'].search([('name', 'like', _('Buy'))])
            buy_route_id = buy_route_id[0].id if buy_route_id else False
        if not buy_route_id:
            raise UserError(_("Can't find any generic Buy route."))

        return {
            'name': self._format_routename(_(' Buy')),
            'location_id': self.in_type_id.default_location_dest_id.id,
            'route_id': buy_route_id,
            'action': 'buy',
            'picking_type_id': self.in_type_id.id,
            'warehouse_id': self.id,
            'group_propagation_option': 'none',
        }

    @api.multi
    def create_routes(self):
        res = super(StockWarehouse, self).create_routes() # super applies ensure_one()
        if self.buy_to_resupply:
            buy_pull_vals = self._get_buy_pull_rule()
            buy_pull = self.env['procurement.rule'].create(buy_pull_vals)
            res['buy_pull_id'] = buy_pull.id
        return res

    @api.multi
    def write(self, vals):
        if 'buy_to_resupply' in vals:
            if vals.get("buy_to_resupply"):
                for warehouse in self:
                    if not warehouse.buy_pull_id:
                        buy_pull_vals = self._get_buy_pull_rule()
                        buy_pull = self.env['procurement.rule'].create(buy_pull_vals)
                        vals['buy_pull_id'] = buy_pull.id
            else:
                for warehouse in self:
                    if warehouse.buy_pull_id:
                        warehouse.buy_pull_id.unlink()
        return super(StockWarehouse, self).write(vals)

    @api.multi
    def _get_all_routes(self):
        routes = super(StockWarehouse, self).get_all_routes_for_wh()
        routes |= self.filtered(lambda self: self.buy_to_resupply and self.buy_pull_id and self.buy_pull_id.route_id).mapped('buy_pull_id').mapped('route_id')
        return routes

    @api.multi
    def _update_name_and_code(self, name=False, code=False):
        res = super(StockWarehouse, self)._update_name_and_code(name, code)
        warehouse = self[0]
        #change the buy procurement rule name
        if warehouse.buy_pull_id and name:
            warehouse.buy_pull_id.write({'name': warehouse.buy_pull_id.name.replace(warehouse.name, name, 1)})
        return res

    @api.multi
    def _update_routes(self):
        res = super(StockWarehouse, self)._update_routes()
        for warehouse in self:
            if warehouse.in_type_id.default_location_dest_id != warehouse.buy_pull_id.location_id:
                warehouse.buy_pull_id.write({'location_id': warehouse.in_type_id.default_location_dest_id.id})
        return res

class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super(ReturnPicking, self)._prepare_move_default_values(return_line, new_picking)
        vals['purchase_line_id'] = return_line.move_id.purchase_line_id.id
        return vals


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _quantity_in_progress(self):
        res = super(Orderpoint, self)._quantity_in_progress()
        for poline in self.env['purchase.order.line'].search([('state','in',('draft','sent','to approve')),('orderpoint_id','in',self.ids)]):
            res[poline.orderpoint_id.id] += poline.product_uom._compute_quantity(poline.product_qty, poline.orderpoint_id.product_uom, round=False)
        return res
