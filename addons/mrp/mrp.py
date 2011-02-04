# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields
from osv import osv
import ir

import netsvc
import time
from mx import DateTime
from tools.translate import _

#----------------------------------------------------------
# Workcenters
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle
#
# TODO: Work Center may be recursive ?
#
class mrp_workcenter(osv.osv):
    _name = 'mrp.workcenter'
    _description = 'Workcenter'
    _columns = {
        'name': fields.char('Workcenter Name', size=64, required=True),
        'active': fields.boolean('Active'),
        'type': fields.selection([('machine','Machine'),('hr','Human Resource'),('tool','Tool')], 'Type', required=True),
        'code': fields.char('Code', size=16),
        'timesheet_id': fields.many2one('hr.timesheet.group', 'Working Time', help="The normal working time of the workcenter."),
        'note': fields.text('Description', help="Description of the workcenter. Explain here what's a cycle according to this workcenter."),

        'capacity_per_cycle': fields.float('Capacity per Cycle', help="Number of operation this workcenter can do in parallel. If this workcenter represent a team of 5 workers, the capacity per cycle is 5."),

        'time_cycle': fields.float('Time for 1 cycle (hour)', help="Time in hours for doing one cycle."),
        'time_start': fields.float('Time before prod.', help="Time in hours for the setup."),
        'time_stop': fields.float('Time after prod.', help="Time in hours for the cleaning."),
        'time_efficiency': fields.float('Time Efficiency', help="Factor that multiplies all times expressed in the workcenter."),

        'costs_hour': fields.float('Cost per hour'),
        'costs_hour_account_id': fields.many2one('account.analytic.account', 'Hour Account', domain=[('type','<>','view')],
            help="Complete this only if you want automatic analytic accounting entries on production orders."),
        'costs_cycle': fields.float('Cost per cycle'),
        'costs_cycle_account_id': fields.many2one('account.analytic.account', 'Cycle Account', domain=[('type','<>','view')],
            help="Complete this only if you want automatic analytic accounting entries on production orders."),
        'costs_journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal'),
        'costs_general_account_id': fields.many2one('account.account', 'General Account', domain=[('type','<>','view')]),
    }
    _defaults = {
        'active': lambda *a: 1,
        'type': lambda *a: 'machine',
        'time_efficiency': lambda *a: 1.0,
        'capacity_per_cycle': lambda *a: 1.0,
    }
mrp_workcenter()


class mrp_property_group(osv.osv):
    _name = 'mrp.property.group'
    _description = 'Property Group'
    _columns = {
        'name': fields.char('Property Group', size=64, required=True),
        'description': fields.text('Description'),
    }
mrp_property_group()

class mrp_property(osv.osv):
    _name = 'mrp.property'
    _description = 'Property'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'composition': fields.selection([('min','min'),('max','max'),('plus','plus')], 'Properties composition', required=True, help="Not used in computations, for information purpose only."),
        'group_id': fields.many2one('mrp.property.group', 'Property Group', required=True),
        'description': fields.text('Description'),
    }
    _defaults = {
        'composition': lambda *a: 'min',
    }
mrp_property()

class mrp_routing(osv.osv):
    _name = 'mrp.routing'
    _description = 'Routing'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'active': fields.boolean('Active'),
        'code': fields.char('Code', size=8),

        'note': fields.text('Description'),
        'workcenter_lines': fields.one2many('mrp.routing.workcenter', 'routing_id', 'Workcenters'),

        'location_id': fields.many2one('stock.location', 'Production Location',
            help="Keep empty if you produce at the location where the finished products are needed." \
                "Set a location if you produce at a fixed location. This can be a partner location " \
                "if you subcontract the manufacturing operations."
        ),
    }
    _defaults = {
        'active': lambda *a: 1,
    }
mrp_routing()

class mrp_routing_workcenter(osv.osv):
    _name = 'mrp.routing.workcenter'
    _description = 'Routing workcenter usage'
    _columns = {
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', required=True),
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence'),
        'cycle_nbr': fields.float('Number of Cycle', required=True,
            help="A cycle is defined in the workcenter definition."),
        'hour_nbr': fields.float('Number of Hours', required=True),
        'routing_id': fields.many2one('mrp.routing', 'Parent Routing', select=True, ondelete='cascade'),
        'note': fields.text('Description')
    }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
    }
mrp_routing_workcenter()

