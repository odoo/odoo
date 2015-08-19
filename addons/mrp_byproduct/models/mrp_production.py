# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE fil
from openerp.osv import osv


class mrp_production(osv.osv):
    _description = 'Production'
    _inherit = 'mrp.production'

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms production order and calculates quantity based on subproduct_type.
        @return: Newly generated picking Id.
        """
        move_obj = self.pool.get('stock.move')
        picking_id = super(mrp_production, self).action_confirm(cr, uid, ids, context=context)
        product_uom_obj = self.pool.get('product.uom')
        for production in self.browse(cr, uid, ids):
            source = production.product_id.property_stock_production.id
            if not production.bom_id:
                continue
            for sub_product in production.bom_id.sub_products:
                product_uom_factor = product_uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, production.bom_id.product_uom.id)
                qty1 = sub_product.product_qty
                if sub_product.subproduct_type == 'variable':
                    if production.product_qty:
                        qty1 *= product_uom_factor / (production.bom_id.product_qty or 1.0)
                data = {
                    'name': 'PROD:'+production.name,
                    'date': production.date_planned,
                    'product_id': sub_product.product_id.id,
                    'product_uom_qty': qty1,
                    'product_uom': sub_product.product_uom.id,
                    'location_id': source,
                    'location_dest_id': production.location_dest_id.id,
                    'move_dest_id': production.move_prod_id.id,
                    'production_id': production.id
                }
                move_id = move_obj.create(cr, uid, data, context=context)
                move_obj.action_confirm(cr, uid, [move_id], context=context)

        return picking_id

    def _get_subproduct_factor(self, cr, uid, production_id, move_id=None, context=None):
        """Compute the factor to compute the qty of procucts to produce for the given production_id. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but with
            the module mrp_byproduct installed it can differ for byproducts having type 'variable'.
        :param production_id: ID of the mrp.order
        :param move_id: ID of the stock move that needs to be produced. Identify the product to produce.
        :return: The factor to apply to the quantity that we should produce for the given production order and stock move.
        """
        sub_obj = self.pool.get('mrp.subproduct')
        move_obj = self.pool.get('stock.move')
        production_obj = self.pool.get('mrp.production')
        production_browse = production_obj.browse(cr, uid, production_id, context=context)
        move_browse = move_obj.browse(cr, uid, move_id, context=context)
        subproduct_factor = 1
        sub_id = sub_obj.search(cr, uid, [('product_id', '=', move_browse.product_id.id), ('bom_id', '=', production_browse.bom_id.id), ('subproduct_type', '=', 'variable')], context=context)
        if sub_id:
            subproduct_record = sub_obj.browse(cr, uid, sub_id[0], context=context)
            if subproduct_record.bom_id.product_qty:
                subproduct_factor = subproduct_record.product_qty / subproduct_record.bom_id.product_qty
                return subproduct_factor
        return super(mrp_production, self)._get_subproduct_factor(cr, uid, production_id, move_id, context=context)
