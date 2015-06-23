# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv


import openerp.addons.decimal_precision as dp


class stock_move(osv.osv):
    _inherit = 'stock.move'

    def _cal_move_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for move in self.browse(cr, uid, ids, context=context):
            weight = weight_net = 0.00
            if move.product_id.weight > 0.00:
                converted_qty = move.product_qty
                weight = (converted_qty * move.product_id.weight)

                if move.product_id.weight_net > 0.00:
                    weight_net = (converted_qty * move.product_id.weight_net)

            res[move.id] =  {
                            'weight': weight,
                            'weight_net': weight_net,
                            }
        return res

    _columns = {
        'weight': fields.function(_cal_move_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                  store={
                 'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_uom_qty', 'product_uom'], 30),
                 }),
        'weight_net': fields.function(_cal_move_weight, type='float', string='Net weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                  store={
                 'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_uom_qty', 'product_uom'], 30),
                 }),
        'weight_uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight",),
        }

    def action_confirm(self, cr, uid, ids, context=None):
        """
            Pass the carrier to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the original move is deleted)
        """
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.carrier_id:
                procs_to_check += [move.procurement_id]
        res = super(stock_move, self).action_confirm(cr, uid, ids, context=context)
        pick_obj = self.pool.get("stock.picking")
        for proc in procs_to_check:
            pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.carrier_id]))
            if pickings:
                pick_obj.write(cr, uid, pickings, {'carrier_id': proc.sale_line_id.order_id.carrier_id.id}, context=context)
        return res


    def _get_default_uom(self, cr, uid, context=None):
        uom_categ_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'product.product_uom_categ_kgm')
        return self.pool.get('product.uom').search(cr, uid, [('category_id', '=', uom_categ_id),('factor','=',1)])[0]

    _defaults = {
        'weight_uom_id': lambda self, cr, uid, c: self._get_default_uom(cr, uid, c),
    }