class mrp_bom(osv.osv):
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    def _child_compute(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for bom in self.browse(cr, uid, ids, context=context):
            result[bom.id] = map(lambda x: x.id, bom.bom_lines)
            if bom.bom_lines:
                continue
            ok = ((name=='child_complete_ids') and (bom.product_id.supply_method=='produce'))
            if bom.type=='phantom' or ok:
                sids = self.pool.get('mrp.bom').search(cr, uid, [('bom_id','=',False),('product_id','=',bom.product_id.id)])
                if sids:
                    bom2 = self.pool.get('mrp.bom').browse(cr, uid, sids[0], context=context)
                    result[bom.id] += map(lambda x: x.id, bom2.bom_lines)
        return result
    def _compute_type(self, cr, uid, ids, field_name, arg, context):
        res = dict(map(lambda x: (x,''), ids))
        for line in self.browse(cr, uid, ids):
            if line.type=='phantom' and not line.bom_id:
                res[line.id] = 'set'
                continue
            if line.bom_lines or line.type=='phantom':
                continue
            if line.product_id.supply_method=='produce':
                if line.product_id.procure_method=='make_to_stock':
                    res[line.id] = 'stock'
                else:
                    res[line.id] = 'order'
        return res
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=16),
        'active': fields.boolean('Active'),
        'type': fields.selection([('normal','Normal BoM'),('phantom','Sets / Phantom')], 'BoM Type', required=True, help=
            "Use a phantom bill of material in raw materials lines that have to be " \
            "automatically computed in on eproduction order and not one per level." \
            "If you put \"Phantom/Set\" at the root level of a bill of material " \
            "it is considered as a set or pack: the products are replaced by the components " \
            "between the sale order to the picking without going through the production order." \
            "The normal BoM will generate one production order per BoM level."),
        'method': fields.function(_compute_type, string='Method', method=True, type='selection', selection=[('',''),('stock','On Stock'),('order','On Order'),('set','Set / Pack')]),
        'date_start': fields.date('Valid From', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence'),
        'position': fields.char('Internal Ref.', size=64, help="Reference to a position in an external plan."),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'product_qty': fields.float('Product Qty', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_rounding': fields.float('Product Rounding', help="Rounding applied on the product quantity. For integer only values, put 1.0"),
        'product_efficiency': fields.float('Product Efficiency', required=True, help="Efficiency on the production. A factor of 0.9 means a loss of 10% in the production."),
        'bom_lines': fields.one2many('mrp.bom', 'bom_id', 'BoM Lines'),
        'bom_id': fields.many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True),
        'routing_id': fields.many2one('mrp.routing', 'Routing', help="The list of operations (list of workcenters) to produce the finished product. The routing is mainly used to compute workcenter costs during operations and to plan futur loads on workcenters based on production plannification."),
        'property_ids': fields.many2many('mrp.property', 'mrp_bom_property_rel', 'bom_id','property_id', 'Properties'),
        'revision_ids': fields.one2many('mrp.bom.revision', 'bom_id', 'BoM Revisions'),
        'revision_type': fields.selection([('numeric','numeric indices'),('alpha','alphabetical indices')], 'indice type'),
        'child_ids': fields.function(_child_compute,relation='mrp.bom', method=True, string="BoM Hyerarchy", type='many2many'),
        'child_complete_ids': fields.function(_child_compute,relation='mrp.bom', method=True, string="BoM Hyerarchy", type='many2many')
    }
    _defaults = {
        'active': lambda *a: 1,
        'product_efficiency': lambda *a: 1.0,
        'product_qty': lambda *a: 1.0,
        'product_rounding': lambda *a: 1.0,
        'type': lambda *a: 'normal',
    }
    _order = "sequence"
    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)',  'All product quantities must be greater than 0.\n' \
            'You should install the mrp_subproduct module if you want to manage extra products on BoMs !'),
    ]

    def _check_recursion(self, cr, uid, ids):
        level = 500
        while len(ids):
            cr.execute('select distinct bom_id from mrp_bom where id in %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive BoM.', ['parent_id'])
    ]


    def onchange_product_id(self, cr, uid, ids, product_id, name, context={}):
        if product_id:
            prod=self.pool.get('product.product').browse(cr,uid,[product_id])[0]
            v = {'product_uom':prod.uom_id.id}
            if not name:
                v['name'] = prod.name
            return {'value': v}
        return {}

    def _bom_find(self, cr, uid, product_id, product_uom, properties=[]):
        bom_result = False
        # Why searching on BoM without parent ?
        cr.execute('select id from mrp_bom where product_id=%s and bom_id is null order by sequence', (product_id,))
        ids = map(lambda x: x[0], cr.fetchall())
        max_prop = 0
        result = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids):
            prop = 0
            for prop_id in bom.property_ids:
                if prop_id.id in properties:
                    prop+=1
            if (prop>max_prop) or ((max_prop==0) and not result):
                result = bom.id
                max_prop = prop
        return result

    def _bom_explode(self, cr, uid, bom, factor, properties, addthis=False, level=0):
        factor = factor / (bom.product_efficiency or 1.0)
        factor = rounding(factor, bom.product_rounding)
        if factor<bom.product_rounding:
            factor = bom.product_rounding
        result = []
        result2 = []
        phantom=False
        if bom.type=='phantom' and not bom.bom_lines:
            newbom = self._bom_find(cr, uid, bom.product_id.id, bom.product_uom.id, properties)
            if newbom:
                res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0], factor*bom.product_qty, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
                phantom=True
            else:
                phantom=False
        if not phantom:
            if addthis and not bom.bom_lines:
                result.append(
                {
                    'name': bom.product_id.name,
                    'product_id': bom.product_id.id,
                    'product_qty': bom.product_qty * factor,
                    'product_uom': bom.product_uom.id,
                    'product_uos_qty': bom.product_uos and bom.product_uos_qty * factor or False,
                    'product_uos': bom.product_uos and bom.product_uos.id or False,
                })
            if bom.routing_id:
                for wc_use in bom.routing_id.workcenter_lines:
                    wc = wc_use.workcenter_id
                    d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                    mult = (d + (m and 1.0 or 0.0))
                    cycle = mult * wc_use.cycle_nbr
                    result2.append({
                        'name': bom.routing_id.name,
                        'workcenter_id': wc.id,
                        'sequence': level+(wc_use.sequence or 0),
                        'cycle': cycle,
                        'hour': float(wc_use.hour_nbr*mult + (wc.time_start+wc.time_stop+cycle*wc.time_cycle) * (wc.time_efficiency or 1.0)),
                    })
            for bom2 in bom.bom_lines:
                res = self._bom_explode(cr, uid, bom2, factor, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2

mrp_bom()

class mrp_bom_revision(osv.osv):
    _name = 'mrp.bom.revision'
    _description = 'Bill of material revisions'
    _columns = {
        'name': fields.char('Modification name', size=64, required=True),
        'description': fields.text('Description'),
        'date': fields.date('Modification Date'),
        'indice': fields.char('Revision', size=16),
        'last_indice': fields.char('last indice', size=64),
        'author_id': fields.many2one('res.users', 'Author'),
        'bom_id': fields.many2one('mrp.bom', 'BoM', select=True),
    }

    _defaults = {
        'author_id': lambda x,y,z,c: z,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

mrp_bom_revision()

def rounding(f, r):
    if not r:
        return f
    return round(f / r) * r

class mrp_production(osv.osv):
    _name = 'mrp.production'
    _description = 'Production'
    _date_name  = 'date_planned'

    def _production_calc(self, cr, uid, ids, prop, unknow_none, context={}):
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = {
                'hour_total': 0.0,
                'cycle_total': 0.0,
            }
            for wc in prod.workcenter_lines:
                result[prod.id]['hour_total'] += wc.hour
                result[prod.id]['cycle_total'] += wc.cycle
        return result

    def _production_date_end(self, cr, uid, ids, prop, unknow_none, context={}):
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned
        return result

    def _production_date(self, cr, uid, ids, prop, unknow_none, context={}):
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned[:10]
        return result

    _columns = {
        'name': fields.char('Reference', size=64, required=True),
        'origin': fields.char('Origin', size=64),
        'priority': fields.selection([('0','Not urgent'),('1','Normal'),('2','Urgent'),('3','Very Urgent')], 'Priority'),

        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[('type','<>','service')]),
        'product_qty': fields.float('Product Qty', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos_qty': fields.float('Product UoS Qty', states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft':[('readonly',False)]}, readonly=True),

        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True,
            help="Location where the system will look for products used in raw materials."),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True,
            help="Location where the system will stock the finished products."),

        'date_planned_end': fields.function(_production_date_end, method=True, type='date', string='Scheduled End'),
        'date_planned_date': fields.function(_production_date, method=True, type='date', string='Scheduled Date'),
        'date_planned': fields.datetime('Scheduled date', required=True, select=1),
        'date_start': fields.datetime('Start Date'),
        'date_finnished': fields.datetime('End Date'),

        'bom_id': fields.many2one('mrp.bom', 'Bill of Material', domain=[('bom_id','=',False)]),
        'routing_id': fields.many2one('mrp.routing', string='Routing', on_delete='set null'),

        'picking_id': fields.many2one('stock.picking', 'Packing list', readonly=True,
            help="This is the internal picking list take bring the raw materials to the production plan."),
        'move_prod_id': fields.many2one('stock.move', 'Move product', readonly=True),
        'move_lines': fields.many2many('stock.move', 'mrp_production_move_ids', 'production_id', 'move_id', 'Products Consummed'),

        'move_created_ids': fields.one2many('stock.move', 'production_id', 'Moves Created'),
        'product_lines': fields.one2many('mrp.production.product.line', 'production_id', 'Scheduled goods'),
        'workcenter_lines': fields.one2many('mrp.production.workcenter.line', 'production_id', 'Workcenters Utilisation'),

        'state': fields.selection([('draft','Draft'),('picking_except', 'Packing Exception'),('confirmed','Waiting Goods'),('ready','Ready to Produce'),('in_production','In Production'),('cancel','Canceled'),('done','Done')],'Status', readonly=True),
        'hour_total': fields.function(_production_calc, method=True, type='float', string='Total Hours', multi='workorder'),
        'cycle_total': fields.function(_production_calc, method=True, type='float', string='Total Cycles', multi='workorder'),

    }
    _defaults = {
        'priority': lambda *a: '1',
        'state': lambda *a: 'draft',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'product_qty':  lambda *a: 1.0,
        'name': lambda x,y,z,c: x.pool.get('ir.sequence').get(y,z,'mrp.production') or '/',
    }
    _order = 'date_planned asc, priority desc';
    def unlink(self, cr, uid, ids, context=None):
        productions = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for s in productions:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Production Order(s) which are in %s State!' % s['state']))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def copy(self, cr, uid, id, default=None,context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.production'),
            'move_lines' : [],
            'move_created_ids': [],
            'state': 'draft'
        })
        return super(mrp_production, self).copy(cr, uid, id, default, context)

    def location_id_change(self, cr, uid, ids, src, dest, context={}):
        if dest:
            return {}
        if src:
            return {'value': {'location_dest_id': src}}
        return {}

    def product_id_change(self, cr, uid, ids, product):
        if not product:
            return {}
        res = self.pool.get('product.product').read(cr, uid, [product], ['uom_id'])[0]
        uom = res['uom_id'] and res['uom_id'][0]
        result = {'product_uom':uom}
        return {'value':result}

    def bom_id_change(self, cr, uid, ids, product):
        if not product:
            return {}
        res = self.pool.get('mrp.bom').read(cr, uid, [product], ['routing_id'])[0]
        routing_id = res['routing_id'] and res['routing_id'][0]
        result = {'routing_id':routing_id}
        return {'value':result}

    def action_picking_except(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'picking_except'})
        return True

    def action_compute(self, cr, uid, ids, properties=[]):
        results = []
        for production in self.browse(cr, uid, ids):
            cr.execute('delete from mrp_production_product_line where production_id=%s', (production.id,))
            cr.execute('delete from mrp_production_workcenter_line where production_id=%s', (production.id,))
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, production.product_id.id, production.product_uom.id, properties)
                if bom_id:
                    bom_point = self.pool.get('mrp.bom').browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))

            #if bom_point.routing_id and bom_point.routing_id.location_id:
            #   self.write(cr, uid, [production.id], {'location_src_id': bom_point.routing_id.location_id.id})

            factor = production.product_qty * production.product_uom.factor_inv / bom_point.product_uom.factor
            res = self.pool.get('mrp.bom')._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, properties)
            results = res[0]
            results2 = res[1]
            for line in results:
                line['production_id'] = production.id
                self.pool.get('mrp.production.product.line').create(cr, uid, line)
            for line in results2:
                line['production_id'] = production.id
                self.pool.get('mrp.production.workcenter.line').create(cr, uid, line)
        return len(results)

    def action_cancel(self, cr, uid, ids):
        for production in self.browse(cr, uid, ids):
            if production.move_created_ids:
                self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in production.move_created_ids])
            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in production.move_lines])
        self.write(cr, uid, ids, {'state':'cancel'}) #,'move_lines':[(6,0,[])]})
        return True

    #XXX: may be a bug here; lot_lines are unreserved for a few seconds;
    #     between the end of the picking list and the call to this function
    def action_ready(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'ready'})
        for production in self.browse(cr, uid, ids):
            if production.move_prod_id:
                self.pool.get('stock.move').write(cr, uid, [production.move_prod_id.id],
                        {'location_id':production.location_dest_id.id})
        return True

    #TODO Review materials in function in_prod and prod_end.
    def action_production_end(self, cr, uid, ids):
