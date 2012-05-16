# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from osv import osv, fields
import decimal_precision as dp
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from tools.translate import _
import netsvc
import time
import tools


#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle

class mrp_workcenter(osv.osv):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource':"resource_id"}
    _columns = {
        'note': fields.text('Description', help="Description of the Work Center. Explain here what's a cycle according to this Work Center."),
        'capacity_per_cycle': fields.float('Capacity per Cycle', help="Number of operations this Work Center can do in parallel. If this Work Center represents a team of 5 workers, the capacity per cycle is 5."),
        'time_cycle': fields.float('Time for 1 cycle (hour)', help="Time in hours for doing one cycle."),
        'time_start': fields.float('Time before prod.', help="Time in hours for the setup."),
        'time_stop': fields.float('Time after prod.', help="Time in hours for the cleaning."),
        'costs_hour': fields.float('Cost per hour', help="Specify Cost of Work Center per hour."),
        'costs_hour_account_id': fields.many2one('account.analytic.account', 'Hour Account', domain=[('type','<>','view')],
            help="Complete this only if you want automatic analytic accounting entries on production orders."),
        'costs_cycle': fields.float('Cost per cycle', help="Specify Cost of Work Center per cycle."),
        'costs_cycle_account_id': fields.many2one('account.analytic.account', 'Cycle Account', domain=[('type','<>','view')],
            help="Complete this only if you want automatic analytic accounting entries on production orders."),
        'costs_journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal'),
        'costs_general_account_id': fields.many2one('account.account', 'General Account', domain=[('type','<>','view')]),
        'resource_id': fields.many2one('resource.resource','Resource', ondelete='cascade', required=True),
        'product_id': fields.many2one('product.product','Work Center Product', help="Fill this product to track easily your production costs in the analytic accounting."),
    }
    _defaults = {
        'capacity_per_cycle': 1.0,
        'resource_type': 'material',
     }

    def on_change_product_cost(self, cr, uid, ids, product_id, context=None):
        value = {}

        if product_id:
            cost = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'costs_hour': cost.standard_price}
        return {'value': value}

mrp_workcenter()


class mrp_routing(osv.osv):
    """
    For specifying the routings of Work Centers.
    """
    _name = 'mrp.routing'
    _description = 'Routing'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the routing without removing it."),
        'code': fields.char('Code', size=8),

        'note': fields.text('Description'),
        'workcenter_lines': fields.one2many('mrp.routing.workcenter', 'routing_id', 'Work Centers'),

        'location_id': fields.many2one('stock.location', 'Production Location',
            help="Keep empty if you produce at the location where the finished products are needed." \
                "Set a location if you produce at a fixed location. This can be a partner location " \
                "if you subcontract the manufacturing operations."
        ),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.routing', context=context)
    }
mrp_routing()

