from openerp.osv.orm import Model


class StockMove(Model):
    _inherit = 'stock.move'

    def update_prestashop_quantities(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            move.product_id.update_prestashop_quantities()

    def get_stock_location_ids(self, cr, uid, context=None):
        warehouse_obj = self.pool['stock.warehouse']
        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
        warehouses = warehouse_obj.browse(
            cr, uid, warehouse_ids, context=context
        )
        location_ids = []
        for warehouse in warehouses:
            location_ids.append(warehouse.lot_stock_id.id)
        return location_ids

    def create(self, cr, uid, vals, context=None):
        stock_id = super(StockMove, self).create(
            cr, uid, vals, context=context
        )
        location_ids = self.get_stock_location_ids(cr, uid, context=context)
        if vals['location_id'] in location_ids:
            self.update_prestashop_quantities(
                cr, uid, [stock_id], context=context
            )
        return stock_id

    def action_cancel(self, cr, uid, ids, context=None):
        res = super(StockMove, self).action_cancel(
            cr, uid, ids, context=context
        )
        location_ids = self.get_stock_location_ids(cr, uid, context=context)
        for move in self.browse(cr, uid, ids, context=context):
            if move.location_id.id in location_ids:
                self.update_prestashop_quantities(
                    cr, uid, [move.id], context=context
                )
        return res

    def action_done(self, cr, uid, ids, context=None):
        res = super(StockMove, self).action_done(cr, uid, ids, context=context)
        location_ids = self.get_stock_location_ids(cr, uid, context=context)
        for move in self.browse(cr, uid, ids, context=context):
            if move.location_dest_id.id in location_ids:
                self.update_prestashop_quantities(
                    cr, uid, [move.id], context=context
                )
        return res