#        move_ids = []
        for production in self.browse(cr, uid, ids):
            for res in production.move_lines:
                for move in production.move_created_ids:
                    #XXX must use the orm
                    cr.execute('INSERT INTO stock_move_history_ids \
                            (parent_id, child_id) VALUES (%s,%s)',
                            (res.id, move.id))
#                move_ids.append(res.id)
            vals= {'state':'confirmed'}
            new_moves = [x.id for x in production.move_created_ids if x.state not in ['done','cancel']]
            self.pool.get('stock.move').write(cr, uid, new_moves, vals)
            if not production.date_finnished:
                self.write(cr, uid, [production.id],
                        {'date_finnished': time.strftime('%Y-%m-%d %H:%M:%S')})
            self.pool.get('stock.move').check_assign(cr, uid, new_moves)
            self.pool.get('stock.move').action_done(cr, uid, new_moves)
            self._costs_generate(cr, uid, production)
#        self.pool.get('stock.move').action_done(cr, uid, move_ids)
        self.write(cr,  uid, ids, {'state': 'done'})
        return True

    def _costs_generate(self, cr, uid, production):
        amount = 0.0
        for wc_line in production.workcenter_lines:
            wc = wc_line.workcenter_id
            if wc.costs_journal_id and wc.costs_general_account_id:
                value = wc_line.hour * wc.costs_hour
                account = wc.costs_hour_account_id.id
                if value and account:
                    amount += value
                    self.pool.get('account.analytic.line').create(cr, uid, {
                        'name': wc_line.name+' (H)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'code': wc.code
                    } )
            if wc.costs_journal_id and wc.costs_general_account_id:
                value = wc_line.cycle * wc.costs_cycle
                account = wc.costs_cycle_account_id.id
                if value and account:
                    amount += value
                    self.pool.get('account.analytic.line').create(cr, uid, {
                        'name': wc_line.name+' (C)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'code': wc.code
                    } )
        return amount

    def action_in_production(self, cr, uid, ids):
        move_ids = []
        for production in self.browse(cr, uid, ids):
            for res in production.move_lines:
                move_ids.append(res.id)
            if not production.date_start:
                self.write(cr, uid, [production.id],
                        {'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        self.pool.get('stock.move').action_done(cr, uid, move_ids)
        self.write(cr, uid, ids, {'state': 'in_production'})
        return True

    def test_if_product(self, cr, uid, ids):
        res = True
        for production in self.browse(cr, uid, ids):
            if not production.product_lines:
                if not self.action_compute(cr, uid, [production.id]):
                    res = False
        return res

    def _get_auto_picking(self, cr, uid, production):
        return True

    def action_confirm(self, cr, uid, ids):
        picking_id=False
        proc_ids = []
        for production in self.browse(cr, uid, ids):
            if not production.product_lines:
                self.action_compute(cr, uid, [production.id])
                production = self.browse(cr, uid, [production.id])[0]
            routing_loc = None
            pick_type = 'internal'
            address_id = False
            if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
                routing_loc = production.bom_id.routing_id.location_id
                if routing_loc.usage<>'internal':
                    pick_type = 'out'
                address_id = routing_loc.address_id and routing_loc.address_id.id or False
                routing_loc = routing_loc.id
            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                'origin': (production.origin or '').split(':')[0] +':'+production.name,
                'type': pick_type,
                'move_type': 'one',
                'state': 'auto',
                'address_id': address_id,
                'auto_picking': self._get_auto_picking(cr, uid, production),
            })

            source = production.product_id.product_tmpl_id.property_stock_production.id
            data = {
                'name':'PROD:'+production.name,
                'date_planned': production.date_planned,
                'product_id': production.product_id.id,
                'product_qty': production.product_qty,
                'product_uom': production.product_uom.id,
                'product_uos_qty': production.product_uos and production.product_uos_qty or False,
                'product_uos': production.product_uos and production.product_uos.id or False,
                'location_id': source,
                'location_dest_id': production.location_dest_id.id,
                'move_dest_id': production.move_prod_id.id,
                'state': 'waiting'
            }
            res_final_id = self.pool.get('stock.move').create(cr, uid, data)

            self.write(cr, uid, [production.id], {'move_created_ids': [(6, 0, [res_final_id])]})
            moves = []
            for line in production.product_lines:
                move_id=False
                newdate = production.date_planned
                if line.product_id.type in ('product', 'consu'):
                    res_dest_id = self.pool.get('stock.move').create(cr, uid, {
                        'name':'PROD:'+production.name,
                        'date_planned': production.date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                        'product_uos': line.product_uos and line.product_uos.id or False,
                        'location_id': routing_loc or production.location_src_id.id,
                        'location_dest_id': source,
                        'move_dest_id': res_final_id,
                        'state': 'waiting',
                    })
                    moves.append(res_dest_id)
                    move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name':'PROD:'+production.name,
                        'picking_id':picking_id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                        'product_uos': line.product_uos and line.product_uos.id or False,
                        'date_planned': newdate,
                        'move_dest_id': res_dest_id,
                        'location_id': production.location_src_id.id,
                        'location_dest_id': routing_loc or production.location_src_id.id,
                        'state': 'waiting',
                    })
                proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                    'name': (production.origin or '').split(':')[0] + ':' + production.name,
                    'origin': (production.origin or '').split(':')[0] + ':' + production.name,
                    'date_planned': newdate,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': line.product_uom.id,
                    'product_uos_qty': line.product_uos and line.product_qty or False,
                    'product_uos': line.product_uos and line.product_uos.id or False,
                    'location_id': production.location_src_id.id,
                    'procure_method': line.product_id.procure_method,
                    'move_id': move_id,
                })
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                proc_ids.append(proc_id)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            self.write(cr, uid, [production.id], {'picking_id':picking_id, 'move_lines': [(6,0,moves)], 'state':'confirmed'})
        return picking_id

    def force_production(self, cr, uid, ids, *args):
        pick_obj = self.pool.get('stock.picking')
        pick_obj.force_assign(cr, uid, [prod.picking_id.id for prod in self.browse(cr, uid, ids)])
        return True

