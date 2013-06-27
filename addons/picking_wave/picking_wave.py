# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp.osv import fields, osv
from openerp import workflow

class picking_wave(osv.osv):
    _name = "picking.wave"
    _columns = {
        'name': fields.char('name', required=True, help='Name of the picking wave'),
        'resp_id': fields.many2one('res.partner', 'Responsible', help='Person responsible for this wave'),
        'time': fields.float('Time', help='Time it will take to perform the wave'),
        'picking_ids': fields.one2many('stock.picking', 'wave_id', 'Pickings', help='List of picking associated to this wave'),
        'capacity': fields.float('Capacity', help='The capacity of the transport used to get the goods'),
        'capacity_uom': fields.many2one('product.uom', 'Unit of Measure', help='The Unity Of Measure of the transport capacity'),
    }

    def confirm_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.pool.get('stock.picking').wave_confirm_picking(cr, uid, picking_todo, context=context)
        return True

    def cancel_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.pool.get('stock.picking').wave_cancel_picking(cr, uid, picking_todo, context=context)
        return True


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'wave_id': fields.many2one('picking.wave', 'Picking Wave', help='Picking wave associated to this picking'),
    }

    def wave_confirm_picking(self, cr, uid, ids, context=None):
        """Set all stocks moves associated to this picking to done state and if picking is in draft,
        advance workflow to confirmed (which mean that it will afterwards automatically go to done)
        """
        move_obj = self.pool.get('stock.move')
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.state == 'draft':
                workflow.trg_validate(uid, 'stock.picking', picking.id, 'button_confirm', cr)

        moves_todo = move_obj.search(cr, uid, [('picking_id', 'in', ids)], context=context)
        move_obj.action_done(cr, uid, moves_todo, context=context)
        return True

    def wave_cancel_picking(self, cr, uid, ids, context=None):
        """Cancel the pickings and all stock move associated
        """
        for id in ids:
            workflow.trg_validate(uid, 'stock.picking', id, 'button_cancel', cr)
        return True