# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp.osv import fields, osv
from openerp import workflow

class stock_picking_wave(osv.osv):
    _name = "stock.picking.wave"
    _columns = {
        'name': fields.char('name', required=True, help='Name of the picking wave'),
        'partner_id': fields.many2one('res.partner', 'Responsible', help='Person responsible for this wave'),
        'time': fields.float('Time', help='Time it will take to perform the wave'),
        'picking_ids': fields.one2many('stock.picking', 'wave_id', 'Pickings', help='List of picking associated to this wave'),
        'capacity': fields.float('Capacity', help='The capacity of the transport used to get the goods'),
        'capacity_uom': fields.many2one('product.uom', 'Unit of Measure', help='The Unity Of Measure of the transport capacity'),
    }

    def confirm_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.pool.get('stock.picking').action_done(cr, uid, picking_todo, context=context)
        return True

    def cancel_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.pool.get('stock.picking').action_cancel(cr, uid, picking_todo, context=context)
        return True

    def print_picking(self, cr, uid, ids, context=None):
        '''
        This function print the report for all picking_ids associated to the picking wave
        '''
        assert len(ids) == 1, 'This option should only be used for a single wave picking at a time.'
        browse_picking_ids = self.browse(cr, uid, ids, context)[0].picking_ids
        picking_ids = []
        for picking in browse_picking_ids:
            picking_ids.append(picking.id)
        datas = {
             'ids': picking_ids,
             'model': 'stock.picking',
             'form': self.read(cr, uid, picking_ids[0], context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': context.get('report', 'stock.picking.list'),
            'datas': datas,
            'nodestroy' : True
        }


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave', help='Picking wave associated to this picking'),
    }