mrp_production()


class stock_move(osv.osv):
    _name = 'stock.move'
    _inherit = 'stock.move'
    _columns = {
        'production_id': fields.many2one('mrp.production', 'Production', select=True),
    }
stock_move()

class mrp_production_workcenter_line(osv.osv):
    _name = 'mrp.production.workcenter.line'
    _description = 'Work Orders'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Work Order', size=64, required=True),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', required=True),
        'cycle': fields.float('Nbr of cycle', digits=(16,2)),
        'hour': fields.float('Nbr of hour', digits=(16,2)),
        'sequence': fields.integer('Sequence', required=True),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True, ondelete='cascade'),
    }
    _defaults = {
        'sequence': lambda *a: 1,
        'hour': lambda *a: 0,
        'cycle': lambda *a: 0,
    }
mrp_production_workcenter_line()

class mrp_production_product_line(osv.osv):
    _name = 'mrp.production.product.line'
    _description = 'Production scheduled products'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Qty', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True),
    }
mrp_production_product_line()

# ------------------------------------------------------------------
# Procurement
# ------------------------------------------------------------------
#
# Produce, Buy or Find products and place a move
#     then wizard for picking lists & move
#
class mrp_procurement(osv.osv):
    _name = "mrp.procurement"
    _description = "Procurement"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'origin': fields.char('Origin', size=64,
            help="Reference of the document that created this procurement.\n"
            "This is automatically completed by Open ERP."),
        'priority': fields.selection([('0','Not urgent'),('1','Normal'),('2','Urgent'),('3','Very Urgent')], 'Priority', required=True),
        'date_planned': fields.datetime('Scheduled date', required=True),
        'date_close': fields.datetime('Date Closed'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Quantity', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product UoM', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos_qty': fields.float('UoS Quantity', states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft':[('readonly',False)]}, readonly=True),
        'move_id': fields.many2one('stock.move', 'Reservation', ondelete='set null'),

        'bom_id': fields.many2one('mrp.bom', 'BoM', ondelete='cascade', select=True),

        'close_move': fields.boolean('Close Move at end', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'procure_method': fields.selection([('make_to_stock','from stock'),('make_to_order','on order')], 'Procurement Method', states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},
            readonly=True, required=True, help="If you encode manually a procurement, you probably want to use" \
            " a make to order method."),

        'purchase_id': fields.many2one('purchase.order', 'Purchase Order'),
        'note': fields.text('Note'),

        'property_ids': fields.many2many('mrp.property', 'mrp_procurement_property_rel', 'procurement_id','property_id', 'Properties'),

        'message': fields.char('Latest error', size=64),
        'state': fields.selection([
            ('draft','Draft'),
            ('confirmed','Confirmed'),
            ('exception','Exception'),
            ('running','Running'),
            ('cancel','Cancel'),
            ('ready','Ready'),
            ('done','Done'),
            ('waiting','Waiting')], 'Status', required=True),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'priority': lambda *a: '1',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'close_move': lambda *a: 0,
        'procure_method': lambda *a: 'make_to_order',
    }

    def unlink(self, cr, uid, ids, context=None):
        procurements = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for s in procurements:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Procurement Order(s) which are in %s State!' % s['state']))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def onchange_product_id(self, cr, uid, ids, product_id, context={}):
        if product_id:
            w=self.pool.get('product.product').browse(cr,uid,product_id, context)
            v = {
                'product_uom':w.uom_id.id,
                'product_uos':w.uos_id and w.uos_id.id or w.uom_id.id
            }
            return {'value': v}
        return {}

    def check_product(self, cr, uid, ids):
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.type in ('product', 'consu'):
                return True
        return False

    def get_phantom_bom_id(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.move_id and procurement.move_id.product_id.supply_method=='produce' \
                 and procurement.move_id.product_id.procure_method=='make_to_order':
                    phantom_bom_id = self.pool.get('mrp.bom').search(cr, uid, [
                        ('product_id', '=', procurement.move_id.product_id.id),
                        ('bom_id', '=', False),
                        ('type', '=', 'phantom')]) 
                    return phantom_bom_id 
        return False

    def check_move_cancel(self, cr, uid, ids, context={}):
        res = True
        ok = False
        for procurement in self.browse(cr, uid, ids, context):
            if procurement.move_id:
                ok = True
                if not procurement.move_id.state=='cancel':
                    res = False
        return res and ok

    def check_move_done(self, cr, uid, ids, context={}):
        res = True
        for proc in self.browse(cr, uid, ids, context):
            if proc.move_id:
                if not proc.move_id.state=='done':
                    res = False
        return res

    #
    # This method may be overrided by objects that override mrp.procurment
    # for computing their own purpose
    #
    def _quantity_compute_get(self, cr, uid, proc, context={}):
        if proc.product_id.type=='product':
            if proc.move_id.product_uos:
                return proc.move_id.product_uos_qty
        return False

    def _uom_compute_get(self, cr, uid, proc, context={}):
        if proc.product_id.type=='product':
            if proc.move_id.product_uos:
                return proc.move_id.product_uos.id
        return False

    #
    # Return the quantity of product shipped/produced/served, wich may be
    # different from the planned quantity
    #
    def quantity_get(self, cr, uid, id, context={}):
        proc = self.browse(cr, uid, id, context)
        result = self._quantity_compute_get(cr, uid, proc, context)
        if not result:
            result = proc.product_qty
        return result

    def uom_get(self, cr, uid, id, context=None):
        proc = self.browse(cr, uid, id, context)
        result = self._uom_compute_get(cr, uid, proc, context)
        if not result:
            result = proc.product_uom.id
        return result

    def check_waiting(self, cr, uid, ids, context=[]):
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.move_id and procurement.move_id.state=='auto':
                return True
        return False

    def check_produce_service(self, cr, uid, procurement, context=[]):
        return True

    def check_produce_product(self, cr, uid, procurement, context=[]):
        properties = [x.id for x in procurement.property_ids]
        bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, procurement.product_id.id, procurement.product_uom.id, properties)
        if not bom_id:
            cr.execute('update mrp_procurement set message=%s where id=%s', (_('No BoM defined for this product !'), procurement.id))
            return False
        return True

    def check_make_to_stock(self, cr, uid, ids, context={}):
        ok = True
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_id.type=='service':
                ok = ok and self._check_make_to_stock_service(cr, uid, procurement, context)
            else:
                ok = ok and self._check_make_to_stock_product(cr, uid, procurement, context)
        return ok

    def check_produce(self, cr, uid, ids, context={}):
        res = True
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.product_tmpl_id.supply_method<>'produce':
                if procurement.product_id.seller_ids:
                    partner = procurement.product_id.seller_ids[0].name
                    if user.company_id and user.company_id.partner_id:
                        if partner.id == user.company_id.partner_id.id:
                            return True
                return False
            if procurement.product_id.product_tmpl_id.type=='service':
                res = res and self.check_produce_service(cr, uid, procurement, context)
            else:
                res = res and self.check_produce_product(cr, uid, procurement, context)
            if not res:
                return False
        return res

    def check_buy(self, cr, uid, ids):
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.product_tmpl_id.supply_method<>'buy':
                return False
            if not procurement.product_id.seller_ids:
                cr.execute('update mrp_procurement set message=%s where id=%s', (_('No supplier defined for this product !'), procurement.id))
                return False
            partner = procurement.product_id.seller_ids[0].name
            if user.company_id and user.company_id.partner_id:
                if partner.id == user.company_id.partner_id.id:
                    return False
            address_id = self.pool.get('res.partner').address_get(cr, uid, [partner.id], ['delivery'])['delivery']
            if not address_id:
                cr.execute('update mrp_procurement set message=%s where id=%s', (_('No address defined for the supplier'), procurement.id))
                return False
        return True

    def test_cancel(self, cr, uid, ids):
        for record in self.browse(cr, uid, ids):
            if record.move_id and record.move_id.state=='cancel':
                return True
        return False

    def action_confirm(self, cr, uid, ids, context={}):
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_qty <= 0.00:
                raise osv.except_osv(_('Data Insufficient !'), _('Please check the Quantity of Procurement Order(s), it should not be less than 1!'))
            if procurement.product_id.type in ('product', 'consu'):
                if not procurement.move_id:
                    source = procurement.location_id.id
                    if procurement.procure_method=='make_to_order':
                        source = procurement.product_id.product_tmpl_id.property_stock_procurement.id
                    id = self.pool.get('stock.move').create(cr, uid, {
                        'name': 'PROC:'+procurement.name,
                        'location_id': source,
                        'location_dest_id': procurement.location_id.id,
                        'product_id': procurement.product_id.id,
                        'product_qty':procurement.product_qty,
                        'product_uom': procurement.product_uom.id,
                        'date_planned': procurement.date_planned,
                        'state':'confirmed',
                    })
                    self.write(cr, uid, [procurement.id], {'move_id': id, 'close_move':1})
                else:
                    if procurement.procure_method=='make_to_stock' and procurement.move_id.state in ('draft','waiting',):
                        # properly call action_confirm() on stock.move to abide by the location chaining etc.
                        id = self.pool.get('stock.move').action_confirm(cr, uid, [procurement.move_id.id], context=context)
        self.write(cr, uid, ids, {'state':'confirmed','message':''})
        return True

    def action_move_assigned(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'running','message':_('from stock: products assigned.')})
        return True

    def _check_make_to_stock_service(self, cr, uid, procurement, context={}):
        return True

    def _check_make_to_stock_product(self, cr, uid, procurement, context={}):
        ok = True
        if procurement.move_id:
            id = procurement.move_id.id
            if not (procurement.move_id.state in ('done','assigned','cancel')):
                ok = ok and self.pool.get('stock.move').action_assign(cr, uid, [id])
                cr.execute('select count(id) from stock_warehouse_orderpoint where product_id=%s', (procurement.product_id.id,))
                if not cr.fetchone()[0]:
                    cr.execute('update mrp_procurement set message=%s where id=%s', (_('from stock and no minimum orderpoint rule defined'), procurement.id))
        return ok

    def action_produce_assign_service(self, cr, uid, ids, context={}):
        for procurement in self.browse(cr, uid, ids):
            self.write(cr, uid, [procurement.id], {'state':'running'})
        return True

    def action_produce_assign_product(self, cr, uid, ids, context={}):
        produce_id = False
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        for procurement in self.browse(cr, uid, ids):
            res_id = procurement.move_id.id
            loc_id = procurement.location_id.id
            newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S') - DateTime.RelativeDateTime(days=procurement.product_id.product_tmpl_id.produce_delay or 0.0)
            newdate = newdate - DateTime.RelativeDateTime(days=company.manufacturing_lead)
            produce_id = self.pool.get('mrp.production').create(cr, uid, {
                'origin': procurement.origin,
                'product_id': procurement.product_id.id,
                'product_qty': procurement.product_qty,
                'product_uom': procurement.product_uom.id,
                'product_uos_qty': procurement.product_uos and procurement.product_uos_qty or False,
                'product_uos': procurement.product_uos and procurement.product_uos.id or False,
                'location_src_id': procurement.location_id.id,
                'location_dest_id': procurement.location_id.id,
                'bom_id': procurement.bom_id and procurement.bom_id.id or False,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_prod_id': res_id,
            })
            self.write(cr, uid, [procurement.id], {'state':'running'})
            bom_result = self.pool.get('mrp.production').action_compute(cr, uid,
                    [produce_id], properties=[x.id for x in procurement.property_ids])
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'mrp.production', produce_id, 'button_confirm', cr)
            self.pool.get('stock.move').write(cr, uid, [res_id],
                    {'location_id':procurement.location_id.id})
        return produce_id

    def action_po_assign(self, cr, uid, ids, context={}):
        purchase_id = False
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        for procurement in self.browse(cr, uid, ids):
            res_id = procurement.move_id.id
            partner = procurement.product_id.seller_ids[0].name
            partner_id = partner.id
            address_id = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            pricelist_id = partner.property_product_pricelist_purchase.id

            uom_id = procurement.product_id.uom_po_id.id

            qty = self.pool.get('product.uom')._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if procurement.product_id.seller_ids[0].qty:
                qty=max(qty,procurement.product_id.seller_ids[0].qty)

            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, False, {'uom': uom_id})[pricelist_id]

            newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S')
            newdate = newdate - DateTime.RelativeDateTime(days=company.po_lead)
            newdate = newdate - procurement.product_id.seller_ids[0].delay

            #Passing partner_id to context for purchase order line integrity of Line name
            context.update({'lang':partner.lang, 'partner_id':partner_id})
            
            product=self.pool.get('product.product').browse(cr,uid,procurement.product_id.id,context=context)

            line = {
                'name': product.partner_ref,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': uom_id,
                'price_unit': price,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_dest_id': res_id,
                'notes':product.description_purchase,
            }

            taxes_ids = procurement.product_id.product_tmpl_id.supplier_taxes_id
            taxes = self.pool.get('account.fiscal.position').map_tax(cr, uid, partner.property_account_position, taxes_ids)
            line.update({
                'taxes_id':[(6,0,taxes)]
            })
            purchase_id = self.pool.get('purchase.order').create(cr, uid, {
                'origin': procurement.origin,
                'partner_id': partner_id,
                'partner_address_id': address_id,
                'location_id': procurement.location_id.id,
                'pricelist_id': pricelist_id,
                'order_line': [(0,0,line)],
                'fiscal_position': partner.property_account_position and partner.property_account_position.id or False
            })
            self.write(cr, uid, [procurement.id], {'state':'running', 'purchase_id':purchase_id})
        return purchase_id

    def action_cancel(self, cr, uid, ids):
        todo = []
        todo2 = []
        for proc in self.browse(cr, uid, ids):
            if proc.close_move and proc.move_id:
                if proc.move_id.state not in ('done','cancel'):
                    todo2.append(proc.move_id.id)
            else:
                if proc.move_id and proc.move_id.state=='waiting':
                    todo.append(proc.move_id.id)
        if len(todo2):
            self.pool.get('stock.move').action_cancel(cr, uid, todo2)
        if len(todo):
            self.pool.get('stock.move').write(cr, uid, todo, {'state':'assigned'})
        self.write(cr, uid, ids, {'state':'cancel'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'mrp.procurement', id, cr)
        return True

    def action_check_finnished(self, cr, uid, ids):
        return self.check_move_done(cr, uid, ids)

    def action_check(self, cr, uid, ids):
        ok = False
        for procurement in self.browse(cr, uid, ids):
            if procurement.move_id.state=='assigned' or procurement.move_id.state=='done':
                self.action_done(cr, uid, [procurement.id])
                ok = True
        return ok

    def action_ready(self, cr, uid, ids):
        res = self.write(cr, uid, ids, {'state':'ready'})
        return res

    def action_done(self, cr, uid, ids):
        for procurement in self.browse(cr, uid, ids):
            if procurement.move_id:
                if procurement.close_move and (procurement.move_id.state <> 'done'):
                    self.pool.get('stock.move').action_done(cr, uid, [procurement.move_id.id])
        res = self.write(cr, uid, ids, {'state':'done', 'date_close':time.strftime('%Y-%m-%d')})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'mrp.procurement', id, cr)
        return res

    def run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        '''
        use_new_cursor: False or the dbname
        '''
        if not context:
            context={}
        self._procure_confirm(cr, uid, use_new_cursor=use_new_cursor, context=context)
        self._procure_orderpoint_confirm(cr, uid, automatic=automatic,\
                use_new_cursor=use_new_cursor, context=context)
