from openerp.osv import fields, osv


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _claim_count(self, cr, uid, ids, field_name, arg, context=None):
        Claim = self.pool['crm.claim']
        return {
            id: Claim.search_count(cr, uid, [('ref', '=',('stock.picking.out,' + str(ids[0])))], context=context)
            for id in ids
        }

    _columns = {
        'claim_count': fields.function(_claim_count, string='Claims', type='integer'),    
    }

class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'

    def _claim_count(self, cr, uid, ids, field_name, arg, context=None):
        return super(stock_picking_out, self)._claim_count(cr, uid, ids, field_name, arg, context=context)

    _columns = {
        'claim_count': fields.function(_claim_count, string='Claims', type='integer'),    
    }
