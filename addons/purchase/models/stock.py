# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id = fields.Many2one('purchase.order', related='move_lines.purchase_line_id.order_id',
        string="Purchase Orders", readonly=True)

    @api.model
    def _prepare_values_extra_move(self, op, product, remaining_qty):
        res = super(StockPicking, self)._prepare_values_extra_move(op, product, remaining_qty)
        for m in op.linked_move_operation_ids:
            if m.move_id.purchase_line_id and m.move_id.product_id == product:
                res['purchase_line_id'] = m.move_id.purchase_line_id.id
                break
        return res

    @api.model
    def _create_backorder(self, backorder_moves=[]):
        res = super(StockPicking, self)._create_backorder(backorder_moves)
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                backorder = self.search([('backorder_id', '=', picking.id)])
                backorder.message_post_with_view('mail.message_origin_link',
                    values={'self': backorder, 'origin': backorder.purchase_id},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_line_id = fields.Many2one('purchase.order.line',
        'Purchase Order Line', ondelete='set null', index=True, readonly=True)

    @api.multi
    def get_price_unit(self):
        """ Returns the unit price to store on the quant """
        if self.purchase_line_id:
            order = self.purchase_line_id.order_id
            #if the currency of the PO is different than the company one, the price_unit on the move must be reevaluated
            #(was created at the rate of the PO confirmation, but must be valuated at the rate of stock move execution)
            if order.currency_id != self.company_id.currency_id:
                #we don't pass the move.date in the compute() for the currency rate on purpose because
                # 1) get_price_unit() is supposed to be called only through move.action_done(),
                # 2) the move hasn't yet the correct date (currently it is the expected date, after
                #    completion of action_done() it will be now() )
                price_unit = self.purchase_line_id._get_stock_move_price_unit()
                self.write({'price_unit': price_unit})
                return price_unit
            return self.price_unit
        return super(StockMove, self).get_price_unit()

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if not default.get('split_from'):
            #we don't want to propagate the link to the purchase order line except in case of move split
            default['purchase_line_id'] = False
        return super(StockMove, self).copy(default)


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