mrp_procurement()


class stock_warehouse_orderpoint(osv.osv):
    _name = "stock.warehouse.orderpoint"
    _description = "Orderpoint minimum rule"
    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'active': fields.boolean('Active'),
        'logic': fields.selection([('max','Order to Max'),('price','Best price (not yet active!)')], 'Reordering Mode', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="cascade"),
        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[('type','=','product')], ondelete="cascade"),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_min_qty': fields.float('Min Quantity', required=True,
            help="When the virtual stock goes belong the Min Quantity, Open ERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
        'product_max_qty': fields.float('Max Quantity', required=True,
            help="When the virtual stock goes belong the Min Quantity, Open ERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
        'qty_multiple': fields.integer('Qty Multiple', required=True,
            help="The procurement quantity will by rounded up to this multiple."),
        'procurement_id': fields.many2one('mrp.procurement', 'Purchase Order', ondelete="set null")
    }
    _defaults = {
        'active': lambda *a: 1,
        'logic': lambda *a: 'max',
        'qty_multiple': lambda *a: 1,
        'name': lambda x,y,z,c: x.pool.get('ir.sequence').get(y,z,'mrp.warehouse.orderpoint') or '',
        'product_uom': lambda sel, cr, uid, context: context.get('product_uom', False),
    }
    
    _sql_constraints = [
        ( 'qty_multiple_check', 'CHECK( qty_multiple > 0 )', _('Qty Multiple must be greater than zero.')),
    ]
    
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context={}):
        if warehouse_id:
            w=self.pool.get('stock.warehouse').browse(cr,uid,warehouse_id, context)
            v = {'location_id':w.lot_stock_id.id}
            return {'value': v}
        return {}
    def onchange_product_id(self, cr, uid, ids, product_id, context={}):
        if product_id:
            prod=self.pool.get('product.product').browse(cr,uid,product_id)
            v = {'product_uom':prod.uom_id.id}
            return {'value': v}
        return {}
    def copy(self, cr, uid, id, default=None,context={}):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.warehouse.orderpoint') or '',
        })
        return super(stock_warehouse_orderpoint, self).copy(cr, uid, id, default, context)
