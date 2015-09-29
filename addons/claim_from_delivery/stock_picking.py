from openerp.osv import fields, osv


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _claim_count_out(self, cr, uid, ids, field_name, arg, context=None):
        Claim = self.pool['crm.claim']
        return {
            id: Claim.search_count(cr, uid, [('ref', '=',('stock.picking,' + str(ids[0])))], context=context)
            for id in ids
        }

    _columns = {
        'claim_count_out': fields.function(_claim_count_out, string='Claims', type='integer'),    
    }
