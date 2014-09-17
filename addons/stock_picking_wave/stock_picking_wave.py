# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_picking_wave(osv.osv):
    _name = "stock.picking.wave"
    _order = "name desc"
    _columns = {
        'name': fields.char('Picking Wave Name', required=True, help='Name of the picking wave', copy=False),
        'user_id': fields.many2one('res.users', 'Responsible', help='Person responsible for this wave'),
        'picking_ids': fields.one2many('stock.picking', 'wave_id', 'Pickings', help='List of picking associated to this wave'),
        'state': fields.selection([('draft', 'Draft'), ('in_progress', 'Running'), ('done', 'Done'), ('cancel', 'Cancelled')], string="State", required=True, copy=False),
    }

    _defaults = {
        'name': '/',
        'state': 'draft',
        }

    def confirm_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.write(cr, uid, ids, {'state': 'in_progress'}, context=context)
        return self.pool.get('stock.picking').action_assign(cr, uid, picking_todo, context=context)

    def cancel_picking(self, cr, uid, ids, context=None):
        picking_todo = self.pool.get('stock.picking').search(cr, uid, [('wave_id', 'in', ids)], context=context)
        self.pool.get('stock.picking').action_cancel(cr, uid, picking_todo, context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def print_picking(self, cr, uid, ids, context=None):
        '''
        This function print the report for all picking_ids associated to the picking wave
        '''
        context = dict(context or {})
        picking_ids = []
        for wave in self.browse(cr, uid, ids, context=context):
            picking_ids += [picking.id for picking in wave.picking_ids]
        if not picking_ids:
            raise osv.except_osv(_('Error!'), _('Nothing to print.'))
        context['active_ids'] = picking_ids
        context['active_model'] = 'stock.picking'
        return self.pool.get("report").get_action(cr, uid, [], 'stock.report_picking', context=context)

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'picking.wave') or '/'
        return super(stock_picking_wave, self).create(cr, uid, vals, context=context)

    def done(self, cr, uid, ids, context=None):
        picking_todo = set()
        for wave in self.browse(cr, uid, ids, context=context):
            for picking in wave.picking_ids:
                if picking.state in ('cancel', 'done'):
                    continue
                if picking.state != 'assigned':
                    raise osv.except_osv(_('Warning'), _('Some pickings are still waiting for goods. Please check or force their availability before setting this wave to done.'))
                picking_todo.add(picking.id)
        if picking_todo:
            self.pool.get('stock.picking').action_done(cr, uid, list(picking_todo), context=context)
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help='Picking wave associated to this picking'),
    }
