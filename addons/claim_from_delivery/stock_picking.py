from openerp.osv import fields, osv


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _claim_count_out(self, cr, uid, ids, field_name, arg, context=None):
        refs = [('stock.picking,' + str(picking_id)) for picking_id in ids]
        claim_data = self.pool['crm.claim'].read_group(cr, uid, [('ref', 'in', refs)], ['ref'], ['ref'], context=context)
        claim_dict = { int(data['ref'].split(',')[1]): data['ref_count'] for data in claim_data }
        return { picking_id: claim_dict.get(picking_id) for picking_id in ids }

    _columns = {
        'claim_count_out': fields.function(_claim_count_out, string='Claims', type='integer'),    
    }