stock_warehouse_orderpoint()


class StockMove(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'procurements': fields.one2many('mrp.procurement', 'move_id', 'Procurements'),
    }
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default['procurements'] = []
        return super(StockMove, self).copy(cr, uid, id, default, context)

    def _action_explode(self, cr, uid, move, context={}):
        if move.product_id.supply_method=='produce' and move.product_id.procure_method=='make_to_order':
            bis = self.pool.get('mrp.bom').search(cr, uid, [
                ('product_id','=',move.product_id.id),
                ('bom_id','=',False),
                ('type','=','phantom')])
            if bis:
                factor = move.product_qty
                bom_point = self.pool.get('mrp.bom').browse(cr, uid, bis[0])
                res = self.pool.get('mrp.bom')._bom_explode(cr, uid, bom_point, factor, [])
                state = 'confirmed'
                if move.state=='assigned':
                    state='assigned'
                for line in res[0]:
                    valdef = {
                        'picking_id': move.picking_id.id,
                        'product_id': line['product_id'],
                        'product_uom': line['product_uom'],
                        'product_qty': line['product_qty'],
                        'product_uos': line['product_uos'],
                        'product_uos_qty': line['product_uos_qty'],
                        'state': state,
                        'name': line['name'],
                        'move_history_ids': [(6,0,[move.id])],
                        'move_history_ids2': [(6,0,[])],
                        'procurements': []
                    }
                    mid = self.pool.get('stock.move').copy(cr, uid, move.id, default=valdef)
                    prodobj = self.pool.get('product.product').browse(cr, uid, line['product_id'], context=context)
                    proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                        'name': (move.picking_id.origin or ''),
                        'origin': (move.picking_id.origin or ''),
                        'date_planned': move.date_planned,
                        'product_id': line['product_id'],
                        'product_qty': line['product_qty'],
                        'product_uom': line['product_uom'],
                        'product_uos_qty': line['product_uos'] and line['product_uos_qty'] or False,
                        'product_uos':  line['product_uos'],
                        'location_id': move.location_id.id,
                        'procure_method': prodobj.procure_method,
                        'move_id': mid,
                    })
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                self.pool.get('stock.move').write(cr, uid, [move.id], {
                    'location_id': move.location_dest_id.id, # src and dest locations identical to have correct inventory, dummy move
                    'auto_validate': True,
                    'picking_id': False,
                    'state': 'waiting'
                })
                for m in self.pool.get('mrp.procurement').search(cr, uid, [('move_id','=',move.id)], context):
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'mrp.procurement', m, 'button_wait_done', cr)
        return True
StockMove()


class StockPicking(osv.osv):
    _inherit = 'stock.picking'

    def test_finnished(self, cursor, user, ids):
        wf_service = netsvc.LocalService("workflow")
        res = super(StockPicking, self).test_finnished(cursor, user, ids)
        for picking in self.browse(cursor, user, ids):
            for move in picking.move_lines:
                if move.state == 'done' and move.procurements:
                    for procurement in move.procurements:
                        wf_service.trg_validate(user, 'mrp.procurement',
                                procurement.id, 'button_check', cursor)
        return res

    #
    # Explode picking by replacing phantom BoMs
    #
    def action_explode(self, cr, uid, picks, *args):
        for move in self.pool.get('stock.move').browse(cr, uid, picks):
            self.pool.get('stock.move')._action_explode(cr, uid, move)
        return picks

StockPicking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

