from openerp.osv import fields, osv


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _claim_count_out(self, cr, uid, ids, field_name, arg, context=None):
        Claim = self.pool['crm.claim']
        return {
            id: Claim.search_count(cr, uid, [('ref', '=',('stock.picking.out,' + str(ids[0])))], context=context)
            for id in ids
        }

    _columns = {
        'claim_count_out': fields.function(_claim_count_out, string='Claims', type='integer'),    
    }

# Because of the way inheritance works in the ORM (bug), and the way stock.picking.out
# is defined (inherit from stock.picking, dispatch read to stock.picking), it is necessary
# to add the field claim_count_out to this class, even though the _claim_count_out method
# in stock_picking_out will not be called (but its existence will be checked).
class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'

    def _claim_count_out(self, cr, uid, ids, field_name, arg, context=None):
        return super(stock_picking_out, self)._claim_count_out(cr, uid, ids, field_name, arg, context=context)

    _columns = {
        'claim_count_out': fields.function(_claim_count_out, string='Claims', type='integer'),    
    }
