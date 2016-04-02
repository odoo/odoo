# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_picking_to_wave(osv.osv_memory):
    _name = 'stock.picking.to.wave'
    _description = 'Add pickings to a picking wave'
    _columns = {
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave', required=True),
    }

    def attach_pickings(self, cr, uid, ids, context=None):
        #use active_ids to add picking line to the selected wave
        wave_id = self.browse(cr, uid, ids, context=context)[0].wave_id.id
        picking_ids = context.get('active_ids', False)
        return self.pool.get('stock.picking').write(cr, uid, picking_ids, {'wave_id': wave_id})