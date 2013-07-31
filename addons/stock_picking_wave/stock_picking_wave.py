# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

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
        return self.pool.get('stock.picking').action_done(cr, uid, picking_todo, context=context)

    def cancel_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        return self.pool.get('stock.picking').action_cancel(cr, uid, picking_todo, context=context)

    def print_picking(self, cr, uid, ids, context=None):
        '''
        This function print the report for all picking_ids associated to the picking wave
        '''
        picking_ids = []
        for wave in self.browse(cr, uid, ids, context=context):
            picking_ids += [picking.id for picking in wave.picking_ids]
        if not picking_ids:
            raise osv.except_osv(_('Error!'), _('Nothing to print.'))
        datas = {
            'ids': picking_ids,
            'model': 'stock.picking',
            'form': self.read(cr, uid, picking_ids, context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': context.get('report', 'stock.picking.list'),
            'datas': datas,
            'nodestroy': True
        }


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave', help='Picking wave associated to this picking'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
