# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_picking_wave(osv.osv):
    _name = "stock.picking.wave"
    _order = "name desc"
    _columns = {
        'name': fields.char('name', required=True, help='Name of the picking wave'),
        'partner_id': fields.many2one('res.partner', 'Responsible', help='Person responsible for this wave'),
        'time': fields.float('Time', help='Time it will take to perform the wave'),
        'picking_ids': fields.one2many('stock.picking', 'wave_id', 'Pickings', help='List of picking associated to this wave'),
        'capacity': fields.float('Capacity', help='The capacity of the transport used to get the goods'),
        'capacity_uom': fields.many2one('product.uom', 'Unit of Measure', help='The Unity Of Measure of the transport capacity'),
        'wave_type_id': fields.many2one('stock.picking.wave.type', 'Picking Wave Type'),
        'state': fields.selection([('in_progress', 'Running'), ('done', 'Done'), ('cancel', 'Cancelled')], required=True),

    }

    _defaults = {
        'name': '/',
        'state': 'in_progress',
        }

    def confirm_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        return self.pool.get('stock.picking').action_done(cr, uid, picking_todo, context=context)

    def cancel_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.pool.get('stock.picking').action_cancel(cr, uid, picking_todo, context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

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

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'picking.wave') or '/'
        return super(stock_picking_wave, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'state': 'in_progress',
            'name': self.pool.get('ir.sequence').get(cr, uid, 'picking.wave'),
        })
        return super(stock_picking_wave, self).copy(cr, uid, id, default=default, context=context)

    def done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave', help='Picking wave associated to this picking'),
        'wave_type_ids': fields.related('partner_id', 'wave_type_ids', type="many2many", relation='stock.picking.wave.type', string='Picking Wave Type'),
    }

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'wave_type_ids': fields.many2many('stock.picking.wave.type', 'stock_picking_wave_type_rel', 'wave_type_id', 'partner_id', 'Picking Wave Type'),
    }

class stock_picking_wave_type(osv.osv):
    _name = 'stock.picking.wave.type'
    _columns = {
        'name': fields.char('Type', required=True),
    }
