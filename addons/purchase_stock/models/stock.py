# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id = fields.Many2one('purchase.order', related='move_lines.purchase_line_id.order_id',
        string="Purchase Orders", readonly=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_line_id = fields.Many2one('purchase.order.line',
        'Purchase Order Line', ondelete='set null', index=True, readonly=True)
    created_purchase_line_id = fields.Many2one('purchase.order.line',
        'Created Purchase Order Line', ondelete='set null', readonly=True, copy=False, index=True)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields += ['purchase_line_id', 'created_purchase_line_id']
        return distinct_fields

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        move.ensure_one()
        keys_sorted = super(StockMove, self)._prepare_merge_move_sort_method(move)
        keys_sorted += [move.purchase_line_id.id, move.created_purchase_line_id.id]
        return keys_sorted

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                # The date must be today, and not the date of the move since the move move is still
                # in assigned state. However, the move date is the scheduled date until move is
                # done, then date of actual move processing. See:
                # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        """ Overridden from stock_account to support amount_currency on valuation lines generated from po
        """
        self.ensure_one()

        rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description)
        if self.purchase_line_id:
            purchase_currency = self.purchase_line_id.currency_id
            if purchase_currency != self.company_id.currency_id:
                # Do not use price_unit since we want the price tax excluded. And by the way, qty
                # is in the UOM of the product, not the UOM of the PO line.
                purchase_price_unit = (
                    self.purchase_line_id.price_subtotal / self.purchase_line_id.product_uom_qty
                    if self.purchase_line_id.product_uom_qty
                    else self.purchase_line_id.price_unit
                )
                currency_move_valuation = purchase_currency.round(purchase_price_unit * abs(qty))
                rslt['credit_line_vals']['amount_currency'] = rslt['credit_line_vals']['credit'] and -currency_move_valuation or currency_move_valuation
                rslt['credit_line_vals']['currency_id'] = purchase_currency.id
                rslt['debit_line_vals']['amount_currency'] = rslt['debit_line_vals']['credit'] and -currency_move_valuation or currency_move_valuation
                rslt['debit_line_vals']['currency_id'] = purchase_currency.id
        return rslt

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _clean_merged(self):
        super(StockMove, self)._clean_merged()
        self.write({'created_purchase_line_id': False})

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.created_purchase_line_id and self.created_purchase_line_id.state not in ('done', 'cancel'):
            return [(self.created_purchase_line_id.order_id, self.created_purchase_line_id.order_id.user_id, visited)]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)

    def _get_related_invoices(self):
        """ Overridden to return the vendor bills related to this stock move.
        """
        rslt = super(StockMove, self)._get_related_invoices()
        rslt += self.mapped('picking_id.purchase_id.invoice_ids').filtered(lambda x: x.state == 'posted')
        return rslt

    def _get_valuation_price_and_qty(self, related_aml, to_curr):
        valuation_price_unit_total = 0
        valuation_total_qty = 0
        for val_stock_move in self:
            # In case val_stock_move is a return move, its valuation entries have been made with the
            # currency rate corresponding to the original stock move
            valuation_date = val_stock_move.origin_returned_move_id.date or val_stock_move.date
            svl = val_stock_move.with_context(active_test=False).mapped('stock_valuation_layer_ids').filtered(
                lambda l: l.quantity)
            layers_qty = sum(svl.mapped('quantity'))
            layers_values = sum(svl.mapped('value'))
            valuation_price_unit_total += related_aml.company_currency_id._convert(
                layers_values, to_curr, related_aml.company_id, valuation_date, round=False,
            )
            valuation_total_qty += layers_qty
        if float_is_zero(valuation_total_qty, precision_rounding=related_aml.product_uom_id.rounding or related_aml.product_id.uom_id.rounding):
            raise UserError(
                _('Odoo is not able to generate the anglo saxon entries. The total valuation of %s is zero.') % _(related_aml.product_id.display_name))
        return valuation_price_unit_total, valuation_total_qty


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    buy_to_resupply = fields.Boolean('Buy to Resupply', default=True,
                                     help="When products are bought, they can be delivered to this warehouse")
    buy_pull_id = fields.Many2one('stock.rule', 'Buy rule')

    def _get_global_route_rules_values(self):
        rules = super(StockWarehouse, self)._get_global_route_rules_values()
        location_id = self.in_type_id.default_location_dest_id
        rules.update({
            'buy_pull_id': {
                'depends': ['reception_steps', 'buy_to_resupply'],
                'create_values': {
                    'action': 'buy',
                    'picking_type_id': self.in_type_id.id,
                    'group_propagation_option': 'none',
                    'company_id': self.company_id.id,
                    'route_id': self._find_global_route('purchase_stock.route_warehouse0_buy', _('Buy')).id,
                    'propagate_cancel': self.reception_steps != 'one_step',
                },
                'update_values': {
                    'active': self.buy_to_resupply,
                    'name': self._format_rulename(location_id, False, 'Buy'),
                    'location_id': location_id.id,
                    'propagate_cancel': self.reception_steps != 'one_step',
                }
            }
        })
        return rules

    def _get_all_routes(self):
        routes = super(StockWarehouse, self)._get_all_routes()
        routes |= self.filtered(lambda self: self.buy_to_resupply and self.buy_pull_id and self.buy_pull_id.route_id).mapped('buy_pull_id').mapped('route_id')
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
        vals = super(ReturnPicking, self)._prepare_move_default_values(return_line, new_picking)
        vals['purchase_line_id'] = return_line.move_id.purchase_line_id.id
        return vals


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _quantity_in_progress(self):
        res = super(Orderpoint, self)._quantity_in_progress()
        purchase_lines_in_progress = self.env['purchase.order.line'].search([
            ('state','in',('draft','sent','to approve')),
            '|',
                ('orderpoint_id','in',self.ids),
                ('move_dest_ids.product_id', 'in', self.mapped('product_id.id'))
        ])
        for poline in purchase_lines_in_progress:
            orderpoints = self.filtered(lambda x: x.product_id == poline.product_id)
            for orderpoint in orderpoints:
                if poline.product_uom.category_id == orderpoint.product_uom.category_id:
                    res[orderpoint.id] += poline.product_uom._compute_quantity(poline.product_qty, orderpoint.product_uom, round=False)
        return res

    def action_view_purchase(self):
        """ This function returns an action that display existing
        purchase orders of given orderpoint.
        """
        action = self.env.ref('purchase.purchase_rfq')
        result = action.read()[0]

        # Remvove the context since the action basically display RFQ and not PO.
        result['context'] = {}
        order_line_ids = self.env['purchase.order.line'].search([('orderpoint_id', '=', self.id)])
        purchase_ids = order_line_ids.mapped('order_id')

        result['domain'] = "[('id','in',%s)]" % (purchase_ids.ids)

        return result

    def write(self, vals):
        if vals.get('product_id'):
            po_lines = self.env['purchase.order.line'].search([('state','in',('draft','sent','to approve')),('orderpoint_id','in',self.ids)])
            po_lines.write({'orderpoint_id': False})
        return super(Orderpoint, self).write(vals)


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    purchase_order_ids = fields.Many2many('purchase.order', string="Purchase Orders", compute='_compute_purchase_order_ids', readonly=True, store=False)
    purchase_order_count = fields.Integer('Purchase order count', compute='_compute_purchase_order_ids')

    @api.depends('name')
    def _compute_purchase_order_ids(self):
        for lot in self:
            stock_moves = self.env['stock.move.line'].search([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done')
            ]).mapped('move_id')
            stock_moves = stock_moves.search([('id', 'in', stock_moves.ids)]).filtered(
                lambda move: move.picking_id.location_id.usage == 'supplier' and move.state == 'done')
            lot.purchase_order_ids = stock_moves.mapped('purchase_line_id.order_id')
            lot.purchase_order_count = len(lot.purchase_order_ids)

    def action_view_po(self):
        self.ensure_one()
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['domain'] = [('id', 'in', self.mapped('purchase_order_ids.id'))]
        action['context'] = dict(self._context, create=False)
        return action