class mrp_routing_workcenter(osv.osv):
    """
    Defines working cycles and hours of a Work Center using routings.
    """
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _columns = {
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of routing Work Centers."),
        'cycle_nbr': fields.float('Number of Cycles', required=True,
            help="Number of iterations this work center has to do in the specified operation of the routing."),
        'hour_nbr': fields.float('Number of Hours', required=True, help="Time in hours for this Work Center to achieve the operation of the specified routing."),
        'routing_id': fields.many2one('mrp.routing', 'Parent Routing', select=True, ondelete='cascade',
             help="Routing indicates all the Work Centers used, for how long and/or cycles." \
                "If Routing is indicated then,the third tab of a production order (Work Centers) will be automatically pre-completed."),
        'note': fields.text('Description'),
        'company_id': fields.related('routing_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
    }
mrp_routing_workcenter()

class mrp_bom(osv.osv):
    """
    Defines bills of material for a product.
    """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = ['mail.thread']

    def _child_compute(self, cr, uid, ids, name, arg, context=None):
        """ Gets child bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        result = {}
        if context is None:
            context = {}
        bom_obj = self.pool.get('mrp.bom')
        bom_id = context and context.get('active_id', False) or False
        cr.execute('select id from mrp_bom')
        if all(bom_id != r[0] for r in cr.fetchall()):
            ids.sort()
            bom_id = ids[0]
        bom_parent = bom_obj.browse(cr, uid, bom_id, context=context)
        for bom in self.browse(cr, uid, ids, context=context):
            if (bom_parent) or (bom.id == bom_id):
                result[bom.id] = map(lambda x: x.id, bom.bom_lines)
            else:
                result[bom.id] = []
            if bom.bom_lines:
                continue
            ok = ((name=='child_complete_ids') and (bom.product_id.supply_method=='produce'))
            if (bom.type=='phantom' or ok):
                sids = bom_obj.search(cr, uid, [('bom_id','=',False),('product_id','=',bom.product_id.id)])
                if sids:
                    bom2 = bom_obj.browse(cr, uid, sids[0], context=context)
                    result[bom.id] += map(lambda x: x.id, bom2.bom_lines)

        return result

    def _compute_type(self, cr, uid, ids, field_name, arg, context=None):
        """ Sets particular method for the selected bom type.
        @param field_name: Name of the field
        @param arg: User defined argument
        @return:  Dictionary of values
        """
        res = dict.fromkeys(ids, False)
        for line in self.browse(cr, uid, ids, context=context):
            if line.type == 'phantom' and not line.bom_id:
                res[line.id] = 'set'
                continue
            if line.bom_lines or line.type == 'phantom':
                continue
            if line.product_id.supply_method == 'produce':
                if line.product_id.procure_method == 'make_to_stock':
                    res[line.id] = 'stock'
                else:
                    res[line.id] = 'order'
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Reference', size=16),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the bills of material without removing it."),
        'type': fields.selection([('normal','Normal BoM'),('phantom','Sets / Phantom')], 'BoM Type', required=True,
                                 help= "If a sub-product is used in several products, it can be useful to create its own BoM. "\
                                 "Though if you don't want separated production orders for this sub-product, select Set/Phantom as BoM type. "\
                                 "If a Phantom BoM is used for a root product, it will be sold and shipped as a set of components, instead of being produced."),
        'method': fields.function(_compute_type, string='Method', type='selection', selection=[('',''),('stock','On Stock'),('order','On Order'),('set','Set / Pack')]),
        'date_start': fields.date('Valid From', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of bills of material."),
        'position': fields.char('Internal Reference', size=64, help="Reference to a position in an external plan."),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS', help="Product UOS (Unit of Sale) is the unit of measurement for the invoicing and promotion of stock."),
        'product_qty': fields.float('Product Qty', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control"),
        'product_rounding': fields.float('Product Rounding', help="Rounding applied on the product quantity."),
        'product_efficiency': fields.float('Manufacturing Efficiency', required=True, help="A factor of 0.9 means a loss of 10% within the production process."),
        'bom_lines': fields.one2many('mrp.bom', 'bom_id', 'BoM Lines'),
        'bom_id': fields.many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True),
        'routing_id': fields.many2one('mrp.routing', 'Routing', help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production planning."),
        'property_ids': fields.many2many('mrp.property', 'mrp_bom_property_rel', 'bom_id','property_id', 'Properties'),
        'revision_ids': fields.one2many('mrp.bom.revision', 'bom_id', 'BoM Revisions'),
        'child_complete_ids': fields.function(_child_compute, relation='mrp.bom', string="BoM Hierarchy", type='many2many'),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'active': lambda *a: 1,
        'product_efficiency': lambda *a: 1.0,
        'product_qty': lambda *a: 1.0,
        'product_rounding': lambda *a: 0.0,
        'type': lambda *a: 'normal',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.bom', context=c),
    }
    _order = "sequence"
    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)',  'All product quantities must be greater than 0.\n' \
            'You should install the mrp_subproduct module if you want to manage extra products on BoMs !'),
    ]

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct bom_id from mrp_bom where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    def _check_product(self, cr, uid, ids, context=None):
        all_prod = []
        boms = self.browse(cr, uid, ids, context=context)
        def check_bom(boms):
            res = True
            for bom in boms:
                if bom.product_id.id in all_prod:
                    res = res and False
                all_prod.append(bom.product_id.id)
                lines = bom.bom_lines
                if lines:
                    res = res and check_bom([bom_id for bom_id in lines if bom_id not in boms])
            return res
        return check_bom(boms)

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive BoM.', ['parent_id']),
        (_check_product, 'BoM line product should not be same as BoM product.', ['product_id']),
    ]

    def onchange_product_id(self, cr, uid, ids, product_id, name, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            return {'value': {'name': prod.name, 'product_uom': prod.uom_id.id}}
        return {}

    def _bom_find(self, cr, uid, product_id, product_uom, properties=[]):
        """ Finds BoM for particular product and product uom.
        @param product_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        cr.execute('select id from mrp_bom where product_id=%s and bom_id is null order by sequence', (product_id,))
        ids = map(lambda x: x[0], cr.fetchall())
        max_prop = 0
        result = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids):
            prop = 0
            for prop_id in bom.property_ids:
                if prop_id.id in properties:
                    prop += 1
            if (prop > max_prop) or ((max_prop == 0) and not result):
                result = bom.id
                max_prop = prop
        return result

    def _bom_explode(self, cr, uid, bom, factor, properties=[], addthis=False, level=0, routing_id=False):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product.
        @param factor: Factor of product UoM.
        @param properties: A List of properties Ids.
        @param addthis: If BoM found then True else False.
        @param level: Depth level to find BoM lines starts from 10.
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        routing_obj = self.pool.get('mrp.routing')
        factor = factor / (bom.product_efficiency or 1.0)
        factor = rounding(factor, bom.product_rounding)
        if factor < bom.product_rounding:
            factor = bom.product_rounding
        result = []
        result2 = []
        phantom = False
        if bom.type == 'phantom' and not bom.bom_lines:
            newbom = self._bom_find(cr, uid, bom.product_id.id, bom.product_uom.id, properties)

            if newbom:
                res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0], factor*bom.product_qty, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
                phantom = True
            else:
                phantom = False
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
            routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
            if routing:
                for wc_use in routing.workcenter_lines:
                    wc = wc_use.workcenter_id
                    d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                    mult = (d + (m and 1.0 or 0.0))
                    cycle = mult * wc_use.cycle_nbr
                    result2.append({
                        'name': tools.ustr(wc_use.name) + ' - '  + tools.ustr(bom.product_id.name),
                        'workcenter_id': wc.id,
                        'sequence': level+(wc_use.sequence or 0),
                        'cycle': cycle,
                        'hour': float(wc_use.hour_nbr*mult + ((wc.time_start or 0.0)+(wc.time_stop or 0.0)+cycle*(wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
                    })
            for bom2 in bom.bom_lines:
                res = self._bom_explode(cr, uid, bom2, factor, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        bom_data = self.read(cr, uid, id, [], context=context)
        default.update({'name': bom_data['name'] + ' ' + _('Copy'), 'bom_id':False})
        return super(mrp_bom, self).copy_data(cr, uid, id, default, context=context)

    def create(self, cr, uid, vals, context=None):
        obj_id = super(mrp_bom, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def create_send_note(self, cr, uid, ids, context=None):
        prod_obj = self.pool.get('product.product')
        for obj in self.browse(cr, uid, ids, context=context):
            for prod in prod_obj.browse(cr, uid, [obj.product_id], context=context):
                self.message_append_note(cr, uid, [obj.id], body=_("Bill of Material has been <b>created</b> for <em>%s</em> product.") % (prod.id.name_template), context=context)
        return True

mrp_bom()

class mrp_bom_revision(osv.osv):
    _name = 'mrp.bom.revision'
    _description = 'Bill of Material Revision'
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
        'author_id': lambda x, y, z, c: z,
        'date': fields.date.context_today,
    }

mrp_bom_revision()

def rounding(f, r):
    import math
    if not r:
        return f
    return math.ceil(f / r) * r

class mrp_production(osv.osv):
    """
    Production Orders / Manufacturing Orders
    """
    _name = 'mrp.production'
    _description = 'Manufacturing Order'
    _date_name  = 'date_planned'
    _inherit = ['ir.needaction_mixin', 'mail.thread']

    def _production_calc(self, cr, uid, ids, prop, unknow_none, context=None):
        """ Calculates total hours and total no. of cycles for a production order.
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
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

    def _production_date_end(self, cr, uid, ids, prop, unknow_none, context=None):
        """ Finds production end date.
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned
        return result

    def _production_date(self, cr, uid, ids, prop, unknow_none, context=None):
        """ Finds production planned date.
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned[:10]
        return result

    _columns = {
        'name': fields.char('Reference', size=64, required=True),
        'origin': fields.char('Source Document', size=64, help="Reference of the document that generated this production order request."),
        'priority': fields.selection([('0','Not urgent'),('1','Normal'),('2','Urgent'),('3','Very Urgent')], 'Priority', select=True),

        'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_qty': fields.float('Product Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos_qty': fields.float('Product UoS Qty', states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft':[('readonly',False)]}, readonly=True),

        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True,
            readonly=True, states={'draft':[('readonly',False)]}, help="Location where the system will look for components."),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True,
            readonly=True, states={'draft':[('readonly',False)]}, help="Location where the system will stock the finished products."),

        'date_planned_end': fields.function(_production_date_end, type='date', string='Scheduled End Date'),
        'date_planned_date': fields.function(_production_date, type='date', string='Scheduled Date'),
        'date_planned': fields.datetime('Scheduled date', required=True, select=1),
        'date_start': fields.datetime('Start Date', select=True),
        'date_finished': fields.datetime('End Date', select=True),

        'bom_id': fields.many2one('mrp.bom', 'Bill of Material', domain=[('bom_id','=',False)], readonly=True, states={'draft':[('readonly',False)]}),
        'routing_id': fields.many2one('mrp.routing', string='Routing', on_delete='set null', readonly=True, states={'draft':[('readonly',False)]}, help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production plannification."),
        'picking_id': fields.many2one('stock.picking', 'Picking list', readonly=True, ondelete="restrict",
            help="This is the Internal Picking List that brings the finished product to the production plan"),
        'move_prod_id': fields.many2one('stock.move', 'Move product', readonly=True),
        'move_lines': fields.many2many('stock.move', 'mrp_production_move_ids', 'production_id', 'move_id', 'Products to Consume', domain=[('state','not in', ('done', 'cancel'))], states={'done':[('readonly',True)]}),
        'move_lines2': fields.many2many('stock.move', 'mrp_production_move_ids', 'production_id', 'move_id', 'Consumed Products', domain=[('state','in', ('done', 'cancel'))]),
        'move_created_ids': fields.one2many('stock.move', 'production_id', 'Products to Produce', domain=[('state','not in', ('done', 'cancel'))], states={'done':[('readonly',True)]}),
        'move_created_ids2': fields.one2many('stock.move', 'production_id', 'Produced Products', domain=[('state','in', ('done', 'cancel'))]),
        'product_lines': fields.one2many('mrp.production.product.line', 'production_id', 'Scheduled goods'),
        'workcenter_lines': fields.one2many('mrp.production.workcenter.line', 'production_id', 'Work Centers Utilisation'),
        'state': fields.selection([('draft','New'),('picking_except', 'Picking Exception'),('confirmed','Waiting Goods'),('ready','Ready to Produce'),('in_production','Production Started'),('cancel','Cancelled'),('done','Done')],'State', readonly=True,
                                    help='When the production order is created the state is set to \'Draft\'.\n If the order is confirmed the state is set to \'Waiting Goods\'.\n If any exceptions are there, the state is set to \'Picking Exception\'.\
                                    \nIf the stock is available then the state is set to \'Ready to Produce\'.\n When the production gets started then the state is set to \'In Production\'.\n When the production is over, the state is set to \'Done\'.'),
        'hour_total': fields.function(_production_calc, type='float', string='Total Hours', multi='workorder', store=True),
        'cycle_total': fields.function(_production_calc, type='float', string='Total Cycles', multi='workorder', store=True),
        'user_id':fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'priority': lambda *a: '1',
        'state': lambda *a: 'draft',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'product_qty':  lambda *a: 1.0,
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').get(y, z, 'mrp.production') or '/',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.production', context=c),
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
    ]
    _order = 'priority desc, date_planned asc';

    def _check_qty(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if order.product_qty <= 0:
                return False
        return True

    _constraints = [
        (_check_qty, 'Order quantity cannot be negative or zero!', ['product_qty']),
    ]

    def create(self, cr, uid, vals, context=None):
        obj_id = super(mrp_production, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def unlink(self, cr, uid, ids, context=None):
        for production in self.browse(cr, uid, ids, context=context):
            if production.state not in ('draft', 'cancel'):
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete a manufacturing order in state \'%s\'') % production.state)
        return super(mrp_production, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.production'),
            'move_lines' : [],
            'move_lines2' : [],
            'move_created_ids' : [],
            'move_created_ids2' : [],
            'product_lines' : [],
            'picking_id': False
        })
        return super(mrp_production, self).copy(cr, uid, id, default, context)

    def location_id_change(self, cr, uid, ids, src, dest, context=None):
        """ Changes destination location if source location is changed.
        @param src: Source location id.
        @param dest: Destination location id.
        @return: Dictionary of values.
        """
        if dest:
            return {}
        if src:
            return {'value': {'location_dest_id': src}}
        return {}

    def product_id_change(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @return: Dictionary of values.
        """
        if not product_id:
            return {'value': {
                'product_uom': False,
                'bom_id': False,
                'routing_id': False
            }}
        bom_obj = self.pool.get('mrp.bom')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        bom_id = bom_obj._bom_find(cr, uid, product.id, product.uom_id and product.uom_id.id, [])
        routing_id = False
        if bom_id:
            bom_point = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom_point.routing_id.id or False
        result = {
            'product_uom': product.uom_id and product.uom_id.id or False,
            'bom_id': bom_id,
            'routing_id': routing_id
        }
        return {'value': result}

    def bom_id_change(self, cr, uid, ids, bom_id, context=None):
        """ Finds routing for changed BoM.
        @param product: Id of product.
        @return: Dictionary of values.
        """
        if not bom_id:
            return {'value': {
                'routing_id': False
            }}
        bom_point = self.pool.get('mrp.bom').browse(cr, uid, bom_id, context=context)
        routing_id = bom_point.routing_id.id or False
        result = {
            'routing_id': routing_id
        }
        return {'value': result}

    def action_picking_except(self, cr, uid, ids):
        """ Changes the state to Exception.
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'picking_except'})
        return True

    def action_compute(self, cr, uid, ids, properties=[], context=None):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        results = []
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids):
            cr.execute('delete from mrp_production_product_line where production_id=%s', (production.id,))
            cr.execute('delete from mrp_production_workcenter_line where production_id=%s', (production.id,))
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, production.product_id.id, production.product_uom.id, properties)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find a bill of material for this product."))
            factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, bom_point.product_uom.id)
            res = bom_obj._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id)
            results = res[0]
            results2 = res[1]
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line)
        return len(results)

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the production order and related stock moves.
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        for production in self.browse(cr, uid, ids, context=context):
            if production.state == 'confirmed' and production.picking_id.state not in ('draft', 'cancel'):
                raise osv.except_osv(
                    _('Could not cancel manufacturing order !'),
                    _('You must first cancel related internal picking attached to this manufacturing order.'))
            if production.move_created_ids:
                move_obj.action_cancel(cr, uid, [x.id for x in production.move_created_ids])
            move_obj.action_cancel(cr, uid, [x.id for x in production.move_lines])
        self.write(cr, uid, ids, {'state': 'cancel'})
        self.action_cancel_send_note(cr, uid, ids, context)
        return True

    def action_ready(self, cr, uid, ids, context=None):
        """ Changes the production state to Ready and location id of stock move.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        self.write(cr, uid, ids, {'state': 'ready'})

        for (production_id,name) in self.name_get(cr, uid, ids):
            production = self.browse(cr, uid, production_id)
            if production.move_prod_id:
                move_obj.write(cr, uid, [production.move_prod_id.id],
                        {'location_id': production.location_dest_id.id})
            self.action_ready_send_note(cr, uid, [production_id], context)
        return True

    def action_production_end(self, cr, uid, ids, context=None):
        """ Changes production state to Finish and writes finished date.
        @return: True
        """
        for production in self.browse(cr, uid, ids):
            self._costs_generate(cr, uid, production)
        write_res = self.write(cr, uid, ids, {'state': 'done', 'date_finished': time.strftime('%Y-%m-%d %H:%M:%S')})
        self.action_done_send_note(cr, uid, ids, context)
        return write_res

    def test_production_done(self, cr, uid, ids):
        """ Tests whether production is done or not.
        @return: True or False
        """
        res = True
        for production in self.browse(cr, uid, ids):
            if production.move_lines:
                res = False

            if production.move_created_ids:
                res = False
        return res

    def _get_subproduct_factor(self, cr, uid, production_id, move_id=None, context=None):
        """ Compute the factor to compute the qty of procucts to produce for the given production_id. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but if the
            module mrp_subproduct is installed, then we must use the move_id to identify the product to produce
            and its quantity.
        :param production_id: ID of the mrp.order
        :param move_id: ID of the stock move that needs to be produced. Will be used in mrp_subproduct.
        :return: The factor to apply to the quantity that we should produce for the given production order.
        """
        return 1

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce
        @param production_mode: specify production mode (consume/consume&produce).
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        production = self.browse(cr, uid, production_id, context=context)

        produced_qty = 0
        for produced_product in production.move_created_ids2:
            if (produced_product.scrapped) or (produced_product.product_id.id <> production.product_id.id):
                continue
            produced_qty += produced_product.product_qty
        if production_mode in ['consume','consume_produce']:
            consumed_data = {}

            # Calculate already consumed qtys
            for consumed in production.move_lines2:
                if consumed.scrapped:
                    continue
                if not consumed_data.get(consumed.product_id.id, False):
                    consumed_data[consumed.product_id.id] = 0
                consumed_data[consumed.product_id.id] += consumed.product_qty

            # Find product qty to be consumed and consume it
            for scheduled in production.product_lines:

                # total qty of consumed product we need after this consumption
                total_consume = ((production_qty + produced_qty) * scheduled.product_qty / production.product_qty)

                # qty available for consume and produce
                qty_avail = scheduled.product_qty - consumed_data.get(scheduled.product_id.id, 0.0)

                if qty_avail <= 0.0:
                    # there will be nothing to consume for this raw material
                    continue

                raw_product = [move for move in production.move_lines if move.product_id.id==scheduled.product_id.id]
                if raw_product:
                    # qtys we have to consume
                    qty = total_consume - consumed_data.get(scheduled.product_id.id, 0.0)

                    if qty > qty_avail:
                        # if qtys we have to consume is more than qtys available to consume
                        prod_name = scheduled.product_id.name_get()[0][1]
                        raise osv.except_osv(_('Warning!'), _('You are going to consume total %s quantities of "%s".\nBut you can only consume up to total %s quantities.') % (qty, prod_name, qty_avail))
                    if qty <= 0.0:
                        # we already have more qtys consumed than we need
                        continue

                    raw_product[0].action_consume(qty, raw_product[0].location_id.id, context=context)

        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            #vals = {'state':'confirmed'}
            #final_product_todo = [x.id for x in production.move_created_ids]
            #stock_mov_obj.write(cr, uid, final_product_todo, vals)
            #stock_mov_obj.action_confirm(cr, uid, final_product_todo, context)
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scrapped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty

            for produce_product in production.move_created_ids:
                produced_qty = produced_products.get(produce_product.product_id.id, 0)
                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                rest_qty = (subproduct_factor * production.product_qty) - produced_qty

                if rest_qty < production_qty:
                    prod_name = produce_product.product_id.name_get()[0][1]
                    raise osv.except_osv(_('Warning!'), _('You are going to produce total %s quantities of "%s".\nBut you can only produce up to total %s quantities.') % (production_qty, prod_name, rest_qty))
                if rest_qty > 0 :
                    stock_mov_obj.action_consume(cr, uid, [produce_product.id], (subproduct_factor * production_qty), context=context)

        for raw_product in production.move_lines2:
            new_parent_ids = []
            parent_move_ids = [x.id for x in raw_product.move_history_ids]
            for final_product in production.move_created_ids2:
                if final_product.id not in parent_move_ids:
                    new_parent_ids.append(final_product.id)
            for new_parent_id in new_parent_ids:
                stock_mov_obj.write(cr, uid, [raw_product.id], {'move_history_ids': [(4,new_parent_id)]})

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'mrp.production', production_id, 'button_produce_done', cr)
        return True

    def _costs_generate(self, cr, uid, production):
        """ Calculates total costs at the end of the production.
        @param production: Id of production order.
        @return: Calculated amount.
        """
        amount = 0.0
        analytic_line_obj = self.pool.get('account.analytic.line')
        for wc_line in production.workcenter_lines:
            wc = wc_line.workcenter_id
            if wc.costs_journal_id and wc.costs_general_account_id:
                value = wc_line.hour * wc.costs_hour
                account = wc.costs_hour_account_id.id
                if value and account:
                    amount += value
                    analytic_line_obj.create(cr, uid, {
                        'name': wc_line.name + ' (H)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'ref': wc.code,
                        'product_id': wc.product_id.id,
                        'unit_amount': wc_line.hour,
                        'product_uom_id': wc.product_id.uom_id.id
                    } )
            if wc.costs_journal_id and wc.costs_general_account_id:
                value = wc_line.cycle * wc.costs_cycle
                account = wc.costs_cycle_account_id.id
                if value and account:
                    amount += value
                    analytic_line_obj.create(cr, uid, {
                        'name': wc_line.name+' (C)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'ref': wc.code,
                        'product_id': wc.product_id.id,
                        'unit_amount': wc_line.cycle,
                        'product_uom_id': wc.product_id.uom_id.id
                    } )
        return amount

    def action_in_production(self, cr, uid, ids, context=None):
        """ Changes state to In Production and writes starting date.
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        self.action_in_production_send_note(cr, uid, ids, context)
        return True

    def test_if_product(self, cr, uid, ids):
        """
        @return: True or False
        """
        res = True
        for production in self.browse(cr, uid, ids):
            if not production.product_lines:
                if not self.action_compute(cr, uid, [production.id]):
                    res = False
        return res

    def _get_auto_picking(self, cr, uid, production):
        return True

    def _make_production_line_procurement(self, cr, uid, production_line, shipment_move_id, context=None):
        wf_service = netsvc.LocalService("workflow")
        procurement_order = self.pool.get('procurement.order')
        production = production_line.production_id
        location_id = production.location_src_id.id
        date_planned = production.date_planned
        procurement_name = (production.origin or '').split(':')[0] + ':' + production.name
        procurement_id = procurement_order.create(cr, uid, {
                    'name': procurement_name,
                    'origin': procurement_name,
                    'date_planned': date_planned,
                    'product_id': production_line.product_id.id,
                    'product_qty': production_line.product_qty,
                    'product_uom': production_line.product_uom.id,
                    'product_uos_qty': production_line.product_uos and production_line.product_qty or False,
                    'product_uos': production_line.product_uos and production_line.product_uos.id or False,
                    'location_id': location_id,
                    'procure_method': production_line.product_id.procure_method,
                    'move_id': shipment_move_id,
                    'company_id': production.company_id.id,
                })
        wf_service.trg_validate(uid, procurement_order._name, procurement_id, 'button_confirm', cr)
        return procurement_id

    def _make_production_internal_shipment_line(self, cr, uid, production_line, shipment_id, parent_move_id, destination_location_id=False, context=None):
        stock_move = self.pool.get('stock.move')
        production = production_line.production_id
        date_planned = production.date_planned
        # Internal shipment is created for Stockable and Consumer Products
        if production_line.product_id.type not in ('product', 'consu'):
            return False
        move_name = _('PROD: %s') % production.name
        source_location_id = production.location_src_id.id
        if not destination_location_id:
            destination_location_id = source_location_id
        return stock_move.create(cr, uid, {
                        'name': move_name,
                        'picking_id': shipment_id,
                        'product_id': production_line.product_id.id,
                        'product_qty': production_line.product_qty,
                        'product_uom': production_line.product_uom.id,
                        'product_uos_qty': production_line.product_uos and production_line.product_uos_qty or False,
                        'product_uos': production_line.product_uos and production_line.product_uos.id or False,
                        'date': date_planned,
                        'move_dest_id': parent_move_id,
                        'location_id': source_location_id,
                        'location_dest_id': destination_location_id,
                        'state': 'waiting',
                        'company_id': production.company_id.id,
                })

    def _make_production_internal_shipment(self, cr, uid, production, context=None):
        ir_sequence = self.pool.get('ir.sequence')
        stock_picking = self.pool.get('stock.picking')
        routing_loc = None
        pick_type = 'internal'
        partner_id = False

        # Take routing address as a Shipment Address.
        # If usage of routing location is a internal, make outgoing shipment otherwise internal shipment
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
            routing_loc = production.bom_id.routing_id.location_id
            if routing_loc.usage <> 'internal':
                pick_type = 'out'
            partner_id = routing_loc.partner_id and routing_loc.partner_id.id or False

        # Take next Sequence number of shipment base on type
        pick_name = ir_sequence.get(cr, uid, 'stock.picking.' + pick_type)

        picking_id = stock_picking.create(cr, uid, {
            'name': pick_name,
            'origin': (production.origin or '').split(':')[0] + ':' + production.name,
            'type': pick_type,
            'move_type': 'one',
            'state': 'auto',
            'partner_id': partner_id,
            'auto_picking': self._get_auto_picking(cr, uid, production),
            'company_id': production.company_id.id,
        })
        production.write({'picking_id': picking_id}, context=context)
        return picking_id

    def _make_production_produce_line(self, cr, uid, production, context=None):
        stock_move = self.pool.get('stock.move')
        source_location_id = production.product_id.product_tmpl_id.property_stock_production.id
        destination_location_id = production.location_dest_id.id
        move_name = _('PROD: %s') + production.name
        data = {
            'name': move_name,
            'date': production.date_planned,
            'product_id': production.product_id.id,
            'product_qty': production.product_qty,
            'product_uom': production.product_uom.id,
            'product_uos_qty': production.product_uos and production.product_uos_qty or False,
            'product_uos': production.product_uos and production.product_uos.id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'move_dest_id': production.move_prod_id.id,
            'state': 'waiting',
            'company_id': production.company_id.id,
        }
        move_id = stock_move.create(cr, uid, data, context=context)
        production.write({'move_created_ids': [(6, 0, [move_id])]}, context=context)
        return move_id

    def _make_production_consume_line(self, cr, uid, production_line, parent_move_id, source_location_id=False, context=None):
        stock_move = self.pool.get('stock.move')
        production = production_line.production_id
        # Internal shipment is created for Stockable and Consumer Products
        if production_line.product_id.type not in ('product', 'consu'):
            return False
        move_name = _('PROD: %s') % production.name
        destination_location_id = production.product_id.product_tmpl_id.property_stock_production.id
        if not source_location_id:
            source_location_id = production.location_src_id.id
        move_id = stock_move.create(cr, uid, {
            'name': move_name,
            'date': production.date_planned,
            'product_id': production_line.product_id.id,
            'product_qty': production_line.product_qty,
            'product_uom': production_line.product_uom.id,
            'product_uos_qty': production_line.product_uos and production_line.product_uos_qty or False,
            'product_uos': production_line.product_uos and production_line.product_uos.id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'move_dest_id': parent_move_id,
            'state': 'waiting',
            'company_id': production.company_id.id,
        })
        production.write({'move_lines': [(4, move_id)]}, context=context)
        return move_id

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms production order.
        @return: Newly generated Shipment Id.
        """
        shipment_id = False
        wf_service = netsvc.LocalService("workflow")
        uncompute_ids = filter(lambda x:x, [not x.product_lines and x.id or False for x in self.browse(cr, uid, ids, context=context)])
        self.action_compute(cr, uid, uncompute_ids, context=context)
        for production in self.browse(cr, uid, ids, context=context):
            shipment_id = self._make_production_internal_shipment(cr, uid, production, context=context)
            produce_move_id = self._make_production_produce_line(cr, uid, production, context=context)

            # Take routing location as a Source Location.
            source_location_id = production.location_src_id.id
            if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
                source_location_id = production.bom_id.routing_id.location_id.id

            for line in production.product_lines:
                consume_move_id = self._make_production_consume_line(cr, uid, line, produce_move_id, source_location_id=source_location_id, context=context)
                shipment_move_id = self._make_production_internal_shipment_line(cr, uid, line, shipment_id, consume_move_id,\
                                 destination_location_id=source_location_id, context=context)
                self._make_production_line_procurement(cr, uid, line, shipment_move_id, context=context)

            wf_service.trg_validate(uid, 'stock.picking', shipment_id, 'button_confirm', cr)
            production.write({'state':'confirmed'}, context=context)
            self.action_confirm_send_note(cr, uid, [production.id], context);
        return shipment_id

    def force_production(self, cr, uid, ids, *args):
        """ Assigns products.
        @param *args: Arguments
        @return: True
        """
        pick_obj = self.pool.get('stock.picking')
        pick_obj.force_assign(cr, uid, [prod.picking_id.id for prod in self.browse(cr, uid, ids)])
        return True
    
    # ---------------------------------------------------
    # OpenChatter methods and notifications
    # ---------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, [])
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'draft' and obj.user_id:
                result[obj.id] = [obj.user_id.id]
        return result

    def message_get_subscribers(self, cr, uid, ids, context=None):
        sub_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context);
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.user_id:
                sub_ids.append(obj.user_id.id)
        return self.pool.get('res.users').read(cr, uid, sub_ids, context=context)

    def create_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Manufacturing order has been <b>created</b>."), context=context)
        return True

    def action_cancel_send_note(self, cr, uid, ids, context=None):
        message = _("Manufacturing order has been <b>canceled</b>.")
        self.message_append_note(cr, uid, ids, body=message, context=context)
        return True

    def action_ready_send_note(self, cr, uid, ids, context=None):
        message = _("Manufacturing order is <b>ready to produce</b>.")
        self.message_append_note(cr, uid, ids, body=message, context=context)
        return True

    def action_in_production_send_note(self, cr, uid, ids, context=None):
        message = _("Manufacturing order is <b>in production</b>.")
        self.message_append_note(cr, uid, ids, body=message, context=context)
        return True

    def action_done_send_note(self, cr, uid, ids, context=None):
        message = _("Manufacturing order has been <b>done</b>.")
        self.message_append_note(cr, uid, ids, body=message, context=context)
        return True

    def action_confirm_send_note(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            # convert datetime field to a datetime, using server format, then
            # convert it to the user TZ and re-render it with %Z to add the timezone
            obj_datetime = fields.DT.datetime.strptime(obj.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
            obj_date_str = fields.datetime.context_timestamp(cr, uid, obj_datetime, context=context).strftime(DATETIME_FORMATS_MAP['%+'] + " (%Z)")
            message = _("Manufacturing order has been <b>confirmed</b> and is <b>scheduled</b> for the <em>%s</em>.") % (obj_date_str)
            self.message_append_note(cr, uid, [obj.id], body=message, context=context)
        return True


mrp_production()

class mrp_production_workcenter_line(osv.osv):
    _name = 'mrp.production.workcenter.line'
    _description = 'Work Order'
    _order = 'sequence'
    _inherit = ['mail.thread']

    _columns = {
        'name': fields.char('Work Order', size=64, required=True),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'cycle': fields.float('Nbr of cycles', digits=(16,2)),
        'hour': fields.float('Nbr of hours', digits=(16,2)),
        'sequence': fields.integer('Sequence', required=True, help="Gives the sequence order when displaying a list of work orders."),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True, ondelete='cascade', required=True),
    }
    _defaults = {
        'sequence': lambda *a: 1,
        'hour': lambda *a: 0,
        'cycle': lambda *a: 0,
    }
mrp_production_workcenter_line()

class mrp_production_product_line(osv.osv):
    _name = 'mrp.production.product.line'
    _description = 'Production Scheduled Product'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True),
    }
mrp_production_product_line()

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'bom_ids': fields.one2many('mrp.bom', 'product_id', 'Bill of Materials'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